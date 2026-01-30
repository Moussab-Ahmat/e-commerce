"""
Tests for catalog app.
"""
import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import override_settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.catalog.models import Category, Product, ProductImage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def category():
    """Create a test category."""
    return Category.objects.create(
        name='Electronics',
        slug='electronics',
        description='Electronic products'
    )


@pytest.fixture
def product(category):
    """Create a test product."""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        description='Test description',
        category=category,
        price=50000,
        stock_quantity=10,
        sku='TEST-001'
    )


@pytest.fixture
def product_with_images(product):
    """Create a product with images."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    image_file = SimpleUploadedFile(
        'test_image.jpg',
        img_io.read(),
        content_type='image/jpeg'
    )
    
    ProductImage.objects.create(
        product=product,
        original=image_file,
        alt_text='Test image',
        is_primary=True,
        order=0
    )
    
    return product


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestCategoryEndpoints:
    """Test category endpoints."""
    
    def test_list_categories(self, api_client, category):
        """Test listing categories."""
        url = '/api/v1/catalog/categories/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == category.name
    
    def test_list_categories_only_active(self, api_client, category):
        """Test that only active categories are returned."""
        inactive_category = Category.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
        
        url = '/api/v1/catalog/categories/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == category.name
        assert inactive_category.name not in [c['name'] for c in response.data]
    
    def test_retrieve_category(self, api_client, category):
        """Test retrieving a single category."""
        url = f'/api/v1/catalog/categories/{category.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == category.name
        assert response.data['slug'] == category.slug


@pytest.mark.django_db
class TestProductEndpoints:
    """Test product endpoints."""
    
    def test_list_products_pagination(self, api_client, category):
        """Test product list pagination."""
        # Create 25 products
        for i in range(25):
            Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                category=category,
                price=10000 * (i + 1),
                stock_quantity=10,
                sku=f'PROD-{i:03d}'
            )
        
        url = '/api/v1/catalog/products/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 25
        assert len(response.data['results']) == 20  # Default page size
    
    def test_list_products_custom_page_size(self, api_client, category):
        """Test product list with custom page size."""
        # Create 10 products
        for i in range(10):
            Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                category=category,
                price=10000 * (i + 1),
                stock_quantity=10,
                sku=f'PROD-{i:03d}'
            )
        
        url = '/api/v1/catalog/products/?page_size=5'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['next'] is not None
    
    def test_list_products_lightweight_fields(self, api_client, product):
        """Test that list endpoint returns lightweight fields."""
        url = '/api/v1/catalog/products/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        product_data = response.data['results'][0]
        
        # Check lightweight fields are present
        assert 'id' in product_data
        assert 'name' in product_data
        assert 'slug' in product_data
        assert 'category_name' in product_data
        assert 'price' in product_data
        assert 'stock_quantity' in product_data
        assert 'sku' in product_data
        assert 'is_featured' in product_data
        
        # Check full fields are NOT present
        assert 'description' not in product_data
        assert 'category' not in product_data  # Only category_name
        assert 'images' not in product_data  # Only primary_image
    
    def test_retrieve_product_full_fields(self, api_client, product_with_images):
        """Test that detail endpoint returns full fields."""
        url = f'/api/v1/catalog/products/{product_with_images.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check full fields are present
        assert 'id' in response.data
        assert 'name' in response.data
        assert 'description' in response.data
        assert 'category' in response.data
        assert 'price' in response.data
        assert 'stock_quantity' in response.data
        assert 'images' in response.data
        assert isinstance(response.data['images'], list)
    
    def test_list_products_only_active(self, api_client, category, product):
        """Test that only active products are returned."""
        inactive_product = Product.objects.create(
            name='Inactive Product',
            slug='inactive-product',
            category=category,
            price=50000,
            stock_quantity=10,
            sku='INACTIVE-001',
            is_active=False
        )
        
        url = '/api/v1/catalog/products/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        product_names = [p['name'] for p in response.data['results']]
        assert product.name in product_names
        assert inactive_product.name not in product_names


@pytest.mark.django_db
class TestProductCaching:
    """Test Redis caching for products list."""
    
    def test_cache_miss_on_first_request(self, api_client, category):
        """Test cache miss on first request."""
        Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=category,
            price=50000,
            stock_quantity=10,
            sku='TEST-001'
        )
        
        # Clear cache
        cache.clear()
        
        url = '/api/v1/catalog/products/'
        
        # First request - cache miss
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            response = api_client.get(url)
            queries_after = len(connection.queries)
            
            assert response.status_code == status.HTTP_200_OK
            assert queries_after > initial_queries  # Database queries made
    
    def test_cache_hit_on_second_request(self, api_client, category):
        """Test cache hit on second request."""
        Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=category,
            price=50000,
            stock_quantity=10,
            sku='TEST-001'
        )
        
        url = '/api/v1/catalog/products/'
        
        # First request - populate cache
        response1 = api_client.get(url)
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request - should hit cache
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            response2 = api_client.get(url)
            queries_after = len(connection.queries)
            
            assert response2.status_code == status.HTTP_200_OK
            assert queries_after == initial_queries  # No new queries (cache hit)
            assert response1.data == response2.data
    
    def test_cache_invalidation_on_product_save(self, api_client, category, product):
        """Test cache invalidation when product is saved."""
        url = '/api/v1/catalog/products/'
        
        # First request - populate cache
        response1 = api_client.get(url)
        assert response1.status_code == status.HTTP_200_OK
        assert len(response1.data['results']) == 1
        
        # Modify and save product (should invalidate cache)
        product.name = 'Updated Product'
        product.save()
        
        # Create new product
        Product.objects.create(
            name='New Product',
            slug='new-product',
            category=category,
            price=60000,
            stock_quantity=5,
            sku='NEW-001'
        )
        
        # Second request - should get fresh data
        response2 = api_client.get(url)
        assert response2.status_code == status.HTTP_200_OK
        assert len(response2.data['results']) == 2
        
        # Verify updated product name
        product_names = [p['name'] for p in response2.data['results']]
        assert 'Updated Product' in product_names
        assert 'New Product' in product_names
    
    def test_cache_ttl(self, api_client, category):
        """Test cache TTL (15 minutes)."""
        Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=category,
            price=50000,
            stock_quantity=10,
            sku='TEST-001'
        )
        
        url = '/api/v1/catalog/products/'
        
        # First request
        response1 = api_client.get(url)
        assert response1.status_code == status.HTTP_200_OK
        
        # Check cache key exists
        cache_key = 'products_list_page_1_size_20'
        cached_data = cache.get(cache_key)
        assert cached_data is not None
        
        # Verify TTL is set (should be around 900 seconds)
        # Note: We can't directly check TTL, but we can verify cache works
        response2 = api_client.get(url)
        assert response2.status_code == status.HTTP_200_OK
        assert response1.data == response2.data


@pytest.mark.django_db
class TestNPlusOneQueries:
    """Test for N+1 query problems."""
    
    def test_no_n_plus_one_in_list_endpoint(self, api_client, category):
        """Test that list endpoint doesn't have N+1 queries."""
        # Create 10 products with images
        products = []
        for i in range(10):
            product = Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                category=category,
                price=10000 * (i + 1),
                stock_quantity=10,
                sku=f'PROD-{i:03d}'
            )
            products.append(product)
            
            # Create image for each product
            img = Image.new('RGB', (100, 100), color='red')
            img_io = BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            
            image_file = SimpleUploadedFile(
                f'test_image_{i}.jpg',
                img_io.read(),
                content_type='image/jpeg'
            )
            
            ProductImage.objects.create(
                product=product,
                original=image_file,
                is_primary=True,
                order=0
            )
        
        url = '/api/v1/catalog/products/'
        
        # Count queries
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            response = api_client.get(url)
            queries_after = len(connection.queries)
            query_count = queries_after - initial_queries
            
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data['results']) == 10
            
            # Should have minimal queries (category select_related + images prefetch)
            # Expected: 1 for products, 1 for categories (select_related), 1 for images (prefetch)
            # Plus pagination count query = 2-3 queries total, not 10+ (which would be N+1)
            assert query_count <= 5, f"Too many queries: {query_count}. Expected <= 5"
    
    def test_no_n_plus_one_in_detail_endpoint(self, api_client, category):
        """Test that detail endpoint doesn't have N+1 queries."""
        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=category,
            price=50000,
            stock_quantity=10,
            sku='TEST-001'
        )
        
        # Create multiple images
        for i in range(5):
            img = Image.new('RGB', (100, 100), color='red')
            img_io = BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            
            image_file = SimpleUploadedFile(
                f'test_image_{i}.jpg',
                img_io.read(),
                content_type='image/jpeg'
            )
            
            ProductImage.objects.create(
                product=product,
                original=image_file,
                order=i
            )
        
        url = f'/api/v1/catalog/products/{product.id}/'
        
        # Count queries
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            response = api_client.get(url)
            queries_after = len(connection.queries)
            query_count = queries_after - initial_queries
            
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data['images']) == 5
            
            # Should have minimal queries (category select_related + images prefetch)
            # Expected: 1 for product, 1 for category, 1 for images = 2-3 queries
            assert query_count <= 5, f"Too many queries: {query_count}. Expected <= 5"

