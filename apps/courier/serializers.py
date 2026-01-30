"""
Serializers for courier app.
"""
from rest_framework import serializers
from apps.deliveries.models import Delivery
from apps.orders.serializers import OrderSerializer


class CourierDeliverySerializer(serializers.ModelSerializer):
    """Delivery serializer for courier."""
    order = OrderSerializer(read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    agent_name = serializers.CharField(source='agent.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Delivery
        fields = (
            'id', 'delivery_number', 'order', 'zone', 'zone_name',
            'fee', 'status', 'status_display', 'agent', 'agent_name',
            'delivery_address_line1', 'delivery_address_line2',
            'delivery_city', 'delivery_region', 'delivery_postal_code', 'delivery_phone',
            'delivery_notes', 'failure_reason',
            'estimated_delivery_date', 'actual_delivery_date',
            'created_at', 'updated_at', 'assigned_at', 'completed_at'
        )
        read_only_fields = (
            'id', 'delivery_number', 'order', 'zone', 'fee',
            'created_at', 'updated_at', 'assigned_at', 'completed_at', 'actual_delivery_date'
        )


class DeliveryStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating delivery status."""
    status = serializers.ChoiceField(
        choices=['IN_TRANSIT', 'DELIVERED', 'FAILED'],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    failure_reason = serializers.CharField(required=False, allow_blank=True)
