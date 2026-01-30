"""
Admin configuration for orders app.
"""
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price', 'total_price')
    fields = ('product', 'quantity', 'unit_price', 'total_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    list_display = ('order_number', 'user', 'status', 'total', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'user__phone_number', 'user__email')
    readonly_fields = ('order_number', 'subtotal', 'total', 'idempotency_key', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at', 'delivered_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'idempotency_key', 'payment_method', 'payment_status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'delivery_fee', 'total')
        }),
        ('Delivery Information', {
            'fields': ('delivery_zone', 'delivery_address_line1', 'delivery_address_line2', 'delivery_city', 'delivery_region', 'delivery_postal_code', 'delivery_phone')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at', 'delivered_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user', 'delivery_zone')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for OrderItem model."""
    list_display = ('order', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__status', 'order__created_at')
    search_fields = ('order__order_number', 'product__name', 'product__sku')
    readonly_fields = ('unit_price', 'total_price')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('order', 'product')
