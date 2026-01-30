"""
Serializers for deliveries app.
"""
from rest_framework import serializers
from .models import DeliveryAgent, Delivery, DeliveryStatusHistory
from apps.orders.serializers import OrderSerializer


class DeliveryAgentSerializer(serializers.ModelSerializer):
    """Delivery agent serializer."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryAgent
        fields = (
            'id', 'agent_id', 'user', 'user_name', 'vehicle_type',
            'vehicle_number', 'phone_number', 'is_active',
            'current_latitude', 'current_longitude'
        )


class DeliveryStatusHistorySerializer(serializers.ModelSerializer):
    """Delivery status history serializer."""
    
    class Meta:
        model = DeliveryStatusHistory
        fields = ('id', 'old_status', 'new_status', 'changed_by', 'notes', 'created_at')
        read_only_fields = ('id', 'old_status', 'new_status', 'changed_by', 'created_at')


class DeliverySerializer(serializers.ModelSerializer):
    """Delivery serializer."""
    order = OrderSerializer(read_only=True)
    agent = DeliveryAgentSerializer(read_only=True)
    agent_id = serializers.IntegerField(write_only=True, required=False)
    status_history = DeliveryStatusHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Delivery
        fields = (
            'id', 'delivery_number', 'order', 'status', 'agent', 'agent_id',
            'estimated_delivery_date', 'actual_delivery_date',
            'delivery_address_line1', 'delivery_address_line2',
            'delivery_city', 'delivery_region', 'delivery_postal_code', 'delivery_phone',
            'delivery_notes', 'failure_reason',
            'status_history',
            'created_at', 'updated_at', 'assigned_at', 'completed_at'
        )
        read_only_fields = (
            'id', 'delivery_number', 'created_at', 'updated_at',
            'assigned_at', 'completed_at', 'actual_delivery_date'
        )

