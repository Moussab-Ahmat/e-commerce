"""
PDF Invoice Generator using ReportLab.
Generates professional A4 invoices with promo support.
"""
import os
import logging
from datetime import datetime
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.orders.models import Order
from .models import Invoice

logger = logging.getLogger(__name__)

# Company defaults (overridden by settings)
COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'MonEntreprise')
COMPANY_ADDRESS = getattr(settings, 'COMPANY_ADDRESS', '123 Rue Principale')
COMPANY_CITY = getattr(settings, 'COMPANY_CITY', "N'Djamena, Tchad")
COMPANY_PHONE = getattr(settings, 'COMPANY_PHONE', '+235 XX XX XX XX')
COMPANY_EMAIL = getattr(settings, 'COMPANY_EMAIL', 'contact@monentreprise.com')
COMPANY_LOGO_PATH = getattr(settings, 'COMPANY_LOGO_PATH', None)

PRIMARY_COLOR_HEX = getattr(settings, 'INVOICE_PRIMARY_COLOR', '#1976D2')
SECONDARY_COLOR_HEX = getattr(settings, 'INVOICE_SECONDARY_COLOR', '#4CAF50')


def _hex_to_color(hex_str):
    """Convert hex color string to ReportLab Color."""
    hex_str = hex_str.lstrip('#')
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


PRIMARY_COLOR = _hex_to_color(PRIMARY_COLOR_HEX)
SECONDARY_COLOR = _hex_to_color(SECONDARY_COLOR_HEX)
TEXT_COLOR = _hex_to_color('#333333')
LIGHT_GRAY = _hex_to_color('#F5F5F5')
MEDIUM_GRAY = _hex_to_color('#E0E0E0')
DARK_GRAY = _hex_to_color('#666666')


def _format_price(amount):
    """Format integer XAF amount with thousands separator."""
    if amount is None:
        return '0 FCFA'
    return f'{amount:,.0f} FCFA'.replace(',', ' ')


def _get_status_display(status):
    """Return French display for order status."""
    mapping = {
        'PENDING_CONFIRMATION': 'En attente',
        'CONFIRMED': 'Confirmee',
        'PICKING': 'Preparation',
        'PACKED': 'Emballee',
        'PROCESSING': 'En traitement',
        'READY_FOR_DELIVERY': 'Prete a livrer',
        'OUT_FOR_DELIVERY': 'En livraison',
        'DELIVERED': 'Livree',
        'COMPLETED': 'Terminee',
        'CANCELLED': 'Annulee',
        'REFUNDED': 'Remboursee',
    }
    return mapping.get(status, status)


def _get_payment_display(method):
    """Return French display for payment method."""
    mapping = {
        'COD': 'Especes a la livraison',
        'MOBILE_MONEY': 'Mobile Money',
        'CARD': 'Carte bancaire',
    }
    return mapping.get(method, method)


