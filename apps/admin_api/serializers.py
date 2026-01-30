"""
Admin API serializers for managing categories, couriers, orders, products, and vendors.
"""
from rest_framework import serializers
from apps.catalog.models import Category, Product
from apps.accounts.models import User
from apps.deliveries.models import DeliveryAgent, Delivery, DeliveryStatus
from apps.orders.models import Order
from apps.vendors.models import Shop
import uuid


# ============ CATEGORY SERIALIZERS ============

class AdminCategorySerializer(serializers.ModelSerializer):
    """Full category serializer with image upload and product count."""
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'parent',
            'image', 'is_active', 'product_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_product_count(self, obj):
        """Get count of active products in this category."""
        return obj.products.filter(is_active=True).count()

    def validate_parent(self, value):
        """Prevent circular parent references."""
        if value and self.instance:
            if value.id == self.instance.id:
                raise serializers.ValidationError("Category cannot be its own parent")

            # Check for circular reference
            parent = value
            while parent.parent:
                if parent.parent.id == self.instance.id:
                    raise serializers.ValidationError("Circular parent reference detected")
                parent = parent.parent
        return value


# ============ COURIER SERIALIZERS ============

class AdminCourierSerializer(serializers.ModelSerializer):
    """Full courier user serializer for admin with delivery agent and stats."""
    delivery_agent = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'is_active', 'is_verified',
            'delivery_agent', 'stats',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['role', 'date_joined', 'last_login']

    def get_delivery_agent(self, obj):
        """Get delivery agent information if exists."""
        try:
            agent = obj.delivery_agent
            return {
                'id': agent.id,
                'agent_id': agent.agent_id,
                'vehicle_type': agent.vehicle_type,
                'vehicle_number': agent.vehicle_number,
                'phone_number': agent.phone_number
            }
        except:
            return None

    def get_stats(self, obj):
        """Get courier delivery statistics."""
        try:
            deliveries = Delivery.objects.filter(agent__user=obj)
            total = deliveries.count()
            completed = deliveries.filter(status=DeliveryStatus.COMPLETED).count()
            in_progress = deliveries.filter(
                status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT]
            ).count()
            failed = deliveries.filter(status=DeliveryStatus.FAILED).count()

            return {
                'total_deliveries': total,
                'completed': completed,
                'in_progress': in_progress,
                'failed': failed
            }
        except:
            return {
                'total_deliveries': 0,
                'completed': 0,
                'in_progress': 0,
                'failed': 0
            }


class AdminCourierCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new courier users with delivery agent."""
    vehicle_type = serializers.ChoiceField(
        choices=[
            ('MOTORCYCLE', 'Motorcycle'),
            ('CAR', 'Car'),
            ('TRUCK', 'Truck'),
            ('BICYCLE', 'Bicycle')
        ],
        write_only=True
    )
    vehicle_number = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True
    )
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'email', 'phone_number', 'first_name', 'last_name',
            'password', 'vehicle_type', 'vehicle_number'
        ]

    def validate(self, attrs):
        """Ensure at least email or phone is provided."""
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError(
                "Either email or phone_number must be provided"
            )
        return attrs

    def create(self, validated_data):
        """Create user with COURIER role and delivery agent."""
        vehicle_type = validated_data.pop('vehicle_type')
        vehicle_number = validated_data.pop('vehicle_number', '')
        password = validated_data.pop('password')

        # Create user with COURIER role
        user = User.objects.create_user(
            **validated_data,
            role='COURIER'
        )
        user.set_password(password)
        user.is_verified = True
        user.save()

        # Create DeliveryAgent
        DeliveryAgent.objects.create(
            user=user,
            agent_id=f'COU{uuid.uuid4().hex[:8].upper()}',
            vehicle_type=vehicle_type,
            vehicle_number=vehicle_number,
            phone_number=user.phone_number or user.email
        )

        return user


class AdminCourierStatsSerializer(serializers.Serializer):
    """Detailed courier statistics serializer."""
    total_deliveries = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    failed = serializers.IntegerField()
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_delivery_time = serializers.IntegerField()  # in minutes


# ============ ORDER SERIALIZERS ============

class AdminOrderSerializer(serializers.ModelSerializer):
    """Admin order serializer with all details."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    courier_name = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_name',
            'status', 'status_display',
            'subtotal', 'delivery_fee', 'total',
            'delivery_address_line1', 'delivery_city',
            'delivery_phone', 'courier', 'courier_name',
            'items_count', 'estimated_minutes',
            'created_at', 'confirmed_at', 'delivered_at'
        ]

    def get_courier_name(self, obj):
        """Get courier full name if assigned."""
        return obj.courier.get_full_name() if obj.courier else None

    def get_items_count(self, obj):
        """Get count of items in order."""
        return obj.items.count()


