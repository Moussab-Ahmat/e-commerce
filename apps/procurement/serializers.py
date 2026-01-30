"""
Serializers for procurement app.
"""
from rest_framework import serializers
from .models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, ReceiptItem
)


class SupplierSerializer(serializers.ModelSerializer):
    """Supplier serializer."""
    
    class Meta:
        model = Supplier
        fields = (
            'id', 'name', 'code', 'contact_person', 'email',
            'phone', 'address', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Purchase order item serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    total_price = serializers.ReadOnlyField()
    quantity_pending = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseOrderItem
        fields = (
            'id', 'purchase_order', 'product', 'product_name', 'product_sku',
            'quantity_ordered', 'unit_price', 'total_price',
            'quantity_received', 'quantity_pending'
        )
        read_only_fields = ('id', 'quantity_received')


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Purchase order serializer."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = (
            'id', 'po_number', 'supplier', 'supplier_name',
            'status', 'order_date', 'expected_delivery_date',
            'notes', 'items',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'po_number', 'created_at', 'updated_at')


class ReceiptItemSerializer(serializers.ModelSerializer):
    """Receipt item serializer."""
    product_name = serializers.CharField(source='purchase_order_item.product.name', read_only=True)
    product_sku = serializers.CharField(source='purchase_order_item.product.sku', read_only=True)
    quantity_total = serializers.ReadOnlyField()
    
    class Meta:
        model = ReceiptItem
        fields = (
            'id', 'goods_receipt', 'purchase_order_item',
            'product_name', 'product_sku',
            'quantity_accepted', 'quantity_rejected', 'quantity_total',
            'rejection_reason'
        )
        read_only_fields = ('id',)


class GoodsReceiptSerializer(serializers.ModelSerializer):
    """Goods receipt serializer."""
    purchase_order_po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    items = ReceiptItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.get_full_name', read_only=True)
    is_validated = serializers.SerializerMethodField()
    
    class Meta:
        model = GoodsReceipt
        fields = (
            'id', 'receipt_number', 'purchase_order', 'purchase_order_po_number',
            'supplier_name', 'status', 'receipt_date', 'notes',
            'items', 'is_validated',
            'validated_at', 'validated_by', 'validated_by_name',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'receipt_number', 'validated_at', 'created_at', 'updated_at')
    
    def get_is_validated(self, obj):
        """Check if receipt is validated."""
        return obj.is_validated()
