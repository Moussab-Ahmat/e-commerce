"""
Tests for courier app.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.deliveries.models import Delivery, DeliveryAgent, DeliveryStatus
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
def courier_user():
    """Create a courier user."""
    return User.objects.create_user(
        phone_number='+23533333333',
        password='testpass',
        role=User.Role.COURIER
    )


@pytest.fixture
def delivery_agent(courier_user):
    """Create a delivery agent."""
    return DeliveryAgent.objects.create(
        user=courier_user,
        agent_id='COURIER-001',
        phone_number='+23533333333'
    )


@pytest.fixture
def customer_user():
    """Create a customer user."""
    return User.objects.create_user(
        phone_number='+23544444444',
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
def order_with_delivery(customer_user, product, delivery_zone):
    """Create an order with delivery."""
    order = Order.objects.create(
        user=customer_user,
        order_number='ORD-DELIVERY-001',
        status=Order.Status.PACKED,  # Packed and ready for delivery
        delivery_zone=delivery_zone,
        delivery_address_line1='123 Main St',
        delivery_city='N\'Djamena',
        delivery_region='Chari-Baguirmi',
        delivery_phone='+23544444444',
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
    
    # Create delivery
    delivery = Delivery.objects.create(
        order=order,
        delivery_number='DEL-001',
        zone=delivery_zone,
        fee=2000,
        status=DeliveryStatus.ASSIGNED,
        delivery_address_line1='123 Main St',
        delivery_city='N\'Djamena',
        delivery_region='Chari-Baguirmi',
        delivery_phone='+23544444444'
    )
    
    return order, delivery


@pytest.mark.django_db
class TestCourierDeliveries:
    """Test courier deliveries endpoint."""
    
    def test_list_deliveries_courier(self, api_client, courier_user, delivery_agent, order_with_delivery):
        """Test listing deliveries assigned to courier."""
        order, delivery = order_with_delivery
        delivery.agent = delivery_agent
        delivery.save()
        
        api_client.force_authenticate(user=courier_user)
        
        url = '/api/v1/courier/deliveries/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['delivery_number'] == delivery.delivery_number
    
    def test_list_deliveries_only_assigned(self, api_client, courier_user, delivery_agent, customer_user, product, delivery_zone):
        """Test that courier only sees assigned deliveries."""
        # Create order
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-001',
            status=Order.Status.PACKED,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444',
            subtotal=10000,
            total=10000
        )
        
        # Create assigned delivery
        assigned_delivery = Delivery.objects.create(
            order=order,
            delivery_number='DEL-ASSIGNED',
            zone=delivery_zone,
            fee=2000,
            status=DeliveryStatus.ASSIGNED,
            agent=delivery_agent,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444'
        )
        
        # Create unassigned delivery
        unassigned_delivery = Delivery.objects.create(
            order=order,
            delivery_number='DEL-UNASSIGNED',
            zone=delivery_zone,
            fee=2000,
            status=DeliveryStatus.PENDING,
            agent=None,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444'
        )
        
        api_client.force_authenticate(user=courier_user)
        
        url = '/api/v1/courier/deliveries/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        delivery_numbers = [d['delivery_number'] for d in response.data]
        assert assigned_delivery.delivery_number in delivery_numbers
        assert unassigned_delivery.delivery_number not in delivery_numbers
    
    def test_list_deliveries_non_courier(self, api_client, customer_user):
        """Test that non-courier cannot access."""
        api_client.force_authenticate(user=customer_user)
        
        url = '/api/v1/courier/deliveries/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDeliveryStatusUpdate:
    """Test delivery status update endpoint."""
    
    def test_update_status_in_transit(self, api_client, courier_user, delivery_agent, order_with_delivery):
        """Test updating status to IN_TRANSIT."""
        order, delivery = order_with_delivery
        delivery.agent = delivery_agent
        delivery.save()
        
        api_client.force_authenticate(user=courier_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'IN_TRANSIT',
            'notes': 'On the way'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == DeliveryStatus.IN_TRANSIT
        
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.IN_TRANSIT
    
    def test_update_status_delivered_atomic(self, api_client, courier_user, delivery_agent, order_with_delivery, product):
        """Test updating status to DELIVERED atomically updates order and inventory."""
        order, delivery = order_with_delivery
        delivery.agent = delivery_agent
        delivery.save()
        
        # Create inventory item with reserved stock
        inventory_item = InventoryItem.objects.create(
            product=product,
            on_hand=100,
            reserved=5  # Reserved for this order
        )
        
        api_client.force_authenticate(user=courier_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'DELIVERED',
            'notes': 'Delivered successfully'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == DeliveryStatus.DELIVERED
        
        # Check delivery status
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.actual_delivery_date is not None
        
        # Check order status
        order.refresh_from_db()
        assert order.status == Order.Status.DELIVERED
        assert order.delivered_at is not None
        
        # Check inventory committed (reserved and on_hand reduced)
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 0  # Reserved released
        assert inventory_item.on_hand == 95  # 100 - 5 = 95
    
    def test_update_status_failed(self, api_client, courier_user, delivery_agent, order_with_delivery):
        """Test updating status to FAILED."""
        order, delivery = order_with_delivery
        delivery.agent = delivery_agent
        delivery.status = DeliveryStatus.IN_TRANSIT
        delivery.save()
        
        api_client.force_authenticate(user=courier_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'FAILED',
            'failure_reason': 'Customer not available'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == DeliveryStatus.FAILED
        
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.FAILED
        assert 'not available' in delivery.failure_reason
    
    def test_update_status_invalid_transition(self, api_client, courier_user, delivery_agent, order_with_delivery):
        """Test invalid status transition."""
        order, delivery = order_with_delivery
        delivery.agent = delivery_agent
        delivery.status = DeliveryStatus.PENDING  # Cannot go directly to DELIVERED
        delivery.save()
        
        api_client.force_authenticate(user=courier_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'DELIVERED'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot transition' in response.data['errors'][0].lower()
    
    def test_update_status_not_assigned_to_courier(self, api_client, courier_user, customer_user, product, delivery_zone):
        """Test that courier cannot update delivery not assigned to them."""
        # Create another courier
        other_courier = User.objects.create_user(
            phone_number='+23555555555',
            password='testpass',
            role=User.Role.COURIER
        )
        other_agent = DeliveryAgent.objects.create(
            user=other_courier,
            agent_id='COURIER-002',
            phone_number='+23555555555'
        )
        
        # Create order
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-002',
            status=Order.Status.PACKED,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444',
            subtotal=10000,
            total=10000
        )
        
        # Create delivery assigned to other courier
        delivery = Delivery.objects.create(
            order=order,
            delivery_number='DEL-OTHER',
            zone=delivery_zone,
            fee=2000,
            status=DeliveryStatus.ASSIGNED,
            agent=other_agent,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444'
        )
        
        api_client.force_authenticate(user=courier_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'IN_TRANSIT'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not assigned to you' in response.data['errors'][0].lower()
    
    def test_update_status_non_courier(self, api_client, customer_user, order_with_delivery):
        """Test that non-courier cannot update status."""
        order, delivery = order_with_delivery
        
        api_client.force_authenticate(user=customer_user)
        
        url = f'/api/v1/courier/deliveries/{delivery.id}/status/'
        response = api_client.post(url, {
            'status': 'IN_TRANSIT'
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDeliveryAssign:
    """Test delivery assignment endpoint."""
    
    def test_assign_delivery_admin(self, api_client, customer_user, product, delivery_zone):
        """Test admin can assign delivery."""
        admin_user = User.objects.create_user(
            phone_number='+23599999999',
            password='testpass',
            role=User.Role.ADMIN,
            is_staff=True
        )
        
        courier_user = User.objects.create_user(
            phone_number='+23588888888',
            password='testpass',
            role=User.Role.COURIER
        )
        agent = DeliveryAgent.objects.create(
            user=courier_user,
            agent_id='COURIER-003',
            phone_number='+23588888888'
        )
        
        # Create order
        order = Order.objects.create(
            user=customer_user,
            order_number='ORD-003',
            status=Order.Status.PACKED,
            delivery_zone=delivery_zone,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444',
            subtotal=10000,
            delivery_fee=2000,
            total=12000
        )
        
        # Create delivery
        delivery = Delivery.objects.create(
            order=order,
            delivery_number='DEL-003',
            zone=delivery_zone,
            fee=2000,
            status=DeliveryStatus.PENDING,
            delivery_address_line1='123 Main St',
            delivery_city='N\'Djamena',
            delivery_region='Chari-Baguirmi',
            delivery_phone='+23544444444'
        )
        
        api_client.force_authenticate(user=admin_user)
        
        url = f'/api/v1/delivery/deliveries/{delivery.id}/assign/'
        response = api_client.post(url, {
            'agent_id': agent.id
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == DeliveryStatus.ASSIGNED
        
        delivery.refresh_from_db()
        assert delivery.agent == agent
        assert delivery.status == DeliveryStatus.ASSIGNED
        assert delivery.zone == delivery_zone
        assert delivery.fee == 2000
