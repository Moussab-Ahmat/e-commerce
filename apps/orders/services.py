"""
Order service with idempotency and total calculation.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Order, OrderItem
from apps.delivery.services import calculate_delivery_fee
from apps.risk.services import RiskService


class OrderService:
    """Service for order operations."""
    
    @staticmethod
    @transaction.atomic
    def create_order(user, items, delivery_info, idempotency_key=None, customer_notes=''):
        """
        Create an order with idempotency support.
        
        Args:
            user: User creating the order
            items: List of dicts with 'product_id' and 'quantity'
            delivery_info: Dict with delivery zone_id, address, etc.
            idempotency_key: Optional idempotency key
            customer_notes: Optional customer notes
        
        Returns:
            dict: {
                'success': bool,
                'order': Order instance or None,
                'is_duplicate': bool,
                'errors': list
            }
        """
        result = {
            'success': True,
            'order': None,
            'is_duplicate': False,
            'errors': []
        }
        
        # Check idempotency if key provided
        if idempotency_key:
            existing_order = Order.objects.filter(
                idempotency_key=idempotency_key,
                user=user
            ).first()
            
            if existing_order:
                result['order'] = existing_order
                result['is_duplicate'] = True
                return result
        
        # Validate items
        if not items:
            result['success'] = False
            result['errors'].append('Order must have at least one item')
            return result
        
        # Calculate estimated total for risk checks (before creating order)
        # We need to estimate delivery fee for risk validation
        estimated_subtotal = 0
        for item_data in items:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)
            try:
                from apps.catalog.models import Product
                product = Product.objects.get(pk=product_id, is_active=True)
                estimated_subtotal += product.price * quantity
            except Product.DoesNotExist:
                pass
        
        # Estimate delivery fee
        estimated_delivery_fee = 0
        if delivery_info.get('zone_id'):
            estimated_delivery_fee = calculate_delivery_fee(
                zone_id=delivery_info.get('zone_id'),
                cart_total_xaf=estimated_subtotal
            )
        estimated_total = estimated_subtotal + estimated_delivery_fee
        
        # Risk validation
        risk_check = RiskService.validate_order_creation(user, estimated_total)
        if not risk_check['allowed']:
            result['success'] = False
            result['errors'].extend(risk_check['errors'])
            return result
        
        # Generate order number
        order_number = f'ORD-{timezone.now().strftime("%Y%m%d")}-{user.id:06d}'
        counter = 1
        while Order.objects.filter(order_number=order_number).exists():
            order_number = f'ORD-{timezone.now().strftime("%Y%m%d")}-{user.id:06d}-{counter}'
            counter += 1
        
        # Create order
        order = Order.objects.create(
            user=user,
            order_number=order_number,
            status=Order.Status.PENDING_CONFIRMATION,
            idempotency_key=idempotency_key,
            delivery_zone_id=delivery_info.get('zone_id'),
            delivery_latitude=delivery_info.get('latitude'),
            delivery_longitude=delivery_info.get('longitude'),
            delivery_address_line1=delivery_info.get('address_line1', ''),
            delivery_address_line2=delivery_info.get('address_line2', ''),
            delivery_city=delivery_info.get('city', ''),
            delivery_region=delivery_info.get('region', ''),
            delivery_postal_code=delivery_info.get('postal_code', ''),
            delivery_phone=delivery_info.get('phone', ''),
            customer_notes=customer_notes
        )
        
        # Create order items and calculate subtotal
        subtotal = 0
        for item_data in items:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)
            
            try:
                from apps.catalog.models import Product
                product = Product.objects.get(pk=product_id, is_active=True)
            except Product.DoesNotExist:
                result['success'] = False
                result['errors'].append(f'Product {product_id} not found or inactive')
                order.delete()  # Rollback
                return result
            
            # Get current price
            unit_price = product.price
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price
            )
            
            subtotal += unit_price * quantity
        
        # Calculate delivery fee
        delivery_fee = 0
        if order.delivery_zone:
            delivery_fee = calculate_delivery_fee(
                zone_id=order.delivery_zone.id,
                cart_total_xaf=subtotal
            )
        
        # Update order totals
        order.subtotal = subtotal
        order.delivery_fee = delivery_fee
        order.total = subtotal + delivery_fee
        order.save(update_fields=['subtotal', 'delivery_fee', 'total'])
        
        result['order'] = order
        return result
    
    @staticmethod
    @transaction.atomic
    def cancel_order(order_id, user):
        """
        Cancel an order (only before CONFIRMED).
        
        Args:
            order_id: Order ID
            user: User cancelling (must be order owner or staff)
        
        Returns:
            dict: {
                'success': bool,
                'order': Order instance or None,
                'errors': list
            }
        """
        result = {
            'success': True,
            'order': None,
            'errors': []
        }
        
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Order {order_id} not found')
            return result
        
        # Check permissions
        if not user.is_staff and order.user != user:
            result['success'] = False
            result['errors'].append('Permission denied')
            return result
        
        # Check if can be cancelled
        if order.status == Order.Status.CONFIRMED:
            result['success'] = False
            result['errors'].append('Cannot cancel order after confirmation')
            return result
        
        if order.status in [Order.Status.CANCELLED, Order.Status.COMPLETED, Order.Status.REFUNDED]:
            result['success'] = False
            result['errors'].append(f'Order is already {order.status}')
            return result
        
        # Cancel order
        try:
            order.transition_status(Order.Status.CANCELLED, user=user)
            result['order'] = order
        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
        
        return result
    
    @staticmethod
    @transaction.atomic
    def confirm_order(order_id, user):
        """
        Confirm order and reserve inventory.
        
        Args:
            order_id: Order ID
            user: User confirming (must be staff)
        
        Returns:
            dict: {
                'success': bool,
                'order': Order instance or None,
                'errors': list
            }
        """
        from core.exceptions import InvalidOrderStatusError
        
        result = {
            'success': True,
            'order': None,
            'errors': []
        }
        
        # Only staff can confirm orders
        if not user.is_staff:
            result['success'] = False
            result['errors'].append('Only staff can confirm orders')
            return result
        
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Order {order_id} not found')
            return result
        
        # Check if order can be confirmed
        if order.status != Order.Status.PENDING_CONFIRMATION:
            result['success'] = False
            result['errors'].append(f'Order status is {order.status}, cannot confirm')
            return result
        
        # Prepare items for inventory reservation
        order_items = [
            {
                'product_id': item.product.id,
                'quantity': item.quantity
            }
            for item in order.items.all()
        ]
        
        # Reserve inventory
        from apps.inventory.services import InventoryService
        reserve_result = InventoryService.reserve(
            order_items=order_items,
            reference=order.order_number
        )
        
        if not reserve_result['success']:
            result['success'] = False
            result['errors'].extend(reserve_result['errors'])
            return result
        
        # Transition order status to CONFIRMED
        try:
            order.transition_status(Order.Status.CONFIRMED, user=user)
            result['order'] = order
        except InvalidOrderStatusError as e:
            result['success'] = False
            result['errors'].append(str(e))
            # Release reservation if status transition fails
            InventoryService.release(order_items, reference=order.order_number)
        
        return result
