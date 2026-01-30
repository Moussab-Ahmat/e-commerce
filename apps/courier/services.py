"""
Courier services for delivery operations.
"""
from django.db import transaction
from django.utils import timezone
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.orders.models import Order
from apps.inventory.services import InventoryService
from core.exceptions import InvalidDeliveryStatusError


class CourierService:
    """Service for courier delivery operations."""
    
    @staticmethod
    @transaction.atomic
    def update_delivery_status(delivery_id, new_status, user, notes='', failure_reason=''):
        """
        Update delivery status with atomic order and inventory operations.
        
        Args:
            delivery_id: Delivery ID
            new_status: New status (IN_TRANSIT, DELIVERED, FAILED)
            user: User updating status
            notes: Optional notes
            failure_reason: Optional failure reason
        
        Returns:
            dict: {
                'success': bool,
                'delivery': Delivery instance or None,
                'errors': list
            }
        """
        result = {
            'success': True,
            'delivery': None,
            'errors': []
        }
        
        try:
            delivery = Delivery.objects.select_for_update().get(pk=delivery_id)
        except Delivery.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Delivery {delivery_id} not found')
            return result
        
        # Check if delivery is assigned to this courier
        if not delivery.agent or delivery.agent.user != user:
            result['success'] = False
            result['errors'].append('Delivery is not assigned to you')
            return result
        
        # Validate status transition
        if not delivery.can_transition_to(new_status):
            result['success'] = False
            result['errors'].append(
                f'Cannot transition from {delivery.status} to {new_status}'
            )
            return result
        
        # Update delivery status
        try:
            old_status = delivery.status
            delivery.transition_status(new_status, user=user)
            
            # Update notes if provided
            if notes:
                delivery.delivery_notes = notes
            if failure_reason:
                delivery.failure_reason = failure_reason
            delivery.save(update_fields=['delivery_notes', 'failure_reason'])
            
            # If DELIVERED, update order and commit inventory outbound atomically
            if new_status == DeliveryStatus.DELIVERED:
                order = delivery.order
                
                # Transition order to DELIVERED
                if order.can_transition_to(Order.Status.DELIVERED):
                    order.transition_status(Order.Status.DELIVERED, user=user)
                else:
                    # Order might already be in a later status
                    pass
                
                # Commit inventory outbound
                order_items = [
                    {
                        'product_id': item.product.id,
                        'quantity': item.quantity
                    }
                    for item in order.items.all()
                ]
                
                commit_result = InventoryService.commit_outbound(
                    order_items=order_items,
                    reference=order.order_number
                )
                
                if not commit_result['success']:
                    result['success'] = False
                    result['errors'].extend(commit_result['errors'])
                    # Rollback will happen automatically due to transaction
                    return result
            
            result['delivery'] = delivery
            return result
            
        except InvalidDeliveryStatusError as e:
            result['success'] = False
            result['errors'].append(str(e))
            return result
