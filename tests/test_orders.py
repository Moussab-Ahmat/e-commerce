"""
Tests for orders app.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderService
from apps.catalog.models import Product, Category
from apps.delivery.models import DeliveryZone
from apps.accounts.models import User


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
class TestOrderCreation:
    """Test order creation."""
    
    def test_create_order_success(self, api_client, user, product, delivery_zone):
        """Test successful order creation."""
        api_client.force_authenticate(user=user)
        
        url = '/api/v1/orders/orders/'
        response = api_client.post(url, {
            'items': [
                {'product_id': product.id, 'quantity': 2}
            ],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == Order.Status.PENDING_CONFIRMATION
        assert response.data['subtotal'] == 20000  # 2 * 10000
        assert 'delivery_fee' in response.data
        assert 'total' in response.data
        assert len(response.data['items']) == 1
    
    def test_create_order_calculates_totals(self, api_client, user, product, delivery_zone):
        """Test that order totals are calculated correctly."""
        api_client.force_authenticate(user=user)
        
        url = '/api/v1/orders/orders/'
        response = api_client.post(url, {
            'items': [
                {'product_id': product.id, 'quantity': 3}
            ],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        order_data = response.data
        
        # Check subtotal
        assert order_data['subtotal'] == 30000  # 3 * 10000
        
        # Check delivery fee is included
        assert order_data['delivery_fee'] >= 0
        
        # Check total
        assert order_data['total'] == order_data['subtotal'] + order_data['delivery_fee']
    
    def test_create_order_idempotency(self, api_client, user, product, delivery_zone):
        """Test order creation with idempotency key."""
        api_client.force_authenticate(user=user)
        
        idempotency_key = 'test-idempotency-key-123'
        url = '/api/v1/orders/orders/'
        
        data = {
            'items': [
                {'product_id': product.id, 'quantity': 2}
            ],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }
        
        # First request
        response1 = api_client.post(
            url,
            data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        
        assert response1.status_code == status.HTTP_201_CREATED
        order_id_1 = response1.data['id']
        order_number_1 = response1.data['order_number']
        
        # Second request with same idempotency key
        response2 = api_client.post(
            url,
            data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key
        )
        
        # Should return same order (200 OK, not 201)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['id'] == order_id_1
        assert response2.data['order_number'] == order_number_1
        
        # Verify only one order was created
        orders_count = Order.objects.filter(idempotency_key=idempotency_key).count()
        assert orders_count == 1
    
    def test_create_order_multiple_items(self, api_client, user, category, delivery_zone):
        """Test order creation with multiple items."""
        product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=category,
            price=10000,
            sku='PROD-1'
        )
        product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=category,
            price=20000,
            sku='PROD-2'
        )
        
        api_client.force_authenticate(user=user)
        
        url = '/api/v1/orders/orders/'
        response = api_client.post(url, {
            'items': [
                {'product_id': product1.id, 'quantity': 2},
                {'product_id': product2.id, 'quantity': 1}
            ],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['subtotal'] == 40000  # (2 * 10000) + (1 * 20000)
        assert len(response.data['items']) == 2


@pytest.mark.django_db
class TestOrderEndpoints:
    """Test order endpoints."""
    
    def test_list_orders_customer(self, api_client, user, product, delivery_zone):
        """Test listing orders for customer."""
        # Create order
        api_client.force_authenticate(user=user)
        url = '/api/v1/orders/orders/'
        api_client.post(url, {
            'items': [{'product_id': product.id, 'quantity': 1}],
            'delivery_zone_id': delivery_zone.id,
            'delivery_address_line1': '123 Main St',
            'delivery_city': 'N\'Djamena',
            'delivery_region': 'Chari-Baguirmi',
            'delivery_phone': '+23512345678'
        }, format='json')
        
        # List orders
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
    
    def test_retrieve_order(self, api_client, user, product, delivery_zone):
        """Test retrieving a single order."""
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
        
        # Retrieve order
        retrieve_url = f'/api/v1/orders/orders/{order_id}/'
        response = api_client.get(retrieve_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == order_id
        assert 'items' in response.data
        assert 'subtotal' in response.data
        assert 'total' in response.data


@pytest.mark.django_db
class TestOrderCancellation:
    """Test order cancellation."""
    
    def test_cancel_order_pending_confirmation(self, api_client, user, product, delivery_zone):
        """Test cancelling order in PENDING_CONFIRMATION status."""
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
        
        # Cancel order
        cancel_url = f'/api/v1/orders/orders/{order_id}/cancel/'
        response = api_client.post(cancel_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Order.Status.CANCELLED
        
        # Verify order is cancelled
        order = Order.objects.get(pk=order_id)
        assert order.status == Order.Status.CANCELLED
        assert order.cancelled_at is not None
    
    def test_cancel_order_after_confirmed(self, api_client, user, product, delivery_zone):
        """Test that order cannot be cancelled after CONFIRMED."""
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
        order = Order.objects.get(pk=order_id)
        
        # Confirm order
        order.transition_status(Order.Status.CONFIRMED)
        
        # Try to cancel
        cancel_url = f'/api/v1/orders/orders/{order_id}/cancel/'
        response = api_client.post(cancel_url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot cancel' in response.data['errors'][0].lower()
        
        # Verify order is still CONFIRMED
        order.refresh_from_db()
        assert order.status == Order.Status.CONFIRMED


@pytest.mark.django_db
class TestOrderStatusTransitions:
    """Test order status transitions."""
    
    def test_status_transitions(self, user, product, delivery_zone):
        """Test valid status transitions."""
        # Create order
        result = OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 1}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        
        order = result['order']
        
        # PENDING_CONFIRMATION -> CONFIRMED
        assert order.can_transition_to(Order.Status.CONFIRMED)
        order.transition_status(Order.Status.CONFIRMED)
        assert order.status == Order.Status.CONFIRMED
        
        # CONFIRMED -> PROCESSING
        assert order.can_transition_to(Order.Status.PROCESSING)
        order.transition_status(Order.Status.PROCESSING)
        assert order.status == Order.Status.PROCESSING
        
        # Cannot go back
        assert not order.can_transition_to(Order.Status.PENDING_CONFIRMATION)
    
    def test_invalid_status_transition(self, user, product, delivery_zone):
        """Test invalid status transition."""
        result = OrderService.create_order(
            user=user,
            items=[{'product_id': product.id, 'quantity': 1}],
            delivery_info={
                'zone_id': delivery_zone.id,
                'address_line1': '123 Main St',
                'city': 'N\'Djamena',
                'region': 'Chari-Baguirmi',
                'phone': '+23512345678'
            }
        )
        
        order = result['order']
        
        # Cannot skip from PENDING_CONFIRMATION to PROCESSING
        assert not order.can_transition_to(Order.Status.PROCESSING)
        
        with pytest.raises(Exception):  # InvalidOrderStatusError
            order.transition_status(Order.Status.PROCESSING)
