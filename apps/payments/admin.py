"""
Admin configuration for payments app.
"""
from django.contrib import admin
from .models import Payment, PaymentHistory


class PaymentHistoryInline(admin.TabularInline):
    """Inline admin for payment history."""
    model = PaymentHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'created_at')
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    list_display = ('payment_number', 'order', 'amount', 'status', 'payment_method', 'collected_by', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('payment_number', 'order__order_number')
    readonly_fields = ('payment_number', 'created_at', 'updated_at', 'collected_at')
    inlines = [PaymentHistoryInline]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_number', 'order', 'amount', 'payment_method', 'status')
        }),
        ('COD Details', {
            'fields': ('collected_by', 'collected_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

