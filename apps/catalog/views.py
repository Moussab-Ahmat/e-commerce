"""
Views for catalog app.
"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from django.db import models
from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Category viewset."""
    queryset = Category.objects.filter(is_active=True).select_related('parent')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Product viewset with caching."""
    queryset = Product.objects.filter(is_active=True, is_published=True).select_related('category')
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """Use lightweight serializer for list, full for detail."""
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        """Optimize queryset for list view with filtering."""
        queryset = super().get_queryset()

        # Apply category filter if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Apply search filter if provided
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(sku__icontains=search)
            )

        # Apply on_sale filter if provided
        on_sale = self.request.query_params.get('on_sale')
        if on_sale is not None:
            queryset = queryset.filter(is_on_sale=True)

        if self.action == 'list':
            # Prefetch images for list view to avoid N+1
            queryset = queryset.prefetch_related(
                models.Prefetch(
                    'images',
                    queryset=ProductImage.objects.filter(
                        is_primary=True
                    ).order_by('order')
                )
            )
            # Order by newest first
            queryset = queryset.order_by('-created_at')
        else:
            # Prefetch all images for detail view
            queryset = queryset.prefetch_related('images')

        return queryset
    
    def list(self, request, *args, **kwargs):
        """List products with Redis caching."""
        # Get pagination and filter parameters
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', None)
        category = request.query_params.get('category', '')
        search = request.query_params.get('search', '')

        # Use default page size from settings if not provided
        if page_size is None:
            from django.conf import settings
            page_size = getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 20)

        # Build cache key including filters
        on_sale = request.query_params.get('on_sale', '')
        cache_key = f'products_list_page_{page}_size_{page_size}_cat_{category}_search_{search}_sale_{on_sale}'

        # Try to get cached response
        cached_response = cache.get(cache_key)

        if cached_response is not None:
            return Response(cached_response)

        # Get response from database
        response = super().list(request, *args, **kwargs)

        # Cache the response data (5 minutes = 300 seconds for filtered results)
        cache_timeout = 300 if (category or search) else 900
        cache.set(cache_key, response.data, timeout=cache_timeout)

        return response
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve product detail."""
        return super().retrieve(request, *args, **kwargs)
