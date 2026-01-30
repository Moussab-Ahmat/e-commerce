"""
Views for delivery app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import DeliveryZone
from .serializers import DeliveryZoneSerializer
from .services import calculate_delivery_fee


class DeliveryZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """Delivery zone viewset."""
    queryset = DeliveryZone.objects.filter(is_active=True)
    serializer_class = DeliveryZoneSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def calculate_fee(self, request):
        """Calculate delivery fee for a zone and cart total."""
        zone_id = request.data.get('zone_id')
        cart_total_xaf = request.data.get('cart_total_xaf')

        if not zone_id:
            return Response(
                {'error': 'zone_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cart_total_xaf is None:
            return Response(
                {'error': 'cart_total_xaf is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart_total_xaf = int(cart_total_xaf)
            if cart_total_xaf < 0:
                raise ValueError('cart_total_xaf must be non-negative')
        except (ValueError, TypeError):
            return Response(
                {'error': 'cart_total_xaf must be a non-negative integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_fee = calculate_delivery_fee(zone_id, cart_total_xaf)

        return Response({
            'zone_id': zone_id,
            'cart_total_xaf': cart_total_xaf,
            'delivery_fee_xaf': delivery_fee
        })

