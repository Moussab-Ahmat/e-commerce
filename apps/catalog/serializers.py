"""
Serializers for catalog app.
"""
from rest_framework import serializers
from .models import Category, Product, ProductImage


def build_absolute_url(request, relative_url):
    """Build absolute URL from relative path."""
    if not relative_url:
        return None
    if request:
        return request.build_absolute_uri(relative_url)
    return relative_url


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer."""

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'is_active')
        read_only_fields = ('id', 'slug')


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer with absolute URLs."""
    original = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'original', 'thumbnail', 'alt_text', 'order', 'is_primary')
        read_only_fields = ('id',)

    def get_original(self, obj):
        request = self.context.get('request')
        if obj.original:
            return build_absolute_url(request, obj.original.url)
        return None

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.thumbnail:
            return build_absolute_url(request, obj.thumbnail.url)
        return None


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight product serializer for list view."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category_name', 'price',
            'effective_price', 'discount', 'is_on_sale',
            'stock_quantity', 'sku', 'is_featured', 'primary_image'
        )

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_discount(self, obj):
        return obj.get_discount_percentage()

    def get_primary_image(self, obj):
        """Get primary image thumbnail URL as string (for Flutter compatibility).
        Returns relative URL path (e.g., /media/...) for client-side base URL handling.
        """
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            if primary.thumbnail:
                return primary.thumbnail.url
            if primary.original:
                return primary.original.url
        first_image = obj.images.first()
        if first_image:
            if first_image.thumbnail:
                return first_image.thumbnail.url
            if first_image.original:
                return first_image.original.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product serializer for detail view."""
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    savings = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'category',
            'price', 'effective_price', 'discount', 'savings',
            'is_on_sale', 'sale_end_date',
            'stock_quantity', 'sku',
            'is_active', 'is_featured',
            'images', 'primary_image',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_discount(self, obj):
        return obj.get_discount_percentage()

    def get_savings(self, obj):
        return obj.get_savings()

    def get_primary_image(self, obj):
        """Get primary image thumbnail URL as string.
        Returns relative URL path (e.g., /media/...) for client-side base URL handling.
        """
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            if primary.thumbnail:
                return primary.thumbnail.url
            if primary.original:
                return primary.original.url
        first_image = obj.images.first()
        if first_image:
            if first_image.thumbnail:
                return first_image.thumbnail.url
            if first_image.original:
                return first_image.original.url
        return None