class AdminAssignCourierSerializer(serializers.Serializer):
    """Serializer for assigning courier to order."""
    courier_id = serializers.IntegerField()
    estimated_minutes = serializers.IntegerField(required=False, allow_null=True)

    def validate_courier_id(self, value):
        """Validate courier exists and is active."""
        try:
            courier = User.objects.get(id=value, role='COURIER', is_active=True)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid courier ID or courier is inactive"
            )


# ============ PRODUCT SERIALIZERS ============

class AdminProductSerializer(serializers.ModelSerializer):
    """Admin product serializer with full control."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True, allow_null=True)
    images = serializers.SerializerMethodField()
    effective_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    savings = serializers.SerializerMethodField()
    sale_active = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'sku',
            'category', 'category_name', 'shop', 'shop_name',
            'price', 'stock_quantity', 'images',
            'is_active', 'is_featured', 'is_published',
            'is_on_sale', 'sale_price', 'sale_start_date', 'sale_end_date',
            'effective_price', 'discount_percentage', 'savings', 'sale_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_images(self, obj):
        """Get product images with full URLs."""
        request = self.context.get('request')
        images = []
        for img in obj.images.all():
            if img.original and request:
                images.append({
                    'id': img.id,
                    'url': request.build_absolute_uri(img.original.url),
                    'is_primary': img.is_primary
                })
        return images

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_discount_percentage(self, obj):
        return obj.get_discount_percentage()

    def get_savings(self, obj):
        return obj.get_savings()

    def get_sale_active(self, obj):
        return obj.is_sale_active()


class AdminProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new products with validation."""

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'sku', 'category', 'shop',
            'price', 'stock_quantity', 'is_active', 'is_featured',
            'is_published',
            'is_on_sale', 'sale_price', 'sale_start_date', 'sale_end_date',
        ]

    def validate_sku(self, value):
        """Ensure SKU is unique."""
        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate_price(self, value):
        """Ensure price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate(self, attrs):
        """Validate promotion fields."""
        if attrs.get('is_on_sale'):
            sale_price = attrs.get('sale_price')
            price = attrs.get('price')
            if not sale_price:
                raise serializers.ValidationError({
                    'sale_price': 'Le prix promotionnel est requis pour une promotion.'
                })
            if price and sale_price >= price:
                raise serializers.ValidationError({
                    'sale_price': 'Le prix promo doit etre inferieur au prix normal.'
                })
            start = attrs.get('sale_start_date')
            end = attrs.get('sale_end_date')
            if start and end and start >= end:
                raise serializers.ValidationError({
                    'sale_end_date': 'La date de fin doit etre apres la date de debut.'
                })
        return attrs


class AdminStockUpdateSerializer(serializers.Serializer):
    """Serializer for stock updates."""
    stock_quantity = serializers.IntegerField(min_value=0)
    operation = serializers.ChoiceField(
        choices=['set', 'add', 'subtract'],
        default='set'
    )


# ============ VENDOR SERIALIZERS ============

class AdminVendorSerializer(serializers.ModelSerializer):
    """Admin vendor/shop serializer."""
    vendor_name = serializers.CharField(source='vendor.get_full_name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'slug', 'vendor', 'vendor_name', 'vendor_email',
            'email', 'phone', 'status', 'is_verified',
            'products_count', 'average_rating', 'total_sales',
            'created_at', 'approved_at', 'approved_by'
        ]
        read_only_fields = ['slug', 'vendor', 'approved_at', 'approved_by']
