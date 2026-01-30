"""
Views for inventory app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import InventoryItem, StockMovement
from .serializers import InventoryItemSerializer, StockMovementSerializer
from .services import InventoryService


class InventoryItemViewSet(viewsets.ReadOnlyModelViewSet):
    """Inventory item viewset."""
    queryset = InventoryItem.objects.select_related('product')
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def check_available(self, request):
        """Check if items are available."""
        items = request.data.get('items', [])
        
        if not items:
            return Response(
                {'error': 'items list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = InventoryService.check_available(items)
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def reserve(self, request):
        """Reserve stock for order items."""
        order_items = request.data.get('order_items', [])
        reference = request.data.get('reference', '')
        
        if not order_items:
            return Response(
                {'error': 'order_items list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = InventoryService.reserve(order_items, reference=reference)
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def release(self, request):
        """Release reserved stock."""
        order_items = request.data.get('order_items', [])
        reference = request.data.get('reference', '')
        
        if not order_items:
            return Response(
                {'error': 'order_items list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = InventoryService.release(order_items, reference=reference)
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def commit_outbound(self, request):
        """Commit outbound stock."""
        order_items = request.data.get('order_items', [])
        reference = request.data.get('reference', '')
        
        if not order_items:
            return Response(
                {'error': 'order_items list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not reference:
            return Response(
                {'error': 'reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = InventoryService.commit_outbound(order_items, reference=reference)
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Stock movement viewset."""
    queryset = StockMovement.objects.select_related('inventory_item__product', 'created_by')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by inventory_item if provided."""
        queryset = super().get_queryset()
        inventory_item_id = self.request.query_params.get('inventory_item_id')
        
        if inventory_item_id:
            queryset = queryset.filter(inventory_item_id=inventory_item_id)
        
        return queryset
