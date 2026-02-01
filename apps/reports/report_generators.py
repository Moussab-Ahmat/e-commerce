"""
Report generators for sales, deliveries, and stock reports.
"""
import os
import logging
from datetime import datetime, timedelta
from io import BytesIO

from django.conf import settings
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)

from apps.orders.models import Order, OrderItem
from apps.catalog.models import Product, Category
from apps.deliveries.models import Delivery, DeliveryAgent, DeliveryStatus

logger = logging.getLogger(__name__)

# Reuse color definitions
COMPANY_NAME = getattr(settings, 'COMPANY_NAME', 'MonEntreprise')
PRIMARY_HEX = getattr(settings, 'INVOICE_PRIMARY_COLOR', '#1976D2')
SECONDARY_HEX = getattr(settings, 'INVOICE_SECONDARY_COLOR', '#4CAF50')


def _hex(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


PRIMARY = _hex(PRIMARY_HEX)
SECONDARY = _hex(SECONDARY_HEX)
TEXT_COLOR = _hex('#333333')
LIGHT_GRAY = _hex('#F5F5F5')
MEDIUM_GRAY = _hex('#E0E0E0')
RED = _hex('#E53935')


def _fmt(amount):
    if amount is None:
        return '0 FCFA'
    return f'{amount:,.0f} FCFA'.replace(',', ' ')


def _save_pdf(buffer, report_type, suffix=''):
    """Save PDF buffer to media/reports/ and return relative path."""
    now = datetime.now()
    rel_dir = f'reports/{now.strftime("%Y/%m")}'
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    filename = f'{report_type}{suffix}_{now.strftime("%d-%m-%Y_%H%M%S")}.pdf'
    abs_path = os.path.join(abs_dir, filename)
    with open(abs_path, 'wb') as f:
        f.write(buffer.getvalue())
    return f'{rel_dir}/{filename}'


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Heading1'],
        fontSize=22, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle', parent=styles['Normal'],
        fontSize=12, textColor=TEXT_COLOR, alignment=TA_CENTER, spaceAfter=6 * mm,
    ))
    styles.add(ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontSize=14, textColor=PRIMARY, spaceBefore=6 * mm, spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        'CellLeft', parent=styles['Normal'], fontSize=9, textColor=TEXT_COLOR,
    ))
    styles.add(ParagraphStyle(
        'CellRight', parent=styles['Normal'], fontSize=9, textColor=TEXT_COLOR, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'CellCenter', parent=styles['Normal'], fontSize=9, textColor=TEXT_COLOR, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'StatLabel', parent=styles['Normal'], fontSize=10, textColor=TEXT_COLOR,
    ))
    styles.add(ParagraphStyle(
        'StatValue', parent=styles['Normal'], fontSize=14, textColor=PRIMARY, fontName='Helvetica-Bold',
    ))
    return styles


def _header_style(styles):
    return ParagraphStyle(
        'TH', parent=styles['Normal'],
        fontSize=9, textColor=colors.white, fontName='Helvetica-Bold',
    )


def _build_report_header(elements, styles, title, start_date, end_date):
    elements.append(Paragraph(COMPANY_NAME, ParagraphStyle(
        'CompTitle', parent=styles['Normal'],
        fontSize=16, textColor=PRIMARY, fontName='Helvetica-Bold', alignment=TA_CENTER,
    )))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(title, styles['ReportTitle']))
    period = f'Du {start_date.strftime("%d/%m/%Y")} au {end_date.strftime("%d/%m/%Y")}'
    elements.append(Paragraph(period, styles['ReportSubtitle']))
    elements.append(Paragraph(
        f'Genere le {datetime.now().strftime("%d/%m/%Y a %H:%M")}',
        styles['ReportSubtitle'],
    ))
    elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))
    elements.append(Spacer(1, 4 * mm))


def _stat_card(label, value):
    """Return a small table cell representing a stat."""
    styles = _base_styles()
    return [
        Paragraph(label, styles['StatLabel']),
        Paragraph(str(value), styles['StatValue']),
    ]


# ═══════════════════════════════════════════════════════
# SALES REPORT
# ═══════════════════════════════════════════════════════

