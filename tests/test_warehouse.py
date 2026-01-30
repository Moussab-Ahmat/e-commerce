"""
Tests for warehouse app.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
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
def warehouse_user():
    """Create a warehouse user."""
    return User.objects.create_user(
        phone_number='+23511111111',
        password='testpass',
        role=User.Role.WAREHOUSE
    )


@pytest.fixture
def customer_user():
    """Create a customer user."""
    return User.objects.create_user(
        phone_number='+23522222222',
        password='testpass',
        role=User.Role.CUSTOMER
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


@pytest.fixture
def confirmed_order(customer_user, product, delivery_zone):
    """Create a confirmed order."""
    order = Order.objects.create(
        user=customer_user,
        order_number='ORD-TEST-001',
        status=Order.Status.CONFIRMED,
        delivery_zone=delivery_zone,
        delivery_address_line1='123 Main St',
        delivery_city='N\'Djamena',
        delivery_region='Chari-Baguirmi',
        delivery_phone='+23522222222',
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
    return order


@pytest.mark.django_db
class TestPickingQueue:
    """Test picking queue endpoint."""
    
    def test_picking_queue_warehouse_user(self, api_client, warehouse_user, confirmed_order):
        """Test picking queue accessible by warehouse user."""
        api_client.force_authenticate(user=warehouse_user)
        
        url = '/api/v1/warehouse/orders/picking_queue/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['order_number'] == confirmed_order.order_number
        assert response.data[0]['status'] == Order.Status.CONFIRMED
    
    def test_picking_queue_only_confirmed_orders(self, api_client, warehouse_user, customer_user, product, delivery_zone):
        """Test picking queue only shows CONFIRMED orders."""
        # Create orders with different statuses
        confirmed_order = Order.objects.create(
            user=customer_user,
            order_number='ORD-CONF-001',
            status=Order.Status.CONFIRMED,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        picking_order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PICK-001',
            status=Order.Status.PICKING,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        packed_order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PACK-001',
            status=Order.Status.PACKED,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        api_client.force_authenticate(user=warehouse_user)
        
        url = '/api/v1/warehouse/orders/picking_queue/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        order_numbers = [o['order_number'] for o in response.data]
        assert confirmed_order.order_number in order_numbers
        assert picking_order.order_number not in order_numbers
        assert packed_order.order_number not in order_numbers
    
    def test_picking_queue_non_warehouse_user(self, api_client, customer_user):
        """Test picking queue not accessible by non-warehouse user."""
        api_client.force_authenticate(user=customer_user)
        
        url = '/api/v1/warehouse/orders/picking_queue/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestStartPicking:
    """Test start picking endpoint."""
    
    def test_start_picking_success(self, api_client, warehouse_user, confirmed_order):
        """Test successful start picking."""
        api_client.force_authenticate(user=warehouse_user)
        
        url = f'/api/v1/warehouse/orders/{confirmed_order.id}/start_picking/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Order.Status.PICKING
        
        # Verify order status
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == Order.Status.PICKING
    
    def test_start_picking_invalid_status(self, api_client, warehouse_user, customer_user, product, delivery_zone):
        """Test start picking with invalid status."""
        # Create order in PICKING status
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PICK-001',
            status=Order.Status.PICKING,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        api_client.force_authenticate(user=warehouse_user)
        
        url = f'/api/v1/warehouse/orders/{order.id}/start_picking/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot start picking' in response.data['error'].lower()
    
    def test_start_picking_non_warehouse_user(self, api_client, customer_user, confirmed_order):
        """Test start picking not accessible by non-warehouse user."""
        api_client.force_authenticate(user=customer_user)
        
        url = f'/api/v1/warehouse/orders/{confirmed_order.id}/start_picking/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_start_picking_transition_enforced(self, api_client, warehouse_user, confirmed_order):
        """Test that status transition is enforced."""
        api_client.force_authenticate(user=warehouse_user)
        
        # Transition to PICKING
        url = f'/api/v1/warehouse/orders/{confirmed_order.id}/start_picking/'
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Try to start picking again (should fail)
        response = api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPacked:
    """Test packed endpoint."""
    
    def test_packed_success(self, api_client, warehouse_user, customer_user, product, delivery_zone):
        """Test successful packed transition."""
        # Create order in PICKING status
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PICK-001',
            status=Order.Status.PICKING,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        api_client.force_authenticate(user=warehouse_user)
        
        url = f'/api/v1/warehouse/orders/{order.id}/packed/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Order.Status.PACKED
        
        # Verify order status
        order.refresh_from_db()
        assert order.status == Order.Status.PACKED
    
    def test_packed_invalid_status(self, api_client, warehouse_user, confirmed_order):
        """Test packed with invalid status (must be PICKING)."""
        api_client.force_authenticate(user=warehouse_user)
        
        url = f'/api/v1/warehouse/orders/{confirmed_order.id}/packed/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot mark as packed' in response.data['error'].lower()
    
    def test_packed_non_warehouse_user(self, api_client, customer_user, product, delivery_zone):
        """Test packed not accessible by non-warehouse user."""
        # Create order in PICKING status
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PICK-001',
            status=Order.Status.PICKING,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        api_client.force_authenticate(user=customer_user)
        
        url = f'/api/v1/warehouse/orders/{order.id}/packed/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_packed_transition_enforced(self, api_client, warehouse_user, customer_user, product, delivery_zone):
        """Test that status transition is enforced."""
        # Create order in PICKING status
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-PICK-001',
            status=Order.Status.PICKING,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23522222222',
            subtotal=10000,
            total=10000
        )
        
        api_client.force_authenticate(user=warehouse_user)
        
        # Transition to PACKED
        url = f'/api/v1/warehouse/orders/{order.id}/packed/'
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Try to mark as packed again (should fail)
        response = api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWarehouseWorkflow:
    """Test complete warehouse workflow."""
    
    def test_complete_warehouse_workflow(self, api_client, warehouse_user, confirmed_order):
        """Test complete workflow: CONFIRMED → PICKING → PACKED."""
        api_client.force_authenticate(user=warehouse_user)
        
        # Step 1: Get picking queue
        queue_url = '/api/v1/warehouse/orders/picking_queue/'
        queue_response = api_client.get(queue_url)
        assert queue_response.status_code == status.HTTP_200_OK
        assert len(queue_response.data) == 1
        
        # Step 2: Start picking
        start_picking_url = f'/api/v1/warehouse/orders/{confirmed_order.id}/start_picking/'
        picking_response = api_client.post(start_picking_url)
        assert picking_response.status_code == status.HTTP_200_OK
        assert picking_response.data['status'] == Order.Status.PICKING
        
        # Verify order no longer in picking queue
        queue_response = api_client.get(queue_url)
        assert len(queue_response.data) == 0
        
        # Step 3: Mark as packed
        packed_url = f'/api/v1/warehouse/orders/{confirmed_order.id}/packed/'
        packed_response = api_client.post(packed_url)
        assert packed_response.status_code == status.HTTP_200_OK
        assert packed_response.data['status'] == Order.Status.PACKED
        
        # Verify final status
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == Order.Status.PACKED
