"""
Procurement models: Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, ReceiptItem.
"""
from django.db import models
from django.core.validators import MinValueValidator
from core.validators import validate_xaf_amount


class Supplier(models.Model):
    """Supplier model."""
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.code})'


class PurchaseOrder(models.Model):
    """Purchase order model."""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED', 'Partially Received'
        RECEIVED = 'RECEIVED', 'Received'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    po_number = models.CharField(max_length=50, unique=True, db_index=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_purchase_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f'PO {self.po_number} - {self.supplier.name}'


class PurchaseOrderItem(models.Model):
    """Purchase order item model."""
    
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='purchase_order_items'
    )
    quantity_ordered = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text='Quantity ordered'
    )
    unit_price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Unit price in XAF'
    )
    quantity_received = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total quantity received across all receipts'
    )
    
    class Meta:
        db_table = 'purchase_order_items'
        unique_together = [['purchase_order', 'product']]
    
    def __str__(self):
        return f'{self.purchase_order.po_number} - {self.product.name}'
    
    @property
    def total_price(self):
        """Calculate total price."""
        return self.quantity_ordered * self.unit_price
    
    @property
    def quantity_pending(self):
        """Calculate pending quantity."""
        return max(0, self.quantity_ordered - self.quantity_received)


class GoodsReceipt(models.Model):
    """Goods receipt model."""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        VALIDATED = 'VALIDATED', 'Validated'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    receipt_number = models.CharField(max_length=50, unique=True, db_index=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='goods_receipts'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    receipt_date = models.DateField()
    notes = models.TextField(blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_receipts'
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_receipts',
        related_query_name='created_receipt'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'goods_receipts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['receipt_number']),
            models.Index(fields=['purchase_order', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f'GR {self.receipt_number} - PO {self.purchase_order.po_number}'
    
    def is_validated(self):
        """Check if receipt is validated."""
        return self.status == self.Status.VALIDATED and self.validated_at is not None


class ReceiptItem(models.Model):
    """Receipt item model."""
    
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name='items'
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name='receipt_items'
    )
    quantity_accepted = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text='Quantity accepted'
    )
    quantity_rejected = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Quantity rejected'
    )
    rejection_reason = models.TextField(blank=True, help_text='Reason for rejection')
    
    class Meta:
        db_table = 'receipt_items'
        unique_together = [['goods_receipt', 'purchase_order_item']]
    
    def __str__(self):
        return f'{self.goods_receipt.receipt_number} - {self.purchase_order_item.product.name}'
    
    @property
    def quantity_total(self):
        """Calculate total quantity (accepted + rejected)."""
        return self.quantity_accepted + self.quantity_rejected
