"""
API views for invoice generation, sending, and reports.
"""
import logging
from datetime import datetime, time

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from apps.admin_api.permissions import IsAdmin
from apps.orders.models import Order
from .models import Invoice
from .serializers import (
    InvoiceSerializer, SendInvoiceSerializer,
    SalesReportSerializer, DeliveriesReportSerializer,
)
from .invoice_generator import InvoiceGenerator
from .email_service import send_invoice_email
from .report_generators import (
    generate_sales_report,
    generate_deliveries_report,
    generate_stock_report,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# INVOICE ENDPOINTS
# ═══════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def generate_invoice(request, order_id):
    """Generate PDF invoice for an order."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        generator = InvoiceGenerator()
        pdf_path = generator.generate_invoice(order_id)
        invoice = Invoice.objects.get(order=order)
        serializer = InvoiceSerializer(invoice, context={'request': request})

        return Response({
            'success': True,
            'invoice_number': invoice.invoice_number,
            'pdf_url': serializer.data['pdf_url'],
            'message': 'Facture generee avec succes',
        })
    except Exception as e:
        logger.exception(f'Invoice generation failed for order {order_id}')
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def send_invoice(request, order_id):
    """Send invoice by email. Generates PDF first if needed."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'success': False, 'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check for custom recipient
    serializer = SendInvoiceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    recipient = serializer.validated_data.get('email')

    # Generate invoice if not exists
    try:
        invoice = Invoice.objects.get(order=order)
        pdf_path = invoice.pdf_file.name
        if not pdf_path:
            generator = InvoiceGenerator()
            pdf_path = generator.generate_invoice(order_id)
    except Invoice.DoesNotExist:
        generator = InvoiceGenerator()
        pdf_path = generator.generate_invoice(order_id)

    # Send email
    success, message = send_invoice_email(order_id, pdf_path, recipient)

    if success:
        return Response({
            'success': True,
            'message': message,
            'sent_at': timezone.now().isoformat(),
        })
    else:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def invoice_history(request, order_id):
    """Get invoice and send history for an order."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        invoice = Invoice.objects.get(order=order)
        serializer = InvoiceSerializer(invoice, context={'request': request})
        return Response(serializer.data)
    except Invoice.DoesNotExist:
        return Response({
            'invoice_number': None,
            'pdf_url': None,
            'created_at': None,
            'sends': [],
        })


# ═══════════════════════════════════════════
# REPORT ENDPOINTS
# ═══════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def sales_report(request):
    """Generate sales report PDF."""
    serializer = SalesReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    start = datetime.combine(serializer.validated_data['start_date'], time.min)
    end = datetime.combine(serializer.validated_data['end_date'], time.max)

    start = timezone.make_aware(start) if timezone.is_naive(start) else start
    end = timezone.make_aware(end) if timezone.is_naive(end) else end

    try:
        pdf_path = generate_sales_report(start, end)
        from django.conf import settings as s
        pdf_url = request.build_absolute_uri(f'{s.MEDIA_URL}{pdf_path}')
        return Response({
            'success': True,
            'pdf_url': pdf_url,
            'message': 'Rapport de ventes genere',
        })
    except Exception as e:
        logger.exception('Sales report generation failed')
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def deliveries_report(request):
    """Generate deliveries report PDF."""
    serializer = DeliveriesReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    start = datetime.combine(serializer.validated_data['start_date'], time.min)
    end = datetime.combine(serializer.validated_data['end_date'], time.max)
    courier_id = serializer.validated_data.get('courier_id')

    start = timezone.make_aware(start) if timezone.is_naive(start) else start
    end = timezone.make_aware(end) if timezone.is_naive(end) else end

    try:
        pdf_path = generate_deliveries_report(start, end, courier_id)
        from django.conf import settings as s
        pdf_url = request.build_absolute_uri(f'{s.MEDIA_URL}{pdf_path}')
        return Response({
            'success': True,
            'pdf_url': pdf_url,
            'message': 'Rapport de livraisons genere',
        })
    except Exception as e:
        logger.exception('Deliveries report generation failed')
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def stock_report(request):
    """Generate stock report PDF."""
    try:
        pdf_path = generate_stock_report()
        from django.conf import settings as s
        pdf_url = request.build_absolute_uri(f'{s.MEDIA_URL}{pdf_path}')
        return Response({
            'success': True,
            'pdf_url': pdf_url,
            'message': 'Rapport de stock genere',
        })
    except Exception as e:
        logger.exception('Stock report generation failed')
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
