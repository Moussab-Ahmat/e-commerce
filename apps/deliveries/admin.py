"""
Admin configuration for deliveries app.
"""
from django.contrib import admin
from .models import DeliveryAgent, Delivery, DeliveryStatusHistory


@admin.register(DeliveryAgent)
class DeliveryAgentAdmin(admin.ModelAdmin):
    """Admin interface for DeliveryAgent model."""
    list_display = ('agent_id', 'user', 'vehicle_type', 'phone_number', 'is_active', 'created_at')
    list_filter = ('vehicle_type', 'is_active', 'created_at')
    search_fields = ('agent_id', 'user__phone_number', 'user__email', 'vehicle_number')


class DeliveryStatusHistoryInline(admin.TabularInline):
    """Inline admin for delivery status history."""
    model = DeliveryStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'created_at')
    can_delete = False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Admin interface for Delivery model."""
    list_display = ('delivery_number', 'order', 'status', 'agent', 'estimated_delivery_date', 'created_at')
    list_filter = ('status', 'created_at', 'agent')
    search_fields = ('delivery_number', 'order__order_number')
    readonly_fields = ('delivery_number', 'created_at', 'updated_at', 'assigned_at', 'completed_at', 'actual_delivery_date')
    inlines = [DeliveryStatusHistoryInline]
    
    fieldsets = (
        ('Delivery Information', {
            'fields': ('delivery_number', 'order', 'status', 'agent')
        }),
        ('Delivery Address', {
            'fields': ('delivery_address_line1', 'delivery_address_line2', 'delivery_city', 'delivery_region', 'delivery_postal_code', 'delivery_phone')
        }),
        ('Delivery Details', {
            'fields': ('estimated_delivery_date', 'actual_delivery_date', 'delivery_notes', 'failure_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'assigned_at', 'completed_at')
        }),
    )