def generate_sales_report(start_date, end_date):
    """
    Generate sales report PDF.
    Returns relative path to saved PDF.
    """
    styles = _base_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    elements = []
    avail = A4[0] - 40 * mm

    _build_report_header(elements, styles, 'Rapport de Ventes', start_date, end_date)

    # Fetch data
    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
    ).exclude(status__in=['CANCELLED', 'REFUNDED'])

    total_revenue = orders.aggregate(t=Sum('total'))['t'] or 0
    total_orders = orders.count()
    avg_basket = int(total_revenue / total_orders) if total_orders > 0 else 0

    # Previous period comparison
    delta = end_date - start_date
    prev_start = start_date - delta
    prev_orders = Order.objects.filter(
        created_at__gte=prev_start, created_at__lt=start_date,
    ).exclude(status__in=['CANCELLED', 'REFUNDED'])
    prev_revenue = prev_orders.aggregate(t=Sum('total'))['t'] or 0
    prev_count = prev_orders.count()

    evo_rev = round(((total_revenue - prev_revenue) / prev_revenue * 100), 1) if prev_revenue > 0 else 0
    evo_count = round(((total_orders - prev_count) / prev_count * 100), 1) if prev_count > 0 else 0

    # Stats section
    elements.append(Paragraph('Statistiques', styles['SectionHead']))
    stats_data = [
        [
            _stat_card('Chiffre d\'affaires', _fmt(total_revenue)),
            _stat_card('Nb commandes', str(total_orders)),
            _stat_card('Panier moyen', _fmt(avg_basket)),
        ],
        [
            _stat_card('Evol. CA', f'{evo_rev:+.1f}%'),
            _stat_card('Evol. commandes', f'{evo_count:+.1f}%'),
            _stat_card('Periode prec.', _fmt(prev_revenue)),
        ],
    ]
    stats_table = Table(stats_data, colWidths=[avail / 3] * 3)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 6 * mm))

    # Top 10 products
    elements.append(Paragraph('Top 10 Produits', styles['SectionHead']))
    th = _header_style(styles)
    top_products = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date,
    ).exclude(order__status__in=['CANCELLED', 'REFUNDED']).values(
        'product__name'
    ).annotate(
        qty=Sum('quantity'), rev=Sum('total_price')
    ).order_by('-qty')[:10]

    tp_data = [[
        Paragraph('#', th),
        Paragraph('Produit', th),
        Paragraph('Quantite', ParagraphStyle('THC', parent=th, alignment=TA_CENTER)),
        Paragraph('Revenus', ParagraphStyle('THR', parent=th, alignment=TA_RIGHT)),
    ]]
    for i, p in enumerate(top_products, 1):
        tp_data.append([
            Paragraph(str(i), styles['CellCenter']),
            Paragraph(p['product__name'] or '-', styles['CellLeft']),
            Paragraph(str(p['qty']), styles['CellCenter']),
            Paragraph(_fmt(p['rev']), styles['CellRight']),
        ])

    tp_table = Table(tp_data, colWidths=[avail * 0.08, avail * 0.47, avail * 0.18, avail * 0.27])
    tp_style = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
    ]
    for i in range(2, len(tp_data), 2):
        tp_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
    tp_table.setStyle(TableStyle(tp_style))
    elements.append(tp_table)
    elements.append(Spacer(1, 6 * mm))

    # Sales by category
    elements.append(Paragraph('Ventes par Categorie', styles['SectionHead']))
    cat_data_qs = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date,
    ).exclude(order__status__in=['CANCELLED', 'REFUNDED']).values(
        cat=F('product__category__name')
    ).annotate(
        rev=Sum('total_price'), qty=Sum('quantity')
    ).order_by('-rev')

    cat_data = [[
        Paragraph('Categorie', th),
        Paragraph('Quantite', ParagraphStyle('THC2', parent=th, alignment=TA_CENTER)),
        Paragraph('Revenus', ParagraphStyle('THR2', parent=th, alignment=TA_RIGHT)),
    ]]
    for c in cat_data_qs:
        cat_data.append([
            Paragraph(c['cat'] or 'Non categorise', styles['CellLeft']),
            Paragraph(str(c['qty']), styles['CellCenter']),
            Paragraph(_fmt(c['rev']), styles['CellRight']),
        ])

    if len(cat_data) > 1:
        cat_table = Table(cat_data, colWidths=[avail * 0.45, avail * 0.25, avail * 0.30])
        cat_style = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ]
        cat_table.setStyle(TableStyle(cat_style))
        elements.append(cat_table)

    doc.build(elements)
    path = _save_pdf(buffer, 'sales_report')
    buffer.close()
    logger.info(f'Sales report generated: {path}')
    return path


# ═══════════════════════════════════════════════════════
# DELIVERIES REPORT
# ═══════════════════════════════════════════════════════

