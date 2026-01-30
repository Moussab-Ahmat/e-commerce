"""
Views for warehouse app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from .permissions import IsWarehouseUser
from .serializers import PickingQueueOrderSerializer
from core.exceptions import InvalidOrderStatusError


class WarehouseOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Warehouse order viewset."""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsWarehouseUser]
    
    def get_queryset(self):
        """Optimize queryset."""
        return Order.objects.select_related(
            'user', 'delivery_zone'
        ).prefetch_related('items__product')
    
    @action(detail=False, methods=['get'])
    def picking_queue(self, request):
        """Get picking queue (orders with status CONFIRMED)."""
        orders = Order.objects.filter(
            status=Order.Status.CONFIRMED
        ).select_related(
            'user', 'delivery_zone'
        ).prefetch_related('items__product').order_by('confirmed_at', 'created_at')
        
        serializer = PickingQueueOrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def start_picking(self, request, pk=None):
        """Start picking order (CONFIRMED → PICKING)."""
        try:
            order = Order.objects.select_for_update().get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if order can transition to PICKING
        if not order.can_transition_to(Order.Status.PICKING):
            return Response(
                {'error': f'Cannot start picking. Order status is {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Transition status
        try:
            order.transition_status(Order.Status.PICKING, user=request.user)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except InvalidOrderStatusError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def packed(self, request, pk=None):
        """Mark order as packed (PICKING → PACKED)."""
        try:
            order = Order.objects.select_for_update().get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if order can transition to PACKED
        if not order.can_transition_to(Order.Status.PACKED):
            return Response(
                {'error': f'Cannot mark as packed. Order status is {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Transition status
        try:
            order.transition_status(Order.Status.PACKED, user=request.user)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except InvalidOrderStatusError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
