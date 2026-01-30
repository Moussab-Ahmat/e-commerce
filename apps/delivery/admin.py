"""
Admin configuration for delivery app.
"""
from django.contrib import admin
from .models import DeliveryZone, DeliveryFeeRule


class DeliveryFeeRuleInline(admin.TabularInline):
    """Inline admin for delivery fee rules."""
    model = DeliveryFeeRule
    extra = 0
    fields = ('rule_type', 'priority', 'is_active', 'fixed_fee', 'percentage', 'min_fee', 'max_fee')


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    """Admin interface for DeliveryZone model."""
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DeliveryFeeRuleInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DeliveryFeeRule)
class DeliveryFeeRuleAdmin(admin.ModelAdmin):
    """Admin interface for DeliveryFeeRule model."""
    list_display = ('zone', 'rule_type', 'priority', 'is_active', 'created_at')
    list_filter = ('zone', 'rule_type', 'is_active', 'priority', 'created_at')
    search_fields = ('zone__name', 'zone__code')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Rule Information', {
            'fields': ('zone', 'rule_type', 'priority', 'is_active')
        }),
        ('Fixed Fee (for FIXED type)', {
            'fields': ('fixed_fee',),
            'classes': ('collapse',)
        }),
        ('Percentage Fee (for PERCENTAGE type)', {
            'fields': ('percentage', 'min_fee', 'max_fee'),
            'classes': ('collapse',)
        }),
        ('Tiered Rules (for TIERED type)', {
            'fields': ('tier_rules',),
            'description': 'JSON format: [{"min": 0, "max": 10000, "fee": 2000}, ...]',
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

