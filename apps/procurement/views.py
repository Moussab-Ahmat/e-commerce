"""
Views for procurement app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Supplier, PurchaseOrder, GoodsReceipt
from .serializers import (
    SupplierSerializer, PurchaseOrderSerializer,
    GoodsReceiptSerializer
)
from .services import ProcurementService


class SupplierViewSet(viewsets.ModelViewSet):
    """Supplier viewset."""
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """Purchase order viewset."""
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset."""
        queryset = super().get_queryset()
        supplier_id = self.request.query_params.get('supplier_id')
        status_filter = self.request.query_params.get('status')
        
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('supplier', 'created_by').prefetch_related('items__product')


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    """Goods receipt viewset."""
    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset."""
        queryset = super().get_queryset()
        purchase_order_id = self.request.query_params.get('purchase_order_id')
        status_filter = self.request.query_params.get('status')
        
        if purchase_order_id:
            queryset = queryset.filter(purchase_order_id=purchase_order_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related(
            'purchase_order__supplier', 'created_by', 'validated_by'
        ).prefetch_related('items__purchase_order_item__product')
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate goods receipt."""
        receipt = self.get_object()
        
        result = ProcurementService.validate_receipt(
            receipt_id=receipt.id,
            validated_by=request.user
        )
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        # Return updated receipt
        serializer = self.get_serializer(receipt)
        return Response({
            'message': 'Receipt validated successfully',
            'result': result,
            'receipt': serializer.data
        })
