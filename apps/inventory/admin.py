"""
Admin configuration for inventory app.
"""
from django.contrib import admin
from .models import InventoryItem, StockMovement


class StockMovementInline(admin.TabularInline):
    """Inline admin for stock movements."""
    model = StockMovement
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('movement_type', 'quantity', 'reference', 'notes', 'created_by', 'created_at')
    can_delete = False


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """Admin interface for InventoryItem model."""
    list_display = ('product', 'on_hand', 'reserved', 'available', 'reorder_point', 'needs_reorder', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('available', 'needs_reorder', 'created_at', 'updated_at')
    inlines = [StockMovementInline]
    
    fieldsets = (
        ('Product', {
            'fields': ('product',)
        }),
        ('Stock Levels', {
            'fields': ('on_hand', 'reserved', 'available')
        }),
        ('Reorder Settings', {
            'fields': ('reorder_point', 'needs_reorder')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('product')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Admin interface for StockMovement model."""
    list_display = ('inventory_item', 'movement_type', 'quantity', 'reference', 'created_by', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('inventory_item__product__name', 'reference', 'notes')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Movement Information', {
            'fields': ('inventory_item', 'movement_type', 'quantity', 'reference', 'notes')
        }),
        ('User', {
            'fields': ('created_by',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'inventory_item__product', 'created_by'
        )
