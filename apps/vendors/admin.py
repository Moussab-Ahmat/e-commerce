"""Django admin for Vendors app."""
from django.contrib import admin
from django.utils.html import format_html
from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Admin for Shop model."""

    list_display = [
        'name',
        'vendor_name',
        'status_badge',
        'is_verified',
        'products_count',
        'total_sales',
        'created_at',
    ]
    list_filter = ['status', 'is_verified', 'created_at']
    search_fields = ['name', 'vendor__email', 'vendor__phone_number', 'email', 'phone']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'approved_at', 'approved_by']

    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'name', 'slug', 'description', 'logo', 'banner')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Business Information', {
            'fields': ('business_license', 'tax_id')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'region', 'postal_code')
        }),
        ('Status', {
            'fields': ('status', 'is_verified', 'average_rating', 'total_sales')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at', 'approved_by')
        }),
    )

    def vendor_name(self, obj):
        """Display vendor name."""
        return obj.vendor.get_full_name()
    vendor_name.short_description = 'Vendor'

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'PENDING': '#FFA500',
            'ACTIVE': '#28A745',
            'SUSPENDED': '#DC3545',
            'INACTIVE': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def products_count(self, obj):
        """Display product count."""
        return obj.products_count
    products_count.short_description = 'Products'

    actions = ['activate_shops', 'suspend_shops']

    def activate_shops(self, request, queryset):
        """Activate selected shops."""
        for shop in queryset:
            shop.activate(request.user)
        self.message_user(request, f'{queryset.count()} shop(s) activated successfully.')
    activate_shops.short_description = 'Activate selected shops'

    def suspend_shops(self, request, queryset):
        """Suspend selected shops."""
        queryset.update(status=Shop.Status.SUSPENDED)
        self.message_user(request, f'{queryset.count()} shop(s) suspended.')
    suspend_shops.short_description = 'Suspend selected shops'
