"""
Procurement services with idempotent receipt validation.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import GoodsReceipt, ReceiptItem, PurchaseOrder, PurchaseOrderItem
from apps.inventory.models import InventoryItem, StockMovement


class ProcurementService:
    """Service for procurement operations."""
    
    @staticmethod
    @transaction.atomic
    def validate_receipt(receipt_id, validated_by=None):
        """
        Validate goods receipt and update inventory.
        Idempotent: validating the same receipt twice will not double stock.
        
        Args:
            receipt_id: GoodsReceipt ID
            validated_by: User validating the receipt
        
        Returns:
            dict: {
                'success': bool,
                'receipt_id': int,
                'movements_created': int,
                'items_processed': int,
                'errors': list
            }
        """
        result = {
            'success': True,
            'receipt_id': receipt_id,
            'movements_created': 0,
            'items_processed': 0,
            'errors': []
        }
        
        try:
            receipt = GoodsReceipt.objects.select_for_update().get(pk=receipt_id)
        except GoodsReceipt.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Goods receipt {receipt_id} not found')
            return result
        
        # Check if already validated (idempotency check)
        if receipt.is_validated():
            result['success'] = True
            result['errors'].append('Receipt already validated (idempotent operation)')
            # Return success but don't process again
            return result
        
        if receipt.status != GoodsReceipt.Status.DRAFT:
            result['success'] = False
            result['errors'].append(f'Receipt status is {receipt.status}, cannot validate')
            return result
        
        # Process receipt items
        receipt_items = ReceiptItem.objects.filter(
            goods_receipt=receipt
        ).select_related('purchase_order_item__product')
        
        if not receipt_items.exists():
            result['success'] = False
            result['errors'].append('Receipt has no items')
            return result
        
        # Process each receipt item
        for receipt_item in receipt_items:
            try:
                # Get or create inventory item
                inventory_item, created = InventoryItem.objects.select_for_update().get_or_create(
                    product=receipt_item.purchase_order_item.product,
                    defaults={'on_hand': 0, 'reserved': 0}
                )
                
                # Only process if quantity_accepted > 0
                if receipt_item.quantity_accepted > 0:
                    # Update inventory
                    inventory_item.on_hand += receipt_item.quantity_accepted
                    inventory_item.save(update_fields=['on_hand'])
                    
                    # Create stock movement
                    StockMovement.objects.create(
                        inventory_item=inventory_item,
                        movement_type=StockMovement.MovementType.INBOUND,
                        quantity=receipt_item.quantity_accepted,
                        reference=receipt.receipt_number,
                        notes=f'Goods receipt: {receipt.receipt_number}, PO: {receipt.purchase_order.po_number}'
                    )
                    result['movements_created'] += 1
                
                # Update purchase order item quantity_received
                po_item = receipt_item.purchase_order_item
                po_item.quantity_received += receipt_item.quantity_accepted
                po_item.save(update_fields=['quantity_received'])
                
                result['items_processed'] += 1
                
            except Exception as e:
                result['errors'].append(f'Error processing item {receipt_item.id}: {str(e)}')
                # Continue processing other items
        
        # Update receipt status
        receipt.status = GoodsReceipt.Status.VALIDATED
        receipt.validated_at = timezone.now()
        if validated_by:
            receipt.validated_by = validated_by
        receipt.save(update_fields=['status', 'validated_at', 'validated_by'])
        
        # Update purchase order status if all items received
        purchase_order = receipt.purchase_order
        all_received = all(
            item.quantity_received >= item.quantity_ordered
            for item in purchase_order.items.all()
        )
        partially_received = any(
            item.quantity_received > 0
            for item in purchase_order.items.all()
        )
        
        if all_received:
            purchase_order.status = PurchaseOrder.Status.RECEIVED
        elif partially_received:
            purchase_order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
        purchase_order.save(update_fields=['status'])
        
        return result
    
    @staticmethod
    @transaction.atomic
    def create_receipt(purchase_order_id, receipt_number, receipt_date, items, created_by=None):
        """
        Create a goods receipt.
        
        Args:
            purchase_order_id: PurchaseOrder ID
            receipt_number: Receipt number (must be unique)
            receipt_date: Receipt date
            items: List of dicts with 'purchase_order_item_id', 'quantity_accepted', 'quantity_rejected', 'rejection_reason'
            created_by: User creating the receipt
        
        Returns:
            dict: {
                'success': bool,
                'receipt_id': int,
                'errors': list
            }
        """
        result = {
            'success': True,
            'receipt_id': None,
            'errors': []
        }
        
        try:
            purchase_order = PurchaseOrder.objects.get(pk=purchase_order_id)
        except PurchaseOrder.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Purchase order {purchase_order_id} not found')
            return result
        
        # Check if receipt number already exists
        if GoodsReceipt.objects.filter(receipt_number=receipt_number).exists():
            result['success'] = False
            result['errors'].append(f'Receipt number {receipt_number} already exists')
            return result
        
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number=receipt_number,
            purchase_order=purchase_order,
            receipt_date=receipt_date,
            created_by=created_by
        )
        
        # Create receipt items
        for item_data in items:
            po_item_id = item_data.get('purchase_order_item_id')
            quantity_accepted = item_data.get('quantity_accepted', 0)
            quantity_rejected = item_data.get('quantity_rejected', 0)
            rejection_reason = item_data.get('rejection_reason', '')
            
            try:
                po_item = PurchaseOrderItem.objects.get(
                    pk=po_item_id,
                    purchase_order=purchase_order
                )
                
                # Validate quantities
                total_quantity = quantity_accepted + quantity_rejected
                pending_quantity = po_item.quantity_pending
                
                if total_quantity > pending_quantity:
                    result['errors'].append(
                        f'PO Item {po_item_id}: total quantity ({total_quantity}) exceeds pending ({pending_quantity})'
                    )
                    continue
                
                ReceiptItem.objects.create(
                    goods_receipt=receipt,
                    purchase_order_item=po_item,
                    quantity_accepted=quantity_accepted,
                    quantity_rejected=quantity_rejected,
                    rejection_reason=rejection_reason
                )
                
            except PurchaseOrderItem.DoesNotExist:
                result['errors'].append(f'Purchase order item {po_item_id} not found')
        
        if result['errors']:
            result['success'] = False
        else:
            result['receipt_id'] = receipt.id
        
        return result
