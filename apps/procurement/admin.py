"""
Admin configuration for procurement app.
"""
from django.contrib import admin
from .models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, ReceiptItem
)


class PurchaseOrderItemInline(admin.TabularInline):
    """Inline admin for purchase order items."""
    model = PurchaseOrderItem
    extra = 0
    fields = ('product', 'quantity_ordered', 'unit_price', 'quantity_received', 'quantity_pending')
    readonly_fields = ('quantity_received', 'quantity_pending')


class GoodsReceiptInline(admin.TabularInline):
    """Inline admin for goods receipts."""
    model = GoodsReceipt
    extra = 0
    readonly_fields = ('receipt_number', 'status', 'receipt_date', 'validated_at')
    can_delete = False


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """Admin interface for Supplier model."""
    list_display = ('name', 'code', 'contact_person', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'contact_person')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """Admin interface for PurchaseOrder model."""
    list_display = ('po_number', 'supplier', 'status', 'order_date', 'expected_delivery_date', 'created_at')
    list_filter = ('status', 'supplier', 'order_date', 'created_at')
    search_fields = ('po_number', 'supplier__name', 'supplier__code')
    readonly_fields = ('po_number', 'created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline, GoodsReceiptInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('po_number', 'supplier', 'status', 'order_date', 'expected_delivery_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('User', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class ReceiptItemInline(admin.TabularInline):
    """Inline admin for receipt items."""
    model = ReceiptItem
    extra = 0
    fields = ('purchase_order_item', 'quantity_accepted', 'quantity_rejected', 'rejection_reason')
    readonly_fields = ()


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    """Admin interface for GoodsReceipt model."""
    list_display = ('receipt_number', 'purchase_order', 'status', 'receipt_date', 'validated_at', 'created_at')
    list_filter = ('status', 'receipt_date', 'created_at')
    search_fields = ('receipt_number', 'purchase_order__po_number')
    readonly_fields = ('receipt_number', 'validated_at', 'created_at', 'updated_at')
    inlines = [ReceiptItemInline]
    
    fieldsets = (
        ('Receipt Information', {
            'fields': ('receipt_number', 'purchase_order', 'status', 'receipt_date', 'notes')
        }),
        ('Validation', {
            'fields': ('validated_at', 'validated_by')
        }),
        ('User', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'purchase_order__supplier', 'created_by', 'validated_by'
        )


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    """Admin interface for PurchaseOrderItem model."""
    list_display = ('purchase_order', 'product', 'quantity_ordered', 'quantity_received', 'quantity_pending', 'unit_price')
    list_filter = ('purchase_order__status', 'purchase_order__supplier')
    search_fields = ('purchase_order__po_number', 'product__name', 'product__sku')
    readonly_fields = ('quantity_received', 'quantity_pending')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('purchase_order', 'product')


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    """Admin interface for ReceiptItem model."""
    list_display = ('goods_receipt', 'purchase_order_item', 'quantity_accepted', 'quantity_rejected', 'quantity_total')
    list_filter = ('goods_receipt__status', 'goods_receipt__receipt_date')
    search_fields = ('goods_receipt__receipt_number', 'purchase_order_item__product__name')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'goods_receipt', 'purchase_order_item__product'
        )
