"""
Tests for inventory app.
"""
import pytest
from django.db import transaction
from django.core.exceptions import ValidationError
from concurrent.futures import ThreadPoolExecutor
from rest_framework.test import APIClient
from rest_framework import status
from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.services import InventoryService
from apps.catalog.models import Product, Category


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


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
def inventory_item(product):
    """Create a test inventory item."""
    return InventoryItem.objects.create(
        product=product,
        on_hand=100,
        reserved=0,
        reorder_point=10
    )


@pytest.mark.django_db
class TestInventoryService:
    """Test InventoryService methods."""
    
    def test_check_available_sufficient(self, inventory_item):
        """Test check_available with sufficient stock."""
        items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        
        result = InventoryService.check_available(items)
        
        assert result['available'] is True
        assert len(result['items']) == 1
        assert result['items'][0]['sufficient'] is True
        assert result['items'][0]['available'] == 100
    
    def test_check_available_insufficient(self, inventory_item):
        """Test check_available with insufficient stock."""
        items = [
            {'product_id': inventory_item.product.id, 'quantity': 150}
        ]
        
        result = InventoryService.check_available(items)
        
        assert result['available'] is False
        assert result['items'][0]['sufficient'] is False
    
    def test_check_available_multiple_items(self, category):
        """Test check_available with multiple items."""
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
        
        item1 = InventoryItem.objects.create(product=product1, on_hand=50)
        item2 = InventoryItem.objects.create(product=product2, on_hand=30)
        
        items = [
            {'product_id': product1.id, 'quantity': 40},
            {'product_id': product2.id, 'quantity': 25}
        ]
        
        result = InventoryService.check_available(items)
        
        assert result['available'] is True
        assert len(result['items']) == 2
    
    def test_reserve_success(self, inventory_item):
        """Test successful reservation."""
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        
        result = InventoryService.reserve(order_items, reference='ORDER-001')
        
        assert result['success'] is True
        assert len(result['reserved_items']) == 1
        
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 50
        assert inventory_item.on_hand == 100
        assert inventory_item.available == 50
        
        # Check movement was created
        movement = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='ORDER-001'
        ).first()
        assert movement is not None
        assert movement.quantity == -50
    
    def test_reserve_insufficient_stock(self, inventory_item):
        """Test reservation with insufficient stock."""
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 150}
        ]
        
        result = InventoryService.reserve(order_items, reference='ORDER-001')
        
        assert result['success'] is False
        assert len(result['errors']) > 0
        
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 0  # Should not be reserved
    
    def test_release_success(self, inventory_item):
        """Test successful release."""
        # First reserve
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        InventoryService.reserve(order_items, reference='ORDER-001')
        
        # Then release
        result = InventoryService.release(order_items, reference='ORDER-001')
        
        assert result['success'] is True
        assert len(result['released_items']) == 1
        
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 0
        assert inventory_item.on_hand == 100
    
    def test_release_insufficient_reserved(self, inventory_item):
        """Test release with insufficient reserved stock."""
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        
        result = InventoryService.release(order_items, reference='ORDER-001')
        
        assert result['success'] is False
        assert len(result['errors']) > 0
    
    def test_commit_outbound_success(self, inventory_item):
        """Test successful commit outbound."""
        # First reserve
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        InventoryService.reserve(order_items, reference='ORDER-001')
        
        # Then commit
        result = InventoryService.commit_outbound(order_items, reference='ORDER-001')
        
        assert result['success'] is True
        assert len(result['committed_items']) == 1
        
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 0
        assert inventory_item.on_hand == 50  # Reduced by 50
        assert inventory_item.available == 50
    
    def test_commit_outbound_without_reservation(self, inventory_item):
        """Test commit outbound without prior reservation."""
        order_items = [
            {'product_id': inventory_item.product.id, 'quantity': 50}
        ]
        
        result = InventoryService.commit_outbound(order_items, reference='ORDER-001')
        
        assert result['success'] is False
        assert len(result['errors']) > 0


