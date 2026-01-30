"""
Views for deliveries app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from .models import DeliveryAgent, Delivery
from .serializers import DeliveryAgentSerializer, DeliverySerializer
from core.exceptions import InvalidDeliveryStatusError
try:
    from apps.audit.utils import log_audit_event
except ImportError:
    # Audit app might not exist, create a no-op function
    def log_audit_event(*args, **kwargs):
        pass


class DeliveryAgentViewSet(viewsets.ModelViewSet):
    """Delivery agent viewset."""
    queryset = DeliveryAgent.objects.filter(is_active=True)
    serializer_class = DeliveryAgentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        if self.request.user.is_staff:
            return DeliveryAgent.objects.all()
        # Agents can only see themselves
        if hasattr(self.request.user, 'delivery_agent'):
            return DeliveryAgent.objects.filter(user=self.request.user)
        return DeliveryAgent.objects.none()


class DeliveryViewSet(viewsets.ModelViewSet):
    """Delivery viewset."""
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        if self.request.user.is_staff:
            return Delivery.objects.all()
        # Agents see their own deliveries
        if hasattr(self.request.user, 'delivery_agent'):
            return Delivery.objects.filter(agent=self.request.user.delivery_agent)
        # Customers see their order deliveries
        return Delivery.objects.filter(order__user=self.request.user)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def assign(self, request, pk=None):
        """Assign delivery to agent (admin/ops only)."""
        if not (request.user.is_staff or request.user.role == 'ADMIN'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        delivery = self.get_object()
        agent_id = request.data.get('agent_id')
        
        if not agent_id:
            return Response(
                {'error': 'agent_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            agent = DeliveryAgent.objects.get(pk=agent_id, is_active=True)
        except DeliveryAgent.DoesNotExist:
            return Response(
                {'error': 'Delivery agent not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update delivery with zone and fee from order
        delivery.agent = agent
        delivery.zone = delivery.order.delivery_zone
        delivery.fee = delivery.order.delivery_fee
        delivery.transition_status(Delivery.DeliveryStatus.ASSIGNED, user=request.user)
        
        # Log audit event
        log_audit_event(
            user=request.user,
            action='ASSIGN_DELIVERY',
            resource_type='Delivery',
            related_object=delivery,
            new_values={'agent_id': agent.agent_id, 'status': 'ASSIGNED'},
            request=request
        )
        
        return Response(DeliverySerializer(delivery).data)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update delivery status."""
        delivery = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions
        if not request.user.is_staff and delivery.agent.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            old_status = delivery.status
            delivery.transition_status(new_status, user=request.user)
            
            # If delivered, update order status
            if new_status == Delivery.DeliveryStatus.DELIVERED:
                delivery.order.transition_status('DELIVERED', user=request.user)
            
            # Log audit event
            log_audit_event(
                user=request.user,
                action='UPDATE_DELIVERY_STATUS',
                resource_type='Delivery',
                related_object=delivery,
                old_values={'status': old_status},
                new_values={'status': new_status},
                request=request
            )
            
            return Response(DeliverySerializer(delivery).data)
        except InvalidDeliveryStatusError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

