"""
Inventory models: InventoryItem and StockMovement.
"""
from django.db import models
from django.core.validators import MinValueValidator
from core.validators import validate_xaf_amount


class InventoryItem(models.Model):
    """Inventory item tracking on-hand and reserved quantities."""
    
    product = models.OneToOneField(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='inventory_item'
    )
    on_hand = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Available quantity on hand'
    )
    reserved = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Reserved quantity for pending orders'
    )
    reorder_point = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Reorder point threshold'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_items'
        indexes = [
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f'{self.product.name} - On Hand: {self.on_hand}, Reserved: {self.reserved}'
    
    @property
    def available(self):
        """Calculate available quantity (on_hand - reserved)."""
        return max(0, self.on_hand - self.reserved)
    
    @property
    def needs_reorder(self):
        """Check if item needs reordering."""
        return self.on_hand <= self.reorder_point


class StockMovement(models.Model):
    """Stock movement tracking."""
    
    class MovementType(models.TextChoices):
        INBOUND = 'INBOUND', 'Inbound'
        OUTBOUND = 'OUTBOUND', 'Outbound'
        ADJUST = 'ADJUST', 'Adjustment'
        RETURN_IN = 'RETURN_IN', 'Return In'
        DAMAGED = 'DAMAGED', 'Damaged'
    
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        db_index=True
    )
    quantity = models.IntegerField(
        help_text='Quantity change (positive for INBOUND/RETURN_IN, negative for OUTBOUND/DAMAGED)'
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Reference (e.g., order number, PO number)'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory_item', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['reference']),
        ]
    
    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.inventory_item.product.name} - Qty: {self.quantity}'
