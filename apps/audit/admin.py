"""
Admin configuration for audit app.
"""
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""
    list_display = ('id', 'user', 'action', 'resource_type', 'ip_address', 'created_at')
    list_filter = ('action', 'resource_type', 'created_at')
    search_fields = ('user__phone_number', 'action', 'resource_type', 'notes')
    readonly_fields = ('user', 'action', 'resource_type', 'content_type', 'object_id', 'old_values', 'new_values', 'ip_address', 'user_agent', 'request_path', 'request_method', 'notes', 'created_at')
    
    fieldsets = (
        ('User & Action', {
            'fields': ('user', 'action', 'resource_type')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id')
        }),
        ('Changes', {
            'fields': ('old_values', 'new_values')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of audit logs."""
        return False

