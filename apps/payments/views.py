"""
Views for payments app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Payment, PaymentHistory
from .serializers import PaymentSerializer
from apps.audit.utils import log_audit_event


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment viewset (read-only for MVP)."""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter payments based on user role."""
        if self.request.user.is_staff:
            return Payment.objects.all()
        # Customers see their own payments
        return Payment.objects.filter(order__user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def collect(self, request, pk=None):
        """Collect COD payment (agent/admin only)."""
        payment = self.get_object()
        
        # Check permissions
        is_agent = hasattr(request.user, 'delivery_agent')
        is_admin = request.user.is_staff
        
        if not (is_agent or is_admin):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if payment.status != 'PENDING':
            return Response(
                {'error': f'Payment is already {payment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update payment status
        old_status = payment.status
        payment.status = 'COLLECTED'
        payment.collected_by = request.user.delivery_agent if is_agent else None
        payment.collected_at = timezone.now()
        payment.save()
        
        # Update order payment status
        payment.order.payment_status = 'PAID'
        payment.order.save()
        
        # Create history entry
        PaymentHistory.objects.create(
            payment=payment,
            old_status=old_status,
            new_status='COLLECTED',
            changed_by=request.user,
            notes=request.data.get('notes', '')
        )
        
        # Log audit event
        log_audit_event(
            user=request.user,
            action='COLLECT_PAYMENT',
            resource_type='Payment',
            related_object=payment,
            old_values={'status': old_status},
            new_values={'status': 'COLLECTED'},
            request=request
        )
        
        return Response(PaymentSerializer(payment).data)

