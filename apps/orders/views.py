"""
Views for orders app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .services import OrderService


class OrderViewSet(viewsets.ModelViewSet):
    """Order viewset."""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return orders for current user or all for staff."""
        if self.request.user.is_staff:
            queryset = Order.objects.all()
        else:
            queryset = Order.objects.filter(user=self.request.user)
        
        return queryset.select_related(
            'user', 'delivery_zone'
        ).prefetch_related('items__product')
    
    def get_serializer_class(self):
        """Use create serializer for creation."""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create order with idempotency support."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get('Idempotency-Key')
        
        # Prepare delivery info
        delivery_info = {
            'zone_id': serializer.validated_data.get('delivery_zone_id'),
            'latitude': serializer.validated_data.get('delivery_latitude'),
            'longitude': serializer.validated_data.get('delivery_longitude'),
            'address_line1': serializer.validated_data.get('delivery_address_line1', ''),
            'address_line2': serializer.validated_data.get('delivery_address_line2', ''),
            'city': serializer.validated_data.get('delivery_city', ''),
            'region': serializer.validated_data.get('delivery_region', ''),
            'postal_code': serializer.validated_data.get('delivery_postal_code', ''),
            'phone': serializer.validated_data.get('delivery_phone'),
        }
        
        # Create order
        result = OrderService.create_order(
            user=request.user,
            items=serializer.validated_data['items'],
            delivery_info=delivery_info,
            idempotency_key=idempotency_key,
            customer_notes=serializer.validated_data.get('customer_notes', '')
        )
        
        if not result['success']:
            return Response(
                {'errors': result['errors']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If duplicate, return existing order
        if result['is_duplicate']:
            return Response(
                OrderSerializer(result['order']).data,
                status=status.HTTP_200_OK  # 200 for idempotent duplicate
            )
        
        return Response(
            OrderSerializer(result['order']).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order (only before CONFIRMED)."""
        result = OrderService.cancel_order(
            order_id=pk,
            user=request.user
        )
        
        if not result['success']:
            return Response(
                {'errors': result['errors']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(OrderSerializer(result['order']).data)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm order and reserve inventory."""
        result = OrderService.confirm_order(
            order_id=pk,
            user=request.user
        )
        
        if not result['success']:
            return Response(
                {'errors': result['errors']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(OrderSerializer(result['order']).data)
