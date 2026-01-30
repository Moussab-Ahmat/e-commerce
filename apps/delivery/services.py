"""
Services for delivery app.
"""
from .models import DeliveryZone, DeliveryFeeRule


def calculate_delivery_fee(zone_id, cart_total_xaf):
    """
    Calculate delivery fee for a zone and cart total.
    
    Args:
        zone_id: Delivery zone ID
        cart_total_xaf: Cart total in XAF (integer)
    
    Returns:
        Delivery fee in XAF (integer)
    """
    try:
        zone = DeliveryZone.objects.get(pk=zone_id, is_active=True)
    except DeliveryZone.DoesNotExist:
        return 0
    
    # Get active fee rules for this zone, ordered by priority
    rules = DeliveryFeeRule.objects.filter(
        zone=zone,
        is_active=True
    ).order_by('priority', '-created_at')
    
    if not rules.exists():
        return 0
    
    # Use the first rule (highest priority)
    rule = rules.first()
    return rule.calculate_fee(cart_total_xaf)

