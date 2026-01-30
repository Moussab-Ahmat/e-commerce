"""
Serializers for orders app.
"""
from rest_framework import serializers
from .models import Order, OrderItem
from apps.catalog.serializers import ProductListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer."""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_id', 'quantity', 'unit_price', 'total_price')
        read_only_fields = ('id', 'unit_price', 'total_price')


class CourierSerializer(serializers.Serializer):
    """Lightweight courier serializer for order tracking."""
    id = serializers.IntegerField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        if instance is None:
            return None
        return {
            'id': instance.id,
            'phone_number': instance.phone_number,
            'first_name': instance.first_name or '',
            'last_name': instance.last_name or '',
            'display_name': instance.get_full_name(),
        }


class OrderSerializer(serializers.ModelSerializer):
    """Order serializer."""
    items = OrderItemSerializer(many=True, read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    delivery_zone_name = serializers.CharField(source='delivery_zone.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    courier = CourierSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'user', 'user_phone', 'status', 'status_display',
            'subtotal', 'delivery_fee', 'total',
            'delivery_zone', 'delivery_zone_name',
            'delivery_latitude', 'delivery_longitude',
            'delivery_address_line1', 'delivery_address_line2',
            'delivery_city', 'delivery_region', 'delivery_postal_code', 'delivery_phone',
            'payment_method', 'payment_status',
            'customer_notes', 'admin_notes',
            'courier', 'estimated_minutes', 'last_status_update',
            'items',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at', 'delivered_at'
        )
        read_only_fields = (
            'id', 'order_number', 'user', 'subtotal', 'delivery_fee', 'total',
            'courier', 'estimated_minutes', 'last_status_update',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at', 'delivered_at'
        )


class OrderCreateSerializer(serializers.Serializer):
    """Order creation serializer."""
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text='List of items: [{"product_id": 1, "quantity": 2}, ...]'
    )

    # Delivery - coordinates (primary method for new orders)
    delivery_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        help_text='Delivery location latitude'
    )
    delivery_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        help_text='Delivery location longitude'
    )

    # Delivery - zone (for fee calculation)
    delivery_zone_id = serializers.IntegerField(required=False, allow_null=True)

    # Delivery - address (auto-generated from coordinates or manual)
    delivery_address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    delivery_address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    delivery_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    delivery_region = serializers.CharField(max_length=100, required=False, allow_blank=True)
    delivery_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    delivery_phone = serializers.CharField(max_length=15)

    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """Validate items list."""
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError('Each item must have product_id')
            if 'quantity' not in item or item['quantity'] < 1:
                raise serializers.ValidationError('Each item must have quantity >= 1')
        return value

    def validate(self, data):
        """Validate that either coordinates OR zone+address are provided."""
        has_coords = data.get('delivery_latitude') and data.get('delivery_longitude')
        has_traditional = data.get('delivery_zone_id') and data.get('delivery_address_line1')

        if not (has_coords or has_traditional):
            raise serializers.ValidationError(
                'Must provide either GPS coordinates (delivery_latitude and delivery_longitude) '
                'OR zone with address (delivery_zone_id and delivery_address_line1)'
            )

        return data
