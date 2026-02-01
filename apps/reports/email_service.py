"""
Email service for sending invoices to customers.
"""
import os
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from apps.orders.models import Order
from .models import Invoice, InvoiceSent

logger = logging.getLogger(__name__)

COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'MonEntreprise')
COMPANY_EMAIL = getattr(settings, 'COMPANY_EMAIL', 'contact@monentreprise.com')


def _format_price(amount):
    if amount is None:
        return '0 FCFA'
    return f'{amount:,.0f} FCFA'.replace(',', ' ')


def _get_status_display(status):
    mapping = {
        'PENDING_CONFIRMATION': 'En attente',
        'CONFIRMED': 'Confirmee',
        'DELIVERED': 'Livree',
        'COMPLETED': 'Terminee',
        'CANCELLED': 'Annulee',
    }
    return mapping.get(status, status)


def _build_email_html(order, invoice):
    """Build HTML email content for the invoice."""
    user = order.user
    customer_name = user.get_full_name() if hasattr(user, 'get_full_name') else str(user)

    address_parts = [order.delivery_address_line1]
    if order.delivery_address_line2:
        address_parts.append(order.delivery_address_line2)
    if order.delivery_city:
        address_parts.append(order.delivery_city)
    if order.delivery_region:
        address_parts.append(order.delivery_region)
    delivery_address = ', '.join(p for p in address_parts if p)

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">

    <div style="text-align: center; margin-bottom: 30px;">
      <h1 style="color: #1976D2;">{COMPANY_NAME}</h1>
    </div>

    <p>Bonjour <strong>{customer_name}</strong>,</p>

    <p>Merci pour votre commande sur <strong>{COMPANY_NAME}</strong> !</p>

    <p>Nous avons le plaisir de vous confirmer votre commande
       <strong>#{order.order_number}</strong> d'un montant total de
       <strong>{_format_price(order.total)}</strong>.</p>

    <p>Vous trouverez ci-joint votre facture en piece jointe.</p>

    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
      <h3 style="margin-top: 0;">Recapitulatif</h3>
      <p><strong>Commande:</strong> #{order.order_number}</p>
      <p><strong>Date:</strong> {order.created_at.strftime('%d/%m/%Y')}</p>
      <p><strong>Montant:</strong> {_format_price(order.total)}</p>
      <p><strong>Statut:</strong> {_get_status_display(order.status)}</p>
    </div>

    <p><strong>Adresse de livraison:</strong><br>
       {delivery_address}</p>

    <p>Pour toute question concernant votre commande, n'hesitez pas a nous contacter.</p>

    <p>Cordialement,<br>
       <strong>L'equipe {COMPANY_NAME}</strong></p>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

    <p style="font-size: 12px; color: #666;">
      Cet email a ete envoye automatiquement, merci de ne pas y repondre directement.<br>
      Pour nous contacter: {COMPANY_EMAIL}
    </p>

  </div>
</body>
</html>"""
    return html


def send_invoice_email(order_id, pdf_file_path, recipient_email=None):
    """
    Send an invoice email with PDF attachment.

    Args:
        order_id: The order ID.
        pdf_file_path: Relative path to the PDF in MEDIA_ROOT.
        recipient_email: Override recipient (default: customer email).

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        return False, f'Commande #{order_id} introuvable'

    try:
        invoice = Invoice.objects.get(order=order)
    except Invoice.DoesNotExist:
        return False, 'Facture non generee pour cette commande'

    # Determine recipient
    user = order.user
    to_email = recipient_email or getattr(user, 'email', None)
    if not to_email:
        return False, 'Aucune adresse email disponible pour le client'

    # Build PDF absolute path
    abs_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_file_path)
    if not os.path.isfile(abs_pdf_path):
        return False, f'Fichier PDF introuvable: {pdf_file_path}'

    # Build email
    subject = f'Votre facture - Commande #{order.order_number}'
    html_body = _build_email_html(order, invoice)

    email = EmailMessage(
        subject=subject,
        body=html_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[to_email],
    )
    email.content_subtype = 'html'

    # Attach PDF
    attachment_name = f'Facture_{order.order_number}.pdf'
    email.attach_file(abs_pdf_path)
    # Rename the attachment
    if email.attachments:
        content = email.attachments[-1]
        if isinstance(content, tuple) and len(content) == 3:
            email.attachments[-1] = (attachment_name, content[1], content[2])

    # Send
    try:
        email.send(fail_silently=False)
        InvoiceSent.objects.create(
            invoice=invoice,
            sent_to=to_email,
            status=InvoiceSent.Status.SENT,
        )
        logger.info(f'Invoice {invoice.invoice_number} sent to {to_email}')
        return True, f'Facture envoyee a {to_email}'

    except Exception as e:
        error_msg = str(e)
        InvoiceSent.objects.create(
            invoice=invoice,
            sent_to=to_email,
            status=InvoiceSent.Status.FAILED,
            error_message=error_msg,
        )
        logger.error(f'Failed to send invoice {invoice.invoice_number} to {to_email}: {error_msg}')
        return False, f'Echec de l\'envoi: {error_msg}'
