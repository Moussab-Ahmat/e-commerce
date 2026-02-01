"""Courier API views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .permissions import IsCourier
from .serializers import (
    CourierDeliverySerializer,
    CourierDeliveryUpdateStatusSerializer
)
from apps.deliveries.models import Delivery, DeliveryStatus


class CourierDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Courier delivery viewset - read only with custom actions."""
    serializer_class = CourierDeliverySerializer
    permission_classes = [IsAuthenticated, IsCourier]

    def get_queryset(self):
        """Get deliveries for current courier."""
        # Get courier's delivery agent
        try:
            agent = self.request.user.delivery_agent
            return Delivery.objects.filter(agent=agent).select_related(
                'order__user', 'agent__user', 'zone'
            ).prefetch_related('order__items__product__images').order_by('-created_at')
        except Exception:
            return Delivery.objects.none()

    @action(detail=False, methods=['GET'])
    def my_deliveries(self, request):
        """Get all deliveries for the current courier."""
        queryset = self.get_queryset()

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def assigned(self, request):
        """Get assigned deliveries (not yet in transit)."""
        queryset = self.get_queryset().filter(status=DeliveryStatus.ASSIGNED)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def in_transit(self, request):
        """Get deliveries in transit."""
        queryset = self.get_queryset().filter(status=DeliveryStatus.IN_TRANSIT)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def completed(self, request):
        """Get completed deliveries."""
        queryset = self.get_queryset().filter(
            status__in=[DeliveryStatus.DELIVERED, DeliveryStatus.COMPLETED]
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Update delivery status."""
        delivery = self.get_object()
        serializer = CourierDeliveryUpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        failure_reason = serializer.validated_data.get('failure_reason', '')

        # Check if transition is valid
        if not delivery.can_transition_to(new_status):
            return Response(
                {'error': f'Cannot transition from {delivery.status} to {new_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Update status
            delivery.transition_status(new_status, user=request.user)

            # Update notes and failure reason if provided
            if notes:
                delivery.delivery_notes = notes
            if failure_reason:
                delivery.failure_reason = failure_reason

            delivery.save(update_fields=['delivery_notes', 'failure_reason'])

            return Response({
                'message': 'Status updated successfully',
                'delivery': CourierDeliverySerializer(delivery, context={'request': request}).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['POST'])
    def start_delivery(self, request, pk=None):
        """Start delivery (transition to IN_TRANSIT)."""
        delivery = self.get_object()

        if delivery.status != DeliveryStatus.ASSIGNED:
            return Response(
                {'error': 'Can only start delivery from ASSIGNED status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delivery.transition_status(DeliveryStatus.IN_TRANSIT, user=request.user)

            # Notify client: livreur en route
            try:
                from apps.notifications.push import send_push_notification
                order = delivery.order
                send_push_notification(
                    user_id=order.user_id,
                    title='Livreur en route',
                    body=f'Votre livreur est en route avec votre commande #{order.order_number} !',
                    notification_type='order_on_the_way',
                    data={'type': 'order_on_the_way', 'order_id': str(order.id)},
                )
            except Exception:
                pass

            return Response({
                'message': 'Delivery started successfully',
                'delivery': CourierDeliverySerializer(delivery, context={'request': request}).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['POST'])
    def mark_delivered(self, request, pk=None):
        """Mark delivery as delivered."""
        delivery = self.get_object()

        if delivery.status != DeliveryStatus.IN_TRANSIT:
            return Response(
                {'error': 'Can only mark as delivered from IN_TRANSIT status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delivery.transition_status(DeliveryStatus.DELIVERED, user=request.user)

            # Auto-send invoice if enabled
            try:
                from django.conf import settings as app_settings
                if getattr(app_settings, 'AUTO_SEND_INVOICE_ON_DELIVERY', False):
                    from apps.reports.invoice_generator import InvoiceGenerator
                    from apps.reports.email_service import send_invoice_email
                    gen = InvoiceGenerator()
                    pdf_path = gen.generate_invoice(delivery.order_id)
                    send_invoice_email(delivery.order_id, pdf_path)
            except Exception:
                pass  # Don't block delivery on invoice failure

            # Notify client: commande livree
            try:
                from apps.notifications.push import send_push_notification
                order = delivery.order
                send_push_notification(
                    user_id=order.user_id,
                    title='Commande livree',
                    body=f'Votre commande #{order.order_number} a ete livree. Merci pour votre achat !',
                    notification_type='order_delivered',
                    data={'type': 'order_delivered', 'order_id': str(order.id)},
                )
            except Exception:
                pass

            return Response({
                'message': 'Delivery marked as delivered successfully',
                'delivery': CourierDeliverySerializer(delivery, context={'request': request}).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        """Get delivery statistics for current courier."""
        queryset = self.get_queryset()

        total = queryset.count()
        assigned = queryset.filter(status=DeliveryStatus.ASSIGNED).count()
        in_transit = queryset.filter(status=DeliveryStatus.IN_TRANSIT).count()
        completed = queryset.filter(status__in=[DeliveryStatus.DELIVERED, DeliveryStatus.COMPLETED]).count()
        failed = queryset.filter(status=DeliveryStatus.FAILED).count()

        # Calculate success rate
        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 0

        # Today's deliveries
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_deliveries = queryset.filter(created_at__gte=today_start).count()
        today_completed = queryset.filter(
            status__in=[DeliveryStatus.DELIVERED, DeliveryStatus.COMPLETED],
            completed_at__gte=today_start
        ).count()

        return Response({
            'total': total,
            'assigned': assigned,
            'in_transit': in_transit,
            'completed': completed,
            'failed': failed,
            'success_rate': round(success_rate, 2),
            'today_deliveries': today_deliveries,
            'today_completed': today_completed,
        })