def generate_deliveries_report(start_date, end_date, courier_id=None):
    """
    Generate deliveries report PDF.
    If courier_id is provided, report is scoped to that courier.
    Returns relative path to saved PDF.
    """
    styles = _base_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    elements = []
    avail = A4[0] - 40 * mm

    # Determine title
    courier_name = None
    if courier_id:
        try:
            agent = DeliveryAgent.objects.select_related('user').get(user_id=courier_id)
            courier_name = agent.user.get_full_name()
        except DeliveryAgent.DoesNotExist:
            pass

    title = f'Rapport de {courier_name}' if courier_name else 'Rapport des Livraisons'
    _build_report_header(elements, styles, title, start_date, end_date)

    # Fetch deliveries
    qs = Delivery.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
    )
    if courier_id:
        qs = qs.filter(agent__user_id=courier_id)

    total = qs.count()
    delivered = qs.filter(status=DeliveryStatus.DELIVERED).count()
    completed = qs.filter(status=DeliveryStatus.COMPLETED).count()
    success = delivered + completed
    failed = qs.filter(status=DeliveryStatus.FAILED).count()
    success_rate = round(success / (success + failed) * 100, 1) if (success + failed) > 0 else 0

    # Avg delivery time
    avg_time = 0
    timed = qs.filter(
        status__in=[DeliveryStatus.DELIVERED, DeliveryStatus.COMPLETED],
        completed_at__isnull=False, assigned_at__isnull=False,
    )
    if timed.exists():
        total_min = sum(
            (d.completed_at - d.assigned_at).total_seconds() / 60 for d in timed
        )
        avg_time = int(total_min / timed.count())

    # Stats
    elements.append(Paragraph('Statistiques', styles['SectionHead']))
    stats_data = [
        [
            _stat_card('Total livraisons', str(total)),
            _stat_card('Reussies', str(success)),
            _stat_card('Echouees', str(failed)),
        ],
        [
            _stat_card('Taux de reussite', f'{success_rate}%'),
            _stat_card('Temps moyen', f'{avg_time} min'),
            _stat_card('En cours', str(total - success - failed)),
        ],
    ]
    st = Table(stats_data, colWidths=[avail / 3] * 3)
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 6 * mm))

    # Breakdown by status
    elements.append(Paragraph('Repartition par Statut', styles['SectionHead']))
    th = _header_style(styles)
    status_labels = {
        DeliveryStatus.PENDING: 'En attente',
        DeliveryStatus.ASSIGNED: 'Assignee',
        DeliveryStatus.PICKED_UP: 'Recuperee',
        DeliveryStatus.IN_TRANSIT: 'En cours',
        DeliveryStatus.DELIVERED: 'Livree',
        DeliveryStatus.COMPLETED: 'Completee',
        DeliveryStatus.FAILED: 'Echouee',
        DeliveryStatus.CANCELLED: 'Annulee',
        DeliveryStatus.RETURNED: 'Retournee',
    }

    status_qs = qs.values('status').annotate(cnt=Count('id')).order_by('status')
    s_data = [[
        Paragraph('Statut', th),
        Paragraph('Nombre', ParagraphStyle('THC3', parent=th, alignment=TA_CENTER)),
        Paragraph('Pourcentage', ParagraphStyle('THR3', parent=th, alignment=TA_RIGHT)),
    ]]
    for item in status_qs:
        pct = round(item['cnt'] / total * 100, 1) if total > 0 else 0
        s_data.append([
            Paragraph(status_labels.get(item['status'], item['status']), styles['CellLeft']),
            Paragraph(str(item['cnt']), styles['CellCenter']),
            Paragraph(f'{pct}%', styles['CellRight']),
        ])

    if len(s_data) > 1:
        s_table = Table(s_data, colWidths=[avail * 0.45, avail * 0.25, avail * 0.30])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ]))
        elements.append(s_table)

    # Per-courier breakdown (if global report)
    if not courier_id:
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph('Detail par Livreur', styles['SectionHead']))

        courier_qs = qs.values(
            'agent__user__first_name', 'agent__user__last_name',
        ).annotate(
            cnt=Count('id'),
            done=Count('id', filter=Q(status__in=[DeliveryStatus.DELIVERED, DeliveryStatus.COMPLETED])),
            fail=Count('id', filter=Q(status=DeliveryStatus.FAILED)),
        ).order_by('-cnt')

        c_data = [[
            Paragraph('Livreur', th),
            Paragraph('Total', ParagraphStyle('THC4', parent=th, alignment=TA_CENTER)),
            Paragraph('Reussies', ParagraphStyle('THC5', parent=th, alignment=TA_CENTER)),
            Paragraph('Echouees', ParagraphStyle('THC6', parent=th, alignment=TA_CENTER)),
            Paragraph('Taux', ParagraphStyle('THR4', parent=th, alignment=TA_RIGHT)),
        ]]
        for c in courier_qs:
            name = f"{c['agent__user__first_name'] or ''} {c['agent__user__last_name'] or ''}".strip() or 'N/A'
            rate = round(c['done'] / (c['done'] + c['fail']) * 100, 1) if (c['done'] + c['fail']) > 0 else 0
            c_data.append([
                Paragraph(name, styles['CellLeft']),
                Paragraph(str(c['cnt']), styles['CellCenter']),
                Paragraph(str(c['done']), styles['CellCenter']),
                Paragraph(str(c['fail']), styles['CellCenter']),
                Paragraph(f'{rate}%', styles['CellRight']),
            ])

        if len(c_data) > 1:
            c_table = Table(c_data, colWidths=[avail * 0.30, avail * 0.15, avail * 0.18, avail * 0.18, avail * 0.19])
            c_style = [
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
                ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
            ]
            c_table.setStyle(TableStyle(c_style))
            elements.append(c_table)

    doc.build(elements)
    suffix = f'_courier_{courier_id}' if courier_id else ''
    path = _save_pdf(buffer, 'deliveries_report', suffix)
    buffer.close()
    logger.info(f'Deliveries report generated: {path}')
    return path


