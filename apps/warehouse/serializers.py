"""
Serializers for warehouse app.
"""
from rest_framework import serializers
from apps.orders.serializers import OrderSerializer


class PickingQueueOrderSerializer(OrderSerializer):
    """Lightweight serializer for picking queue."""
    
    class Meta(OrderSerializer.Meta):
        fields = (
            'id', 'order_number', 'user_phone', 'status',
            'total', 'items',
            'created_at', 'confirmed_at'
        )
