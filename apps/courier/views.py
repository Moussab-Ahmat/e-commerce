"""
Views for courier app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.deliveries.models import Delivery
from .serializers import CourierDeliverySerializer, DeliveryStatusUpdateSerializer
from .permissions import IsCourierUser
from .services import CourierService


class CourierDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Courier delivery viewset."""
    queryset = Delivery.objects.all()
    serializer_class = CourierDeliverySerializer
    permission_classes = [IsAuthenticated, IsCourierUser]
    
    def get_queryset(self):
        """Return deliveries assigned to current courier."""
        # Get delivery agent for current user
        if hasattr(self.request.user, 'delivery_agent'):
            agent = self.request.user.delivery_agent
            return Delivery.objects.filter(
                agent=agent
            ).select_related(
                'order__user', 'zone', 'agent__user'
            ).prefetch_related('order__items__product')
        
        # If user has COURIER role but no delivery_agent, return empty
        return Delivery.objects.none()
    
    @action(detail=True, methods=['post'])
    def status(self, request, pk=None):
        """Update delivery status (IN_TRANSIT, DELIVERED, FAILED)."""
        serializer = DeliveryStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        failure_reason = serializer.validated_data.get('failure_reason', '')
        
        result = CourierService.update_delivery_status(
            delivery_id=pk,
            new_status=new_status,
            user=request.user,
            notes=notes,
            failure_reason=failure_reason
        )
        
        if not result['success']:
            return Response(
                {'errors': result['errors']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(CourierDeliverySerializer(result['delivery']).data)
