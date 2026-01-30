"""
Admin configuration for products app.
"""
from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images."""
    model = ProductImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    list_display = ('name', 'slug', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""
    list_display = ('name', 'sku', 'category', 'price', 'stock_quantity', 'available_quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'sku', 'barcode', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('reserved_quantity', 'available_quantity', 'created_at', 'updated_at')
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category', 'sku', 'barcode')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_quantity', 'reserved_quantity', 'available_quantity')
        }),
        ('Product Details', {
            'fields': ('weight', 'dimensions')
        }),
        ('Images', {
            'fields': ('image1', 'image2', 'image3')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