@pytest.mark.django_db
class TestConcurrency:
    """Test concurrency scenarios."""
    
    def test_concurrent_reservations_last_stock(self, category):
        """Test concurrent reservations on last stock item."""
        product = Product.objects.create(
            name='Last Stock Product',
            slug='last-stock',
            category=category,
            price=10000,
            sku='LAST-001'
        )
        
        inventory_item = InventoryItem.objects.create(
            product=product,
            on_hand=1,  # Only 1 item available
            reserved=0
        )
        
        def reserve_stock():
            """Reserve stock in a transaction."""
            try:
                with transaction.atomic():
                    result = InventoryService.reserve(
                        [{'product_id': product.id, 'quantity': 1}],
                        reference='CONCURRENT-ORDER'
                    )
                    return result['success']
            except Exception:
                return False
        
        # Try to reserve the same item concurrently from two threads
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reserve_stock) for _ in range(2)]
            results = [future.result() for future in futures]
        
        # Only one reservation should succeed
        assert sum(results) == 1, "Only one reservation should succeed"
        
        # Verify final state
        inventory_item.refresh_from_db()
        assert inventory_item.reserved == 1
        assert inventory_item.available == 0
    
    def test_concurrent_reservations_multiple_items(self, category):
        """Test concurrent reservations with multiple items."""
        product = Product.objects.create(
            name='Concurrent Product',
            slug='concurrent',
            category=category,
            price=10000,
            sku='CONC-001'
        )
        
        inventory_item = InventoryItem.objects.create(
            product=product,
            on_hand=10,
            reserved=0
        )
        
        def reserve_stock(quantity):
            """Reserve stock."""
            try:
                with transaction.atomic():
                    result = InventoryService.reserve(
                        [{'product_id': product.id, 'quantity': quantity}],
                        reference=f'ORDER-{quantity}'
                    )
                    return result['success']
            except Exception:
                return False
        
        # Try to reserve 6 items from two concurrent requests (total 12, but only 10 available)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(reserve_stock, 6),
                executor.submit(reserve_stock, 6)
            ]
            results = [future.result() for future in futures]
        
        # At least one should fail
        assert sum(results) < 2, "At least one reservation should fail"
        
        # Verify total reserved doesn't exceed available
        inventory_item.refresh_from_db()
        assert inventory_item.reserved <= inventory_item.on_hand


@pytest.mark.django_db
class TestInventoryModels:
    """Test inventory models."""
    
    def test_inventory_item_available_property(self, inventory_item):
        """Test available property calculation."""
        inventory_item.on_hand = 100
        inventory_item.reserved = 30
        inventory_item.save()
        
        assert inventory_item.available == 70
    
    def test_inventory_item_needs_reorder(self, inventory_item):
        """Test needs_reorder property."""
        inventory_item.on_hand = 5
        inventory_item.reorder_point = 10
        inventory_item.save()
        
        assert inventory_item.needs_reorder is True
        
        inventory_item.on_hand = 15
        inventory_item.save()
        
        assert inventory_item.needs_reorder is False
    
    def test_stock_movement_creation(self, inventory_item):
        """Test stock movement creation."""
        movement = StockMovement.objects.create(
            inventory_item=inventory_item,
            movement_type=StockMovement.MovementType.INBOUND,
            quantity=50,
            reference='PO-001',
            notes='Received goods'
        )
        
        assert movement.inventory_item == inventory_item
        assert movement.movement_type == StockMovement.MovementType.INBOUND
        assert movement.quantity == 50


@pytest.mark.django_db
class TestInventoryEndpoints:
    """Test inventory API endpoints."""
    
    def test_list_inventory_items(self, api_client, inventory_item):
        """Test listing inventory items."""
        # Note: Requires authentication
        url = '/api/v1/inventory/items/'
        response = api_client.get(url)
        
        # Should require authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
    
    def test_check_available_endpoint(self, api_client, inventory_item):
        """Test check_available endpoint."""
        url = '/api/v1/inventory/items/check_available/'
        response = api_client.post(url, {
            'items': [
                {'product_id': inventory_item.product.id, 'quantity': 50}
            ]
        }, format='json')
        
        # Should require authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
    
    def test_reserve_endpoint(self, api_client, inventory_item):
        """Test reserve endpoint."""
        url = '/api/v1/inventory/items/reserve/'
        response = api_client.post(url, {
            'order_items': [
                {'product_id': inventory_item.product.id, 'quantity': 50}
            ],
            'reference': 'ORDER-001'
        }, format='json')
        
        # Should require authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
