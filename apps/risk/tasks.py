"""
Celery tasks for risk app.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from apps.orders.models import Order
from apps.inventory.services import InventoryService


@shared_task
def auto_cancel_pending_orders():
    """
    Celery beat task to auto-cancel orders pending confirmation older than X minutes.
    Runs every 10 minutes.
    """
    # Get timeout from settings (default 30 minutes)
    timeout_minutes = getattr(settings, 'ORDER_CONFIRMATION_TIMEOUT_MINUTES', 30)
    timeout_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
    
    # Find orders pending confirmation older than threshold
    old_orders = Order.objects.filter(
        status=Order.Status.PENDING_CONFIRMATION,
        created_at__lt=timeout_threshold
    )
    
    cancelled_count = 0
    for order in old_orders:
        try:
            # Prepare items for release (in case any reservation was made)
            order_items = [
                {
                    'product_id': item.product.id,
                    'quantity': item.quantity
                }
                for item in order.items.all()
            ]
            
            # Try to release any reservations (idempotent, won't fail if none)
            InventoryService.release(
                order_items=order_items,
                reference=f'AUTO-CANCEL-{order.order_number}'
            )
            
            # Cancel order
            order.transition_status(Order.Status.CANCELLED)
            cancelled_count += 1
            
        except Exception as e:
            # Log error but continue with other orders
            print(f'Error cancelling order {order.id}: {str(e)}')
            continue
    
    return {
        'cancelled_count': cancelled_count,
        'threshold_minutes': timeout_minutes
    }