# ═══════════════════════════════════════════════════════
# STOCK REPORT
# ═══════════════════════════════════════════════════════

def generate_stock_report():
    """
    Generate stock status report PDF.
    Returns relative path to saved PDF.
    """
    styles = _base_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    elements = []
    avail = A4[0] - 40 * mm
    now = timezone.now()

    # Header
    elements.append(Paragraph(COMPANY_NAME, ParagraphStyle(
        'CompT2', parent=styles['Normal'],
        fontSize=16, textColor=PRIMARY, fontName='Helvetica-Bold', alignment=TA_CENTER,
    )))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph('Etat du Stock', styles['ReportTitle']))
    elements.append(Paragraph(
        f'Genere le {now.strftime("%d/%m/%Y a %H:%M")}',
        styles['ReportSubtitle'],
    ))
    elements.append(HRFlowable(width='100%', thickness=1, color=MEDIUM_GRAY))
    elements.append(Spacer(1, 4 * mm))

    LOW_STOCK_THRESHOLD = 5

    products = Product.objects.filter(
        is_active=True
    ).select_related('category').order_by('category__name', 'name')

    normal = products.filter(stock_quantity__gt=LOW_STOCK_THRESHOLD).count()
    low = products.filter(stock_quantity__gt=0, stock_quantity__lte=LOW_STOCK_THRESHOLD).count()
    out = products.filter(stock_quantity=0).count()
    total_value = sum(p.price * p.stock_quantity for p in products)

    # Summary
    elements.append(Paragraph('Resume', styles['SectionHead']))
    sum_data = [
        [
            _stat_card('Stock normal', str(normal)),
            _stat_card('Stock faible', str(low)),
            _stat_card('Rupture', str(out)),
        ],
        [
            _stat_card('Total produits', str(products.count())),
            _stat_card('Valeur stock', _fmt(total_value)),
            [],
        ],
    ]
    sum_table = Table(sum_data, colWidths=[avail / 3] * 3)
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 6 * mm))

    # Product table
    elements.append(Paragraph('Detail des Produits', styles['SectionHead']))
    th = _header_style(styles)

    p_data = [[
        Paragraph('Produit', th),
        Paragraph('Categorie', th),
        Paragraph('Stock', ParagraphStyle('THC7', parent=th, alignment=TA_CENTER)),
        Paragraph('Seuil', ParagraphStyle('THC8', parent=th, alignment=TA_CENTER)),
        Paragraph('Statut', ParagraphStyle('THC9', parent=th, alignment=TA_CENTER)),
    ]]

    # Status styles
    ok_style = ParagraphStyle('OK', parent=styles['CellCenter'], textColor=SECONDARY, fontName='Helvetica-Bold')
    low_style = ParagraphStyle('Low', parent=styles['CellCenter'], textColor=_hex('#FF9800'), fontName='Helvetica-Bold')
    out_style = ParagraphStyle('Out', parent=styles['CellCenter'], textColor=RED, fontName='Helvetica-Bold')

    for p in products:
        if p.stock_quantity == 0:
            status_p = Paragraph('RUPTURE', out_style)
        elif p.stock_quantity <= LOW_STOCK_THRESHOLD:
            status_p = Paragraph('FAIBLE', low_style)
        else:
            status_p = Paragraph('OK', ok_style)

        p_data.append([
            Paragraph(p.name[:40], styles['CellLeft']),
            Paragraph(p.category.name if p.category else '-', styles['CellLeft']),
            Paragraph(str(p.stock_quantity), styles['CellCenter']),
            Paragraph(str(LOW_STOCK_THRESHOLD), styles['CellCenter']),
            status_p,
        ])

    if len(p_data) > 1:
        p_table = Table(p_data, colWidths=[avail * 0.30, avail * 0.22, avail * 0.14, avail * 0.14, avail * 0.20])
        p_style = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ]
        for i in range(2, len(p_data), 2):
            p_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        p_table.setStyle(TableStyle(p_style))
        elements.append(p_table)

    doc.build(elements)
    path = _save_pdf(buffer, 'stock_report')
    buffer.close()
    logger.info(f'Stock report generated: {path}')
    return path
