"""
Serializers for products app.
"""
from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer."""
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'image', 'is_active')
        read_only_fields = ('id', 'slug')


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer."""
    
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'order')


class ProductSerializer(serializers.ModelSerializer):
    """Product serializer."""
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    available_quantity = serializers.ReadOnlyField()
    images = ProductImageSerializer(source='additional_images', many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'category', 'category_id',
            'price', 'stock_quantity', 'reserved_quantity', 'available_quantity',
            'sku', 'barcode', 'weight', 'dimensions',
            'image1', 'image2', 'image3', 'images',
            'is_active', 'is_featured', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'reserved_quantity', 'available_quantity', 'created_at', 'updated_at')


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight product serializer for list views (low bandwidth)."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    available_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category_name', 'price',
            'available_quantity', 'image1', 'is_featured'
        )

