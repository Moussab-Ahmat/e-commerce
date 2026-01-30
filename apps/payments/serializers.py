"""
Serializers for payments app.
"""
from rest_framework import serializers
from .models import Payment, PaymentHistory
from apps.orders.serializers import OrderSerializer


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Payment history serializer."""
    
    class Meta:
        model = PaymentHistory
        fields = ('id', 'old_status', 'new_status', 'changed_by', 'notes', 'created_at')
        read_only_fields = ('id', 'old_status', 'new_status', 'changed_by', 'created_at')


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer."""
    order = OrderSerializer(read_only=True)
    collected_by_name = serializers.CharField(source='collected_by.user.get_full_name', read_only=True)
    history = PaymentHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Payment
        fields = (
            'id', 'payment_number', 'order', 'amount', 'payment_method',
            'status', 'collected_by', 'collected_by_name', 'collected_at',
            'notes', 'history', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'payment_number', 'created_at', 'updated_at', 'collected_at')

