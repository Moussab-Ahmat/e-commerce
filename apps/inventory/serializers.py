"""
Serializers for inventory app.
"""
from rest_framework import serializers
from .models import InventoryItem, StockMovement


class InventoryItemSerializer(serializers.ModelSerializer):
    """Inventory item serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    available = serializers.ReadOnlyField()
    needs_reorder = serializers.ReadOnlyField()
    
    class Meta:
        model = InventoryItem
        fields = (
            'id', 'product', 'product_name', 'product_sku',
            'on_hand', 'reserved', 'available',
            'reorder_point', 'needs_reorder',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class StockMovementSerializer(serializers.ModelSerializer):
    """Stock movement serializer."""
    inventory_item_id = serializers.IntegerField(source='inventory_item.id', read_only=True)
    product_name = serializers.CharField(source='inventory_item.product.name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = (
            'id', 'inventory_item', 'inventory_item_id', 'product_name',
            'movement_type', 'movement_type_display',
            'quantity', 'reference', 'notes',
            'created_by', 'created_by_name',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')
