"""
Admin configuration for risk app.
"""
from django.contrib import admin
from .models import Blacklist, CodLimitRule


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    """Admin interface for Blacklist model."""
    list_display = ('phone_number', 'reason', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('phone_number', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Blacklist Information', {
            'fields': ('phone_number', 'reason', 'is_active')
        }),
        ('User', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(CodLimitRule)
class CodLimitRuleAdmin(admin.ModelAdmin):
    """Admin interface for CodLimitRule model."""
    list_display = ('limit_amount_xaf', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Limit Information', {
            'fields': ('limit_amount_xaf', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
