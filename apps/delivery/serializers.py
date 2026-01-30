"""
Serializers for delivery app.
"""
from rest_framework import serializers
from .models import DeliveryZone, DeliveryFeeRule


class DeliveryZoneSerializer(serializers.ModelSerializer):
    """Delivery zone serializer."""
    
    class Meta:
        model = DeliveryZone
        fields = ('id', 'name', 'code', 'description', 'is_active')
        read_only_fields = ('id',)


class DeliveryFeeRuleSerializer(serializers.ModelSerializer):
    """Delivery fee rule serializer."""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    
    class Meta:
        model = DeliveryFeeRule
        fields = (
            'id', 'zone', 'zone_name',
            'rule_type', 'rule_type_display',
            'fixed_fee', 'percentage', 'min_fee', 'max_fee',
            'tier_rules', 'priority', 'is_active'
        )
        read_only_fields = ('id',)

