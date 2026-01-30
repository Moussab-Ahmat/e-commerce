"""
Admin configuration for notifications app.
"""
from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin interface for NotificationLog model."""
    list_display = (
        'id', 'recipient_phone', 'notification_type', 'status',
        'retry_count', 'max_retries', 'created_at', 'sent_at'
    )
    list_filter = ('status', 'notification_type', 'created_at')
    search_fields = ('recipient_phone', 'message', 'order__order_number')
    readonly_fields = ('created_at', 'sent_at', 'updated_at', 'last_retry_at')
    
    fieldsets = (
        ('Recipient', {
            'fields': ('recipient_phone',)
        }),
        ('Notification', {
            'fields': ('notification_type', 'message', 'status')
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'max_retries', 'last_retry_at', 'error_message')
        }),
        ('Related Objects', {
            'fields': ('order', 'delivery')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at', 'updated_at')
        }),
    )
