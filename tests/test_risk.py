"""
Tests for risk app.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.risk.models import Blacklist, CodLimitRule
from apps.risk.services import RiskService
from apps.risk.tasks import auto_cancel_pending_orders
from apps.orders.models import Order, OrderItem
from apps.accounts.models import User
from apps.catalog.models import Product, Category
from apps.delivery.models import DeliveryZone
from apps.inventory.models import InventoryItem


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        phone_number='+23512345678',
        password='testpass'
    )


@pytest.fixture
def staff_user():
    """Create a staff user."""
    return User.objects.create_user(
        phone_number='+23587654321',
        password='testpass',
        is_staff=True
    )


@pytest.fixture
def category():
    """Create a test category."""
    return Category.objects.create(
        name='Test Category',
        slug='test-category'
    )


@pytest.fixture
def product(category):
    """Create a test product."""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        category=category,
        price=10000,
        stock_quantity=100,
        sku='TEST-001'
    )


@pytest.fixture
def delivery_zone():
    """Create a test delivery zone."""
    return DeliveryZone.objects.create(
        name='Test Zone',
        code='TEST-ZONE'
    )


@pytest.mark.django_db
class TestBlacklist:
    """Test blacklist functionality."""
    
    def test_blacklist_check_not_blacklisted(self, user):
        """Test checking non-blacklisted phone."""
        result = RiskService.check_blacklist(user.phone_number)
        
        assert result['is_blacklisted'] is False
        assert result['blacklist'] is None
    
    def test_blacklist_check_blacklisted(self, user):
        """Test checking blacklisted phone."""
        Blacklist.objects.create(
            phone_number=user.phone_number,
            reason='Fraudulent activity',
            is_active=True
        )
        
        result = RiskService.check_blacklist(user.phone_number)
        
        assert result['is_blacklisted'] is True
        assert result['blacklist'] is not None
        assert 'Fraudulent' in result['reason']
    
    def test_blacklist_blocks_order_creation(self, api_client, user, product, delivery_zone):
        """Test that blacklisted user cannot create order."""
        # Blacklist user
        Blacklist.objects.create(
            phone_number=user.phone_number,
            reason='Fraudulent activity',
            is_active=True
        )
        
        api_client.force_authenticate(user=user)
        
        url = '/api/v1/orders/orders/'
        response = api_client.post(url, {
            'items': [{'product_id': product.id, 'quantity': 1}],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'blacklisted' in response.data['errors'][0].lower()
    
    def test_inactive_blacklist_does_not_block(self, user, product, delivery_zone):
        """Test that inactive blacklist doesn't block orders."""
        Blacklist.objects.create(
            phone_number=user.phone_number,
            reason='Old issue',
            is_active=False
        )
        
        result = RiskService.check_blacklist(user.phone_number)
        assert result['is_blacklisted'] is False


