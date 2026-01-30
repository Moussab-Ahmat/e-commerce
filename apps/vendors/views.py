"""
Views for vendor API endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from .models import Shop
from .serializers import (
    ShopSerializer,
    VendorProductSerializer,
    VendorProductListSerializer,
    VendorOrderItemSerializer,
    VendorStatsSerializer,
)
from .permissions import IsVendor, IsVendorOwner
from apps.catalog.models import Product
from apps.orders.models import OrderItem


class VendorDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vendor dashboard - shop info and stats.
    Read-only access to vendor's shop information.
    """

    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        """Return only the current vendor's shop."""
        return Shop.objects.filter(vendor=self.request.user).annotate(
            products_count=Count('products', filter=Q(products__is_active=True)),
            pending_orders_count=Count('order_items', filter=Q(order_items__item_status='PENDING'))
        )

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        """
        Get vendor statistics for dashboard.

        Returns:
            - total_products: Total number of products
            - active_products: Number of active products
            - out_of_stock: Number of out-of-stock products
            - pending_orders: Number of pending order items
            - confirmed_orders: Number of confirmed order items
            - completed_orders: Number of delivered order items
            - total_sales: Total number of sales
            - total_revenue: Total revenue amount
            - this_month_revenue: This month's revenue
        """
        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response(
                {'error': 'No shop found for this vendor'},
                status=status.HTTP_404_NOT_FOUND
            )

        from django.db.models import Sum
        from django.utils import timezone
        from datetime import datetime

        # Calculate product statistics
        total_products = shop.products.count()
        active_products = shop.products.filter(is_active=True).count()
        out_of_stock = shop.products.filter(stock_quantity=0).count()

        # Calculate order statistics
        pending_orders = shop.order_items.filter(item_status='PENDING').count()
        confirmed_orders = shop.order_items.filter(item_status='CONFIRMED').count()
        completed_orders = shop.order_items.filter(item_status='DELIVERED').count()

        # Calculate revenue statistics
        total_revenue = shop.order_items.filter(
            item_status='DELIVERED'
        ).aggregate(total=Sum('total_price'))['total'] or 0

        # This month's revenue
        now = timezone.now()
        month_start = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
        this_month_revenue = shop.order_items.filter(
            item_status='DELIVERED',
            order__created_at__gte=month_start
        ).aggregate(total=Sum('total_price'))['total'] or 0

        # Total sales (number of delivered items)
        total_sales = completed_orders

        stats_data = {
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock': out_of_stock,
            'pending_orders': pending_orders,
            'confirmed_orders': confirmed_orders,
            'completed_orders': completed_orders,
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'this_month_revenue': this_month_revenue,
        }

        serializer = VendorStatsSerializer(stats_data)
        return Response(serializer.data)


class VendorProductViewSet(viewsets.ModelViewSet):
    """
    Vendor product management.
    Full CRUD operations for vendor's products.
    """

    permission_classes = [IsAuthenticated, IsVendor, IsVendorOwner]

    def get_serializer_class(self):
        """Use VendorProductSerializer for all actions."""
        return VendorProductSerializer

    def get_queryset(self):
        """Return only products from vendor's shop."""
        try:
            return Product.objects.filter(
                shop=self.request.user.shop
            ).select_related('category', 'shop').order_by('-created_at')
        except Shop.DoesNotExist:
            return Product.objects.none()

    def perform_create(self, serializer):
        """Auto-assign shop when creating product."""
        serializer.save()

    @action(detail=True, methods=['POST'])
    def toggle_active(self, request, pk=None):
        """Toggle product active status."""
        product = self.get_object()
        product.is_active = not product.is_active
        product.save(update_fields=['is_active'])

        serializer = self.get_serializer(product)
        return Response(serializer.data)


class VendorOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vendor order management.
    View and update status of order items belonging to vendor's shop.
    """

    serializer_class = VendorOrderItemSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        """Return only order items for vendor's shop."""
        try:
            return OrderItem.objects.filter(
                shop=self.request.user.shop
            ).select_related(
                'order', 'order__user', 'product', 'shop'
            ).order_by('-order__created_at')
        except Shop.DoesNotExist:
            return OrderItem.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List all order items with optional filtering by status.

        Query params:
            - status: Filter by item_status (PENDING, CONFIRMED, PREPARING, READY, DELIVERED)
        """
        queryset = self.get_queryset()

        # Filter by status if provided
        item_status = request.query_params.get('status')
        if item_status:
            queryset = queryset.filter(item_status=item_status)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """
        Update order item status.

        Body params:
            - status: New status (CONFIRMED, PREPARING, READY, DELIVERED)
        """
        item = self.get_object()
        new_status = request.data.get('status')

        # Validate status
        valid_statuses = ['CONFIRMED', 'PREPARING', 'READY', 'DELIVERED']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        item.update_status(new_status)

        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """
        Get summary of orders by status.

        Returns counts for each status: PENDING, CONFIRMED, PREPARING, READY, DELIVERED
        """
        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response(
                {'error': 'No shop found for this vendor'},
                status=status.HTTP_404_NOT_FOUND
            )

        summary = {
            'pending': shop.order_items.filter(item_status='PENDING').count(),
            'confirmed': shop.order_items.filter(item_status='CONFIRMED').count(),
            'preparing': shop.order_items.filter(item_status='PREPARING').count(),
            'ready': shop.order_items.filter(item_status='READY').count(),
            'delivered': shop.order_items.filter(item_status='DELIVERED').count(),
        }

        return Response(summary)
