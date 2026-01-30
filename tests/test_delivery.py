"""
Tests for delivery app.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.delivery.models import DeliveryZone, DeliverySlot, DeliveryFeeRule
from apps.delivery.services import calculate_delivery_fee
from decimal import Decimal


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def zone():
    """Create a test delivery zone."""
    return DeliveryZone.objects.create(
        name='N\'Djamena Central',
        code='NDJ-CENTRAL',
        description='Central N\'Djamena area'
    )


@pytest.fixture
def zone2():
    """Create another test delivery zone."""
    return DeliveryZone.objects.create(
        name='N\'Djamena North',
        code='NDJ-NORTH',
        description='North N\'Djamena area'
    )


@pytest.fixture
def slot(zone):
    """Create a test delivery slot."""
    return DeliverySlot.objects.create(
        zone=zone,
        day_of_week=DeliverySlot.DayOfWeek.MONDAY,
        start_time='09:00',
        end_time='12:00',
        max_orders=50
    )


@pytest.mark.django_db
class TestDeliveryZoneEndpoints:
    """Test delivery zone endpoints."""
    
    def test_list_zones(self, api_client, zone, zone2):
        """Test listing delivery zones."""
        url = '/api/v1/delivery/zones/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        zone_names = [z['name'] for z in response.data]
        assert zone.name in zone_names
        assert zone2.name in zone_names
    
    def test_list_zones_only_active(self, api_client, zone):
        """Test that only active zones are returned."""
        inactive_zone = DeliveryZone.objects.create(
            name='Inactive Zone',
            code='INACTIVE',
            is_active=False
        )
        
        url = '/api/v1/delivery/zones/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        zone_names = [z['name'] for z in response.data]
        assert zone.name in zone_names
        assert inactive_zone.name not in zone_names
    
    def test_retrieve_zone(self, api_client, zone):
        """Test retrieving a single zone."""
        url = f'/api/v1/delivery/zones/{zone.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == zone.name
        assert response.data['code'] == zone.code


@pytest.mark.django_db
class TestDeliverySlotEndpoints:
    """Test delivery slot endpoints."""
    
    def test_list_slots(self, api_client, zone, slot):
        """Test listing delivery slots."""
        url = '/api/v1/delivery/slots/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['zone'] == zone.id
    
    def test_list_slots_filter_by_zone(self, api_client, zone, zone2):
        """Test filtering slots by zone_id."""
        # Create slots for both zones
        slot1 = DeliverySlot.objects.create(
            zone=zone,
            day_of_week=DeliverySlot.DayOfWeek.MONDAY,
            start_time='09:00',
            end_time='12:00'
        )
        slot2 = DeliverySlot.objects.create(
            zone=zone2,
            day_of_week=DeliverySlot.DayOfWeek.MONDAY,
            start_time='14:00',
            end_time='17:00'
        )
        
        # List all slots
        url = '/api/v1/delivery/slots/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        
        # Filter by zone_id
        url_filtered = f'/api/v1/delivery/slots/?zone_id={zone.id}'
        response_filtered = api_client.get(url_filtered)
        
        assert response_filtered.status_code == status.HTTP_200_OK
        assert len(response_filtered.data) == 1
        assert response_filtered.data[0]['zone'] == zone.id
        assert response_filtered.data[0]['id'] == slot1.id
    
    def test_list_slots_only_active(self, api_client, zone):
        """Test that only active slots are returned."""
        active_slot = DeliverySlot.objects.create(
            zone=zone,
            day_of_week=DeliverySlot.DayOfWeek.MONDAY,
            start_time='09:00',
            end_time='12:00',
            is_active=True
        )
        inactive_slot = DeliverySlot.objects.create(
            zone=zone,
            day_of_week=DeliverySlot.DayOfWeek.TUESDAY,
            start_time='09:00',
            end_time='12:00',
            is_active=False
        )
        
        url = '/api/v1/delivery/slots/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        slot_ids = [s['id'] for s in response.data]
        assert active_slot.id in slot_ids
        assert inactive_slot.id not in slot_ids
    
    def test_available_slots_endpoint(self, api_client, zone):
        """Test available slots endpoint."""
        # Create slots for different days
        monday_slot = DeliverySlot.objects.create(
            zone=zone,
            day_of_week=DeliverySlot.DayOfWeek.MONDAY,
            start_time='09:00',
            end_time='12:00'
        )
        tuesday_slot = DeliverySlot.objects.create(
            zone=zone,
            day_of_week=DeliverySlot.DayOfWeek.TUESDAY,
            start_time='09:00',
            end_time='12:00'
        )
        
        url = f'/api/v1/delivery/slots/available/?zone_id={zone.id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Should return slots for current day only
        assert isinstance(response.data, list)
    
    def test_available_slots_missing_zone_id(self, api_client):
        """Test available slots endpoint without zone_id."""
        url = '/api/v1/delivery/slots/available/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data


@pytest.mark.django_db
class TestDeliveryFeeCalculation:
    """Test delivery fee calculation."""
    
    def test_fixed_fee_rule(self, zone):
        """Test fixed fee calculation."""
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000,
            priority=0
        )
        
        fee = calculate_delivery_fee(zone.id, 10000)
        assert fee == 2000
        
        fee = calculate_delivery_fee(zone.id, 50000)
        assert fee == 2000
    
    def test_percentage_fee_rule(self, zone):
        """Test percentage fee calculation."""
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.PERCENTAGE,
            percentage=Decimal('5.00'),  # 5%
            min_fee=1000,
            max_fee=5000,
            priority=0
        )
        
        # 5% of 10000 = 500, but min is 1000
        fee = calculate_delivery_fee(zone.id, 10000)
        assert fee == 1000
        
        # 5% of 50000 = 2500
        fee = calculate_delivery_fee(zone.id, 50000)
        assert fee == 2500
        
        # 5% of 200000 = 10000, but max is 5000
        fee = calculate_delivery_fee(zone.id, 200000)
        assert fee == 5000
    
    def test_tiered_fee_rule(self, zone):
        """Test tiered fee calculation."""
        tier_rules = [
            {'min': 0, 'max': 10000, 'fee': 2000},
            {'min': 10000, 'max': 50000, 'fee': 1500},
            {'min': 50000, 'max': 100000, 'fee': 1000},
            {'min': 100000, 'max': float('inf'), 'fee': 500},
        ]
        
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.TIERED,
            tier_rules=tier_rules,
            priority=0
        )
        
        # Test tier 1: 0-10000
        fee = calculate_delivery_fee(zone.id, 5000)
        assert fee == 2000
        
        # Test tier 2: 10000-50000
        fee = calculate_delivery_fee(zone.id, 25000)
        assert fee == 1500
        
        # Test tier 3: 50000-100000
        fee = calculate_delivery_fee(zone.id, 75000)
        assert fee == 1000
        
        # Test tier 4: 100000+
        fee = calculate_delivery_fee(zone.id, 150000)
        assert fee == 500
    
    def test_rule_priority(self, zone):
        """Test that higher priority rules are used first."""
        # Lower priority number = higher priority
        rule1 = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000,
            priority=1  # Lower priority
        )
        
        rule2 = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=3000,
            priority=0  # Higher priority
        )
        
        # Should use rule2 (priority 0)
        fee = calculate_delivery_fee(zone.id, 10000)
        assert fee == 3000
    
    def test_inactive_rule_not_used(self, zone):
        """Test that inactive rules are not used."""
        active_rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000,
            is_active=True,
            priority=0
        )
        
        inactive_rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=5000,
            is_active=False,
            priority=0
        )
        
        fee = calculate_delivery_fee(zone.id, 10000)
        assert fee == 2000  # Should use active rule
    
    def test_no_rules_returns_zero(self, zone):
        """Test that no rules returns zero fee."""
        fee = calculate_delivery_fee(zone.id, 10000)
        assert fee == 0
    
    def test_invalid_zone_returns_zero(self):
        """Test that invalid zone returns zero fee."""
        fee = calculate_delivery_fee(99999, 10000)
        assert fee == 0
    
    def test_calculate_fee_endpoint(self, api_client, zone):
        """Test calculate fee endpoint."""
        DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000,
            priority=0
        )
        
        url = '/api/v1/delivery/slots/calculate_fee/'
        response = api_client.post(url, {
            'zone_id': zone.id,
            'cart_total_xaf': 10000
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['zone_id'] == zone.id
        assert response.data['cart_total_xaf'] == 10000
        assert response.data['delivery_fee_xaf'] == 2000
    
    def test_calculate_fee_endpoint_missing_params(self, api_client):
        """Test calculate fee endpoint with missing parameters."""
        url = '/api/v1/delivery/slots/calculate_fee/'
        
        # Missing zone_id
        response = api_client.post(url, {'cart_total_xaf': 10000})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing cart_total_xaf
        response = api_client.post(url, {'zone_id': 1})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_calculate_fee_endpoint_invalid_cart_total(self, api_client, zone):
        """Test calculate fee endpoint with invalid cart total."""
        url = '/api/v1/delivery/slots/calculate_fee/'
        
        # Negative cart total
        response = api_client.post(url, {
            'zone_id': zone.id,
            'cart_total_xaf': -1000
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Non-integer cart total
        response = api_client.post(url, {
            'zone_id': zone.id,
            'cart_total_xaf': 'invalid'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDeliveryFeeRuleModel:
    """Test DeliveryFeeRule model methods."""
    
    def test_fixed_fee_calculation(self, zone):
        """Test fixed fee calculation in model."""
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000
        )
        
        assert rule.calculate_fee(10000) == 2000
        assert rule.calculate_fee(50000) == 2000
    
    def test_percentage_fee_calculation(self, zone):
        """Test percentage fee calculation in model."""
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.PERCENTAGE,
            percentage=Decimal('10.00'),
            min_fee=500,
            max_fee=3000
        )
        
        # 10% of 2000 = 200, but min is 500
        assert rule.calculate_fee(2000) == 500
        
        # 10% of 20000 = 2000
        assert rule.calculate_fee(20000) == 2000
        
        # 10% of 50000 = 5000, but max is 3000
        assert rule.calculate_fee(50000) == 3000
    
    def test_tiered_fee_calculation(self, zone):
        """Test tiered fee calculation in model."""
        tier_rules = [
            {'min': 0, 'max': 10000, 'fee': 2000},
            {'min': 10000, 'max': 50000, 'fee': 1500},
        ]
        
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.TIERED,
            tier_rules=tier_rules
        )
        
        assert rule.calculate_fee(5000) == 2000
        assert rule.calculate_fee(25000) == 1500
    
    def test_inactive_rule_returns_zero(self, zone):
        """Test that inactive rule returns zero."""
        rule = DeliveryFeeRule.objects.create(
            zone=zone,
            rule_type=DeliveryFeeRule.RuleType.FIXED,
            fixed_fee=2000,
            is_active=False
        )
        
        assert rule.calculate_fee(10000) == 0

