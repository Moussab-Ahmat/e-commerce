"""Courier API serializers."""
from rest_framework import serializers
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.orders.models import Order


class CourierOrderItemSerializer(serializers.Serializer):
    """Serializer for order items in courier delivery."""
    product_name = serializers.CharField(source='product.name')
    product_image = serializers.SerializerMethodField()
    quantity = serializers.IntegerField()
    price = serializers.IntegerField(source='unit_price')
    subtotal = serializers.IntegerField(source='total_price')

    def get_product_image(self, obj):
        """Get first product image URL."""
        if obj.product.images.exists():
            image = obj.product.images.first()
            request = self.context.get('request')
            if image.thumbnail and request:
                return request.build_absolute_uri(image.thumbnail.url)
            elif image.original and request:
                return request.build_absolute_uri(image.original.url)
        return None


class CourierDeliverySerializer(serializers.ModelSerializer):
    """Serializer for courier deliveries."""
    delivery_number = serializers.CharField(read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    customer_name = serializers.CharField(source='order.user.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='delivery_phone', read_only=True)
    total_amount = serializers.IntegerField(source='order.total', read_only=True)
    items_count = serializers.IntegerField(source='order.items.count', read_only=True)
    items = serializers.SerializerMethodField()

    # Delivery address
    address = serializers.SerializerMethodField()

    # Status and dates
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)
    estimated_delivery_date = serializers.DateTimeField(read_only=True)
    actual_delivery_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'delivery_number', 'order_id', 'order_number',
            'customer_name', 'customer_phone', 'total_amount',
            'items_count', 'items', 'address', 'status',
            'created_at', 'assigned_at', 'estimated_delivery_date',
            'actual_delivery_date', 'delivery_notes', 'fee'
        ]

    def get_items(self, obj):
        """Get order items."""
        items = obj.order.items.all()
        return CourierOrderItemSerializer(items, many=True, context=self.context).data

    def get_address(self, obj):
        """Get formatted delivery address."""
        return {
            'line1': obj.delivery_address_line1,
            'line2': obj.delivery_address_line2,
            'city': obj.delivery_city,
            'region': obj.delivery_region,
            'postal_code': obj.delivery_postal_code,
            'phone': obj.delivery_phone,
        }


class CourierDeliveryUpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating delivery status."""
    status = serializers.ChoiceField(choices=DeliveryStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    failure_reason = serializers.CharField(required=False, allow_blank=True)
