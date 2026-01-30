"""
Inventory service with atomic operations for stock management.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import InventoryItem, StockMovement


class InventoryService:
    """Service for atomic inventory operations."""
    
    @staticmethod
    @transaction.atomic
    def check_available(items):
        """
        Check if items are available in requested quantities.
        
        Args:
            items: List of dicts with 'product_id' and 'quantity'
        
        Returns:
            dict: {
                'available': bool,
                'items': [
                    {
                        'product_id': int,
                        'requested': int,
                        'available': int,
                        'sufficient': bool
                    }
                ]
            }
        """
        result = {
            'available': True,
            'items': []
        }
        
        for item in items:
            product_id = item['product_id']
            requested_quantity = item['quantity']
            
            try:
                inventory_item = InventoryItem.objects.select_for_update().get(
                    product_id=product_id
                )
                available_quantity = inventory_item.available
                sufficient = available_quantity >= requested_quantity
                
                result['items'].append({
                    'product_id': product_id,
                    'requested': requested_quantity,
                    'available': available_quantity,
                    'sufficient': sufficient
                })
                
                if not sufficient:
                    result['available'] = False
                    
            except InventoryItem.DoesNotExist:
                result['items'].append({
                    'product_id': product_id,
                    'requested': requested_quantity,
                    'available': 0,
                    'sufficient': False
                })
                result['available'] = False
        
        return result
    
    @staticmethod
    @transaction.atomic
    def reserve(order_items, reference=''):
        """
        Reserve stock for order items.
        
        Args:
            order_items: List of dicts with 'product_id' and 'quantity'
            reference: Optional reference string (e.g., order number)
        
        Returns:
            dict: {
                'success': bool,
                'reserved_items': [
                    {
                        'product_id': int,
                        'quantity': int,
                        'inventory_item_id': int
                    }
                ],
                'errors': list
            }
        """
        result = {
            'success': True,
            'reserved_items': [],
            'errors': []
        }
        
        # First, check availability
        availability = InventoryService.check_available(order_items)
        
        if not availability['available']:
            result['success'] = False
            for item in availability['items']:
                if not item['sufficient']:
                    result['errors'].append(
                        f"Product {item['product_id']}: requested {item['requested']}, "
                        f"available {item['available']}"
                    )
            return result
        
        # Reserve stock
        for item in order_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            try:
                inventory_item = InventoryItem.objects.select_for_update().get(
                    product_id=product_id
                )
                
                # Double-check availability (within transaction)
                if inventory_item.available < quantity:
                    result['success'] = False
                    result['errors'].append(
                        f"Product {product_id}: insufficient stock at reservation time"
                    )
                    # Rollback will happen automatically
                    return result
                
                # Reserve stock
                inventory_item.reserved += quantity
                inventory_item.save(update_fields=['reserved'])
                
                # Create movement record
                StockMovement.objects.create(
                    inventory_item=inventory_item,
                    movement_type=StockMovement.MovementType.OUTBOUND,
                    quantity=-quantity,  # Negative for reservation
                    reference=reference,
                    notes=f'Reserved for order: {reference}'
                )
                
                result['reserved_items'].append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'inventory_item_id': inventory_item.id
                })
                
            except InventoryItem.DoesNotExist:
                result['success'] = False
                result['errors'].append(f"Product {product_id}: inventory item not found")
                return result
        
        return result
    
    @staticmethod
    @transaction.atomic
    def release(order_items, reference=''):
        """
        Release reserved stock.
        
        Args:
            order_items: List of dicts with 'product_id' and 'quantity'
            reference: Optional reference string
        
        Returns:
            dict: {
                'success': bool,
                'released_items': list,
                'errors': list
            }
        """
        result = {
            'success': True,
            'released_items': [],
            'errors': []
        }
        
        for item in order_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            try:
                inventory_item = InventoryItem.objects.select_for_update().get(
                    product_id=product_id
                )
                
                # Check if enough reserved
                if inventory_item.reserved < quantity:
                    result['success'] = False
                    result['errors'].append(
                        f"Product {product_id}: cannot release {quantity}, "
                        f"only {inventory_item.reserved} reserved"
                    )
                    continue
                
                # Release stock
                inventory_item.reserved -= quantity
                inventory_item.save(update_fields=['reserved'])
                
                # Create movement record
                StockMovement.objects.create(
                    inventory_item=inventory_item,
                    movement_type=StockMovement.MovementType.RETURN_IN,
                    quantity=quantity,
                    reference=reference,
                    notes=f'Released reservation: {reference}'
                )
                
                result['released_items'].append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'inventory_item_id': inventory_item.id
                })
                
            except InventoryItem.DoesNotExist:
                result['success'] = False
                result['errors'].append(f"Product {product_id}: inventory item not found")
        
        return result
    
    @staticmethod
    @transaction.atomic
    def commit_outbound(order_items, reference=''):
        """
        Commit outbound stock (confirm order fulfillment).
        
        Args:
            order_items: List of dicts with 'product_id' and 'quantity'
            reference: Reference string (e.g., order number)
        
        Returns:
            dict: {
                'success': bool,
                'committed_items': list,
                'errors': list
            }
        """
        result = {
            'success': True,
            'committed_items': [],
            'errors': []
        }
        
        for item in order_items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            try:
                inventory_item = InventoryItem.objects.select_for_update().get(
                    product_id=product_id
                )
                
                # Check if enough reserved
                if inventory_item.reserved < quantity:
                    result['success'] = False
                    result['errors'].append(
                        f"Product {product_id}: cannot commit {quantity}, "
                        f"only {inventory_item.reserved} reserved"
                    )
                    continue
                
                # Commit outbound: reduce both reserved and on_hand
                inventory_item.reserved -= quantity
                inventory_item.on_hand -= quantity
                inventory_item.save(update_fields=['reserved', 'on_hand'])
                
                # Create movement record
                StockMovement.objects.create(
                    inventory_item=inventory_item,
                    movement_type=StockMovement.MovementType.OUTBOUND,
                    quantity=-quantity,
                    reference=reference,
                    notes=f'Committed outbound: {reference}'
                )
                
                result['committed_items'].append({
                    'product_id': product_id,
                    'quantity': quantity,
                    'inventory_item_id': inventory_item.id
                })
                
            except InventoryItem.DoesNotExist:
                result['success'] = False
                result['errors'].append(f"Product {product_id}: inventory item not found")
        
        return result
    
    @staticmethod
    @transaction.atomic
    def adjust_inventory(product_id, quantity, reason='', created_by=None):
        """
        Adjust inventory (manual adjustment).
        
        Args:
            product_id: Product ID
            quantity: Quantity change (positive or negative)
            reason: Reason for adjustment
            created_by: User making the adjustment
        
        Returns:
            dict: {
                'success': bool,
                'inventory_item_id': int,
                'new_on_hand': int,
                'errors': list
            }
        """
        result = {
            'success': True,
            'inventory_item_id': None,
            'new_on_hand': None,
            'errors': []
        }
        
        try:
            inventory_item = InventoryItem.objects.select_for_update().get(
                product_id=product_id
            )
            
            # Adjust on_hand
            new_on_hand = inventory_item.on_hand + quantity
            if new_on_hand < 0:
                result['success'] = False
                result['errors'].append(
                    f"Cannot adjust: would result in negative stock ({new_on_hand})"
                )
                return result
            
            inventory_item.on_hand = new_on_hand
            inventory_item.save(update_fields=['on_hand'])
            
            # Create movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type=StockMovement.MovementType.ADJUST,
                quantity=quantity,
                notes=reason,
                created_by=created_by
            )
            
            result['inventory_item_id'] = inventory_item.id
            result['new_on_hand'] = new_on_hand
            
        except InventoryItem.DoesNotExist:
            result['success'] = False
            result['errors'].append(f"Product {product_id}: inventory item not found")
        
        return result
    
    @staticmethod
    @transaction.atomic
    def record_inbound(product_id, quantity, reference='', notes='', created_by=None):
        """
        Record inbound stock (receiving goods).
        
        Args:
            product_id: Product ID
            quantity: Quantity received
            reference: Reference (e.g., PO number)
            notes: Additional notes
            created_by: User recording the inbound
        
        Returns:
            dict: {
                'success': bool,
                'inventory_item_id': int,
                'new_on_hand': int,
                'errors': list
            }
        """
        result = {
            'success': True,
            'inventory_item_id': None,
            'new_on_hand': None,
            'errors': []
        }
        
        try:
            inventory_item = InventoryItem.objects.select_for_update().get(
                product_id=product_id
            )
            
            # Increase on_hand
            inventory_item.on_hand += quantity
            inventory_item.save(update_fields=['on_hand'])
            
            # Create movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type=StockMovement.MovementType.INBOUND,
                quantity=quantity,
                reference=reference,
                notes=notes,
                created_by=created_by
            )
            
            result['inventory_item_id'] = inventory_item.id
            result['new_on_hand'] = inventory_item.on_hand
            
        except InventoryItem.DoesNotExist:
            result['success'] = False
            result['errors'].append(f"Product {product_id}: inventory item not found")
        
        return result
