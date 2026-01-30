"""
Serializers for vendor endpoints.
"""
from rest_framework import serializers
from .models import Shop
from apps.catalog.models import Product
from apps.orders.models import OrderItem


class ShopSerializer(serializers.ModelSerializer):
    """
    Shop serializer for vendor dashboard.
    """

    vendor_name = serializers.CharField(source='vendor.get_full_name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    products_count = serializers.IntegerField(read_only=True)
    pending_orders_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner',
            'email', 'phone',
            'business_license', 'tax_id',
            'address_line1', 'address_line2', 'city', 'region', 'postal_code',
            'status', 'is_verified',
            'average_rating', 'total_sales',
            'vendor_name', 'vendor_email',
            'products_count', 'pending_orders_count',
            'created_at', 'approved_at',
        ]
        read_only_fields = ['slug', 'status', 'is_verified', 'total_sales', 'average_rating', 'approved_at']


class VendorProductSerializer(serializers.ModelSerializer):
    """
    Product serializer for vendors (includes shop auto-assignment).
    """

    category_id = serializers.IntegerField(source='category.id', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    shop_id = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    compare_at_price = serializers.SerializerMethodField()
    cost_per_item = serializers.SerializerMethodField()
    low_stock_threshold = serializers.SerializerMethodField()
    track_inventory = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'description',
            'category', 'category_id', 'category_name',
            'shop', 'shop_id', 'shop_name',
            'price', 'compare_at_price', 'cost_per_item',
            'stock_quantity', 'low_stock_threshold', 'track_inventory',
            'is_active', 'is_featured',
            'images', 'thumbnail_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['slug', 'shop', 'shop_id', 'shop_name']

    def get_shop_id(self, obj):
        """Get shop ID"""
        return obj.shop.id if obj.shop else None

    def get_shop_name(self, obj):
        """Get shop name"""
        return obj.shop.name if obj.shop else None

    def get_thumbnail_url(self, obj):
        """Get the first product image as thumbnail"""
        if obj.images.exists():
            first_image = obj.images.first()
            if first_image and first_image.image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(first_image.image.url)
        return None

    def get_images(self, obj):
        """Get all product image URLs"""
        request = self.context.get('request')
        images = []
        for img in obj.images.all():
            if img.image and request:
                images.append(request.build_absolute_uri(img.image.url))
        return images

    def get_compare_at_price(self, obj):
        """Return None as this field doesn't exist in the model yet"""
        return None

    def get_cost_per_item(self, obj):
        """Return None as this field doesn't exist in the model yet"""
        return None

    def get_low_stock_threshold(self, obj):
        """Return default threshold"""
        return 10

    def get_track_inventory(self, obj):
        """Return True as default"""
        return True

    def create(self, validated_data):
        """
        Auto-assign shop from request user when creating product.
        """
        request = self.context.get('request')
        if request and hasattr(request.user, 'shop'):
            validated_data['shop'] = request.user.shop

        # Remove fields that don't exist in Product model
        validated_data.pop('compare_at_price', None)
        validated_data.pop('cost_per_item', None)
        validated_data.pop('low_stock_threshold', None)
        validated_data.pop('track_inventory', None)

        return super().create(validated_data)


class VendorProductListSerializer(serializers.ModelSerializer):
    """
    Simplified product serializer for list views.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug',
            'category_name',
            'price', 'stock_quantity',
            'is_active', 'is_featured',
            'created_at',
        ]


class VendorOrderItemSerializer(serializers.ModelSerializer):
    """
    OrderItem serializer for vendors (their items only).
    """

    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.user.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='order.delivery_phone', read_only=True)
    delivery_address = serializers.CharField(source='order.delivery_address_line1', read_only=True)
    delivery_city = serializers.CharField(source='order.delivery_city', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_created = serializers.DateTimeField(source='order.created_at', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order', 'order_number', 'order_status', 'order_created',
            'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'total_price',
            'item_status',
            'customer_name', 'customer_phone',
            'delivery_address', 'delivery_city',
        ]
        read_only_fields = [
            'order', 'product', 'quantity', 'unit_price', 'total_price',
            'order_number', 'product_name',
        ]


class VendorStatsSerializer(serializers.Serializer):
    """
    Serializer for vendor dashboard statistics.
    """

    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_sales = serializers.IntegerField()
    total_revenue = serializers.IntegerField()
    this_month_revenue = serializers.IntegerField()
