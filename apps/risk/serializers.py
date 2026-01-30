"""
Serializers for risk app.
"""
from rest_framework import serializers
from .models import Blacklist, CodLimitRule


class BlacklistSerializer(serializers.ModelSerializer):
    """Blacklist serializer."""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Blacklist
        fields = (
            'id', 'phone_number', 'reason', 'is_active',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CodLimitRuleSerializer(serializers.ModelSerializer):
    """COD limit rule serializer."""
    
    class Meta:
        model = CodLimitRule
        fields = (
            'id', 'limit_amount_xaf', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