class InvoiceGenerator:
    """Generates professional PDF invoices for orders."""

    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 20 * mm
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Define custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            'InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=PRIMARY_COLOR,
            alignment=TA_RIGHT,
            spaceAfter=2 * mm,
        ))
        self.styles.add(ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=PRIMARY_COLOR,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ))
        self.styles.add(ParagraphStyle(
            'NormalLeft',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=TEXT_COLOR,
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            'NormalRight',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=TEXT_COLOR,
            alignment=TA_RIGHT,
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            'SmallGray',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=DARK_GRAY,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            'CompanyName',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=PRIMARY_COLOR,
            fontName='Helvetica-Bold',
            leading=20,
        ))
        self.styles.add(ParagraphStyle(
            'TotalLabel',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=TEXT_COLOR,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            'GrandTotal',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=PRIMARY_COLOR,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
        ))

    def generate_invoice(self, order_id):
        """
        Generate a PDF invoice for the given order.
        Returns the relative path to the saved PDF file.
        """
        try:
            order = Order.objects.select_related('user').prefetch_related(
                'items__product'
            ).get(id=order_id)
        except Order.DoesNotExist:
            raise ValueError(f'Order with id {order_id} not found')

        # Get or create Invoice record
        invoice, created = Invoice.objects.get_or_create(
            order=order,
            defaults={
                'invoice_number': Invoice.generate_invoice_number(),
                'total_amount': order.total,
            }
        )

        if not created:
            invoice.total_amount = order.total
            invoice.save(update_fields=['total_amount'])

        # Build PDF
        now = datetime.now()
        year_month = now.strftime('%Y/%m')
        rel_dir = f'invoices/{year_month}'
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        filename = f'invoice_{order.order_number}_{now.strftime("%d-%m-%Y")}.pdf'
        abs_path = os.path.join(abs_dir, filename)
        rel_path = f'{rel_dir}/{filename}'

        # Generate PDF into buffer then write to file
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        elements = []
        self._build_header(elements, invoice, now)
        self._build_client_section(elements, order)
        self._build_order_details(elements, order)
        self._build_items_table(elements, order)
        self._build_totals(elements, order)
        self._build_footer(elements)

        doc.build(elements)

        # Write buffer to file
        with open(abs_path, 'wb') as f:
            f.write(buffer.getvalue())
        buffer.close()

        # Update invoice record
        invoice.pdf_file.name = rel_path
        invoice.save(update_fields=['pdf_file'])

        logger.info(f'Invoice {invoice.invoice_number} generated: {rel_path}')
        return rel_path

    # ─── Header ────────────────────────────────────────────

    def _build_header(self, elements, invoice, now):
        """Build the header section with logo/company + invoice title."""
        avail_width = self.page_width - 2 * self.margin

        # Left column: logo + company info
        left_parts = []
        logo_path = COMPANY_LOGO_PATH
        if logo_path and os.path.isfile(logo_path):
            try:
                img = RLImage(logo_path, width=40 * mm, height=40 * mm)
                img.hAlign = 'LEFT'
                left_parts.append(img)
                left_parts.append(Spacer(1, 2 * mm))
            except Exception:
                pass

        left_parts.append(Paragraph(COMPANY_NAME, self.styles['CompanyName']))
        left_parts.append(Paragraph(COMPANY_ADDRESS, self.styles['NormalLeft']))
        left_parts.append(Paragraph(COMPANY_CITY, self.styles['NormalLeft']))
        left_parts.append(Paragraph(f'Tel: {COMPANY_PHONE}', self.styles['NormalLeft']))
        left_parts.append(Paragraph(f'Email: {COMPANY_EMAIL}', self.styles['NormalLeft']))

        # Right column: FACTURE + number + date
        right_parts = []
        right_parts.append(Paragraph('FACTURE', self.styles['InvoiceTitle']))
        right_parts.append(Paragraph(
            f'<b>#{invoice.invoice_number}</b>',
            self.styles['NormalRight']
        ))
        right_parts.append(Spacer(1, 4 * mm))
        right_parts.append(Paragraph(
            f'Date: {now.strftime("%d/%m/%Y")}',
            self.styles['NormalRight']
        ))

        # Combine into a two-column table
        left_cell = []
        for part in left_parts:
            left_cell.append(part)

        right_cell = []
        for part in right_parts:
            right_cell.append(part)

        header_data = [[left_cell, right_cell]]
        header_table = Table(header_data, colWidths=[avail_width * 0.55, avail_width * 0.45])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))
        elements.append(Spacer(1, 4 * mm))

    # ─── Client Section ────────────────────────────────────

    def _build_client_section(self, elements, order):
        """Build the 'FACTURE A' client info section."""
        elements.append(Paragraph('FACTURE A:', self.styles['SectionTitle']))

        user = order.user
        client_name = user.get_full_name() if hasattr(user, 'get_full_name') else str(user)
        address_parts = [order.delivery_address_line1]
        if order.delivery_address_line2:
            address_parts.append(order.delivery_address_line2)
        if order.delivery_city:
            address_parts.append(order.delivery_city)
        if order.delivery_region:
            address_parts.append(order.delivery_region)
        address = ', '.join(p for p in address_parts if p)

        phone = order.delivery_phone or getattr(user, 'phone_number', '') or ''
        email = getattr(user, 'email', '') or ''

        avail_width = self.page_width - 2 * self.margin

        info_data = [
            [Paragraph(f'<b>{client_name}</b>', self.styles['NormalLeft'])],
            [Paragraph(address, self.styles['NormalLeft'])],
        ]
        if phone:
            info_data.append([Paragraph(f'Telephone: {phone}', self.styles['NormalLeft'])])
        if email:
            info_data.append([Paragraph(f'Email: {email}', self.styles['NormalLeft'])])

        info_table = Table(info_data, colWidths=[avail_width - 6 * mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm),
            ('TOPPADDING', (0, 0), (0, 0), 3 * mm),
            ('BOTTOMPADDING', (-1, -1), (-1, -1), 3 * mm),
            ('LINEBEFOREA', (0, 0), (0, -1), 3, PRIMARY_COLOR),
        ]))
        # Left border workaround: draw a vertical line on left side
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm),
            ('TOPPADDING', (0, 0), (0, 0), 3 * mm),
            ('BOTTOMPADDING', (-1, -1), (-1, -1), 3 * mm),
            ('LINEBEFORE', (0, 0), (0, -1), 3, PRIMARY_COLOR),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))
        elements.append(Spacer(1, 4 * mm))

    # ─── Order Details ─────────────────────────────────────

    def _build_order_details(self, elements, order):
        """Build the order details section."""
        elements.append(Paragraph('DETAILS DE LA COMMANDE', self.styles['SectionTitle']))

        details = [
            ('Numero de commande', f'#{order.order_number}'),
            ('Date de commande', order.created_at.strftime('%d/%m/%Y')),
            ('Statut', _get_status_display(order.status)),
            ('Mode de paiement', _get_payment_display(order.payment_method)),
        ]

        avail_width = self.page_width - 2 * self.margin
        data = []
        for label, value in details:
            data.append([
                Paragraph(f'<b>{label}:</b>', self.styles['NormalLeft']),
                Paragraph(value, self.styles['NormalLeft']),
            ])

        detail_table = Table(data, colWidths=[avail_width * 0.35, avail_width * 0.65])
        detail_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 1 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1 * mm),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))
        elements.append(Spacer(1, 4 * mm))

    # ─── Items Table ───────────────────────────────────────

    def _build_items_table(self, elements, order):
        """Build the articles table with promo support."""
        elements.append(Paragraph('ARTICLES', self.styles['SectionTitle']))

        avail_width = self.page_width - 2 * self.margin
        col_widths = [
            avail_width * 0.42,  # Article
            avail_width * 0.10,  # Qty
            avail_width * 0.24,  # Unit price
            avail_width * 0.24,  # Total
        ]

        # Header row
        header_style = ParagraphStyle(
            'TableHeader', parent=self.styles['Normal'],
            fontSize=10, textColor=colors.white, fontName='Helvetica-Bold',
        )
        header_right = ParagraphStyle(
            'TableHeaderRight', parent=header_style, alignment=TA_RIGHT,
        )
        header_center = ParagraphStyle(
            'TableHeaderCenter', parent=header_style, alignment=TA_CENTER,
        )

        data = [[
            Paragraph('Article', header_style),
            Paragraph('Qte', header_center),
            Paragraph('Prix unit.', header_right),
            Paragraph('Total', header_right),
        ]]

        # Cell styles for content
        cell_left = ParagraphStyle(
            'CellLeft', parent=self.styles['Normal'],
            fontSize=9, textColor=TEXT_COLOR, leading=12,
        )
        cell_center = ParagraphStyle(
            'CellCenter', parent=cell_left, alignment=TA_CENTER,
        )
        cell_right = ParagraphStyle(
            'CellRight', parent=cell_left, alignment=TA_RIGHT,
        )
        cell_promo = ParagraphStyle(
            'CellPromo', parent=cell_left,
            fontSize=8, textColor=SECONDARY_COLOR,
        )
        cell_old_price = ParagraphStyle(
            'CellOldPrice', parent=cell_left,
            fontSize=8, textColor=DARK_GRAY, alignment=TA_RIGHT,
        )

        items = order.items.select_related('product').all()

        for item in items:
            product = item.product
            is_promo = product.is_sale_active() if product else False
            original_price = product.price if product else item.unit_price
            effective_price = item.unit_price

            # Article name
            name_text = product.name if product else f'Produit #{item.product_id}'
            if is_promo and original_price > effective_price:
                discount_pct = round((1 - effective_price / original_price) * 100)
                name_parts = [
                    Paragraph(f'<b>{name_text}</b>', cell_left),
                    Paragraph(f'PROMO -{discount_pct}%', cell_promo),
                ]
            else:
                name_parts = [Paragraph(f'<b>{name_text}</b>', cell_left)]

            # Price column
            if is_promo and original_price > effective_price:
                price_parts = [
                    Paragraph(
                        f'<strike>{_format_price(original_price)}</strike>',
                        cell_old_price
                    ),
                    Paragraph(_format_price(effective_price), cell_right),
                ]
            else:
                price_parts = [Paragraph(_format_price(effective_price), cell_right)]

            data.append([
                name_parts,
                Paragraph(str(item.quantity), cell_center),
                price_parts,
                Paragraph(_format_price(item.total_price), cell_right),
            ])

        table = Table(data, colWidths=col_widths)

        # Build table styles
        style_commands = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
            # Grid
            ('LINEBELOW', (0, 0), (-1, 0), 1, PRIMARY_COLOR),
            ('LINEBELOW', (0, -1), (-1, -1), 1, MEDIUM_GRAY),
        ]

        # Alternating row colors
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))

            # Line between rows
            if i < len(data) - 1:
                style_commands.append(('LINEBELOW', (0, i), (-1, i), 0.5, MEDIUM_GRAY))

        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        elements.append(Spacer(1, 4 * mm))

    # ─── Totals ────────────────────────────────────────────

    def _build_totals(self, elements, order):
        """Build the totals section."""
        avail_width = self.page_width - 2 * self.margin

        # Calculate savings
        savings = 0
        for item in order.items.select_related('product').all():
            product = item.product
            if product and product.is_sale_active() and product.price > item.unit_price:
                savings += (product.price - item.unit_price) * item.quantity

        rows = [
            ('Sous-total:', _format_price(order.subtotal), self.styles['NormalRight'], self.styles['NormalRight']),
            ('Frais de livraison:', _format_price(order.delivery_fee), self.styles['NormalRight'], self.styles['NormalRight']),
        ]

        if savings > 0:
            savings_style = ParagraphStyle(
                'Savings', parent=self.styles['NormalRight'],
                textColor=SECONDARY_COLOR, fontName='Helvetica-Bold',
            )
            rows.append((
                'Economies:',
                f'-{_format_price(savings)}',
                self.styles['NormalRight'],
                savings_style,
            ))

        data = []
        for label, value, label_style, value_style in rows:
            data.append([
                '',  # spacer column
                Paragraph(label, label_style),
                Paragraph(value, value_style),
            ])

        # Grand total row
        data.append([
            '',
            Paragraph('TOTAL TTC:', self.styles['GrandTotal']),
            Paragraph(f'<b>{_format_price(order.total)}</b>', self.styles['GrandTotal']),
        ])

        col_widths = [avail_width * 0.40, avail_width * 0.30, avail_width * 0.30]
        totals_table = Table(data, colWidths=col_widths)
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
            # Total row highlight
            ('LINEABOVE', (1, -1), (-1, -1), 1.5, PRIMARY_COLOR),
            ('BACKGROUND', (1, -1), (-1, -1), LIGHT_GRAY),
            ('TOPPADDING', (0, -1), (-1, -1), 3 * mm),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 3 * mm),
        ]))

        elements.append(totals_table)
        elements.append(Spacer(1, 6 * mm))
        elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))

    # ─── Footer ────────────────────────────────────────────

    def _build_footer(self, elements):
        """Build the thank-you footer."""
        elements.append(Spacer(1, 6 * mm))

        thanks_style = ParagraphStyle(
            'Thanks', parent=self.styles['Normal'],
            fontSize=12, textColor=PRIMARY_COLOR,
            fontName='Helvetica-Bold', alignment=TA_CENTER,
        )
        elements.append(Paragraph('Merci pour votre commande !', thanks_style))
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f'Pour toute question concernant cette facture, '
            f'contactez-nous a: {COMPANY_EMAIL}',
            self.styles['SmallGray']
        ))