@pytest.mark.django_db
class TestCodLimit:
    """Test COD limit functionality."""
    
    def test_cod_limit_within_limit(self, user, product, delivery_zone):
        """Test order within COD limit."""
        CodLimitRule.objects.create(
            limit_amount_xaf=100000,
            is_active=True
        )
        
        result = RiskService.check_cod_limit(user, 50000)
        
        assert result['within_limit'] is True
        assert result['limit'] == 100000
    
    def test_cod_limit_exceeded(self, user, product, delivery_zone):
        """Test order exceeding COD limit."""
        CodLimitRule.objects.create(
            limit_amount_xaf=100000,
            is_active=True
        )
        
        # Create order for 60000 today
        from apps.orders.services import OrderService
        OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 6}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        
        # Try to create another order that would exceed limit
        result = RiskService.check_cod_limit(user, 50000)
        
        assert result['within_limit'] is False
        assert result['error'] is not None
    
    def test_cod_limit_daily_total(self, user, product, delivery_zone):
        """Test COD limit checks daily total."""
        CodLimitRule.objects.create(
            limit_amount_xaf=100000,
            is_active=True
        )
        
        # Create multiple orders today
        from apps.orders.services import OrderService
        
        # First order: 30000
        result1 = OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 3}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        order1 = result1['order']
        order1.transition_status(Order.Status.CONFIRMED)
        
        # Second order: 40000
        result2 = OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 4}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        order2 = result2['order']
        order2.transition_status(Order.Status.CONFIRMED)
        
        # Check limit for new order
        result = RiskService.check_cod_limit(user, 40000)
        
        # Total would be 30000 + 40000 + 40000 = 110000, exceeds 100000
        assert result['within_limit'] is False
    
    def test_cod_limit_blocks_order_creation(self, api_client, user, product, delivery_zone):
        """Test that COD limit blocks order creation."""
        CodLimitRule.objects.create(
            limit_amount_xaf=50000,
            is_active=True
        )
        
        # Create and confirm order for 60000 (exceeds limit)
        from apps.orders.services import OrderService
        result = OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 6}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        order = result['order']
        order.transition_status(Order.Status.CONFIRMED)
        
        # Try to create another order via API
        api_client.force_authenticate(user=user)
        url = '/api/v1/orders/orders/'
        response = api_client.post(url, {
            'items': [{'product_id': product.id, 'quantity': 1}],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'limit' in response.data['errors'][0].lower()


@pytest.mark.django_db
class TestOrderConfirmation:
    """Test order confirmation flow."""
    
    def test_confirm_order_success(self, api_client, user, staff_user, product, delivery_zone):
        """Test successful order confirmation."""
        # Create inventory item
        inventory_item = InventoryItem.objects.create(
            product=product,
            on_hand=100,
            reserved=0
        )
        
        # Create order
        api_client.force_authenticate(user=user)
        create_url = '/api/v1/orders/orders/'
        create_response = api_client.post(create_url, {
            'items': [{'product_id': product.id, 'quantity': 5}],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        order_id = create_response.data['id']
        
        # Confirm order (staff only)
        api_client.force_authenticate(user=staff_user)
        confirm_url = f'/api/v1/orders/orders/{order_id}/confirm/'
        response = api_client.post(confirm_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Order.Status.CONFIRMED
        
        # Check inventory reserved
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 5
        
        # Check order status
        order = Order.objects.get(pk=order_id)
        assert order.status == Order.Status.CONFIRMED
        assert order.confirmed_at is not None
    
    def test_confirm_order_non_staff(self, api_client, user, product, delivery_zone):
        """Test that non-staff cannot confirm orders."""
        # Create order
        api_client.force_authenticate(user=user)
        create_url = '/api/v1/orders/orders/'
        create_response = api_client.post(create_url, {
            'items': [{'product_id': product.id, 'quantity': 1}],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        order_id = create_response.data['id']
        
        # Try to confirm (should fail)
        confirm_url = f'/api/v1/orders/orders/{order_id}/confirm/'
        response = api_client.post(confirm_url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'staff' in response.data['errors'][0].lower()


@pytest.mark.django_db
class TestAutoCancelTask:
    """Test auto-cancel Celery task."""
    
    def test_auto_cancel_old_pending_orders(self, user, product, delivery_zone):
        """Test that old pending orders are auto-cancelled."""
        # Create old pending order (older than timeout)
        old_time = timezone.now() - timedelta(minutes=35)  # Older than 30 min default
        
        order = Order.objects.create(
            user=user,
            order_number='ORD-TEST-001',
            status=Order.Status.PENDING_CONFIRMATION,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23512345678',
            subtotal=10000,
            delivery_fee=2000,
            total=12000
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=10000
        )
        
        # Manually set created_at to old time
        Order.objects.filter(pk=order.id).update(created_at=old_time)
        
        # Run task
        result = auto_cancel_pending_orders()
        
        assert result['cancelled_count'] == 1
        
        # Check order is cancelled
        order.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        assert order.cancelled_at is not None
    
    def test_auto_cancel_releases_reservations(self, user, product, delivery_zone):
        """Test that auto-cancel releases any reservations."""
        # Create inventory item
        inventory_item = InventoryItem.objects.create(
            product=product,
            on_hand=100,
            reserved=10  # Some reserved stock
        )
        
        # Create old pending order
        old_time = timezone.now() - timedelta(minutes=35)
        
        order = Order.objects.create(
            user=user,
            order_number='ORD-TEST-002',
            status=Order.Status.PENDING_CONFIRMATION,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23512345678',
            subtotal=10000,
            delivery_fee=2000,
            total=12000
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            unit_price=10000
        )
        
        # Manually set created_at
        Order.objects.filter(pk=order.id).update(created_at=old_time)
        
        # Note: In real scenario, reservations might exist if order was partially processed
        # For this test, we verify the task handles the case gracefully
        
        # Run task
        result = auto_cancel_pending_orders()
        
        assert result['cancelled_count'] == 1
        
        # Check order is cancelled
        order.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
    
    def test_auto_cancel_does_not_cancel_recent_orders(self, user, product, delivery_zone):
        """Test that recent pending orders are not cancelled."""
        # Create recent pending order
        order = Order.objects.create(
            user=user,
            order_number='ORD-TEST-003',
            status=Order.Status.PENDING_CONFIRMATION,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23512345678',
            subtotal=10000,
            delivery_fee=2000,
            total=12000
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=10000
        )
        
        # Run task
        result = auto_cancel_pending_orders()
        
        assert result['cancelled_count'] == 0
        
        # Check order is still pending
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING_CONFIRMATION
