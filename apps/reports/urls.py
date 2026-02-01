"""
URL configuration for the reports app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Invoice endpoints
    path(
        'orders/<int:order_id>/generate-invoice/',
        views.generate_invoice,
        name='generate-invoice',
    ),
    path(
        'orders/<int:order_id>/send-invoice/',
        views.send_invoice,
        name='send-invoice',
    ),
    path(
        'orders/<int:order_id>/invoice-history/',
        views.invoice_history,
        name='invoice-history',
    ),

    # Report endpoints
    path('reports/sales/', views.sales_report, name='sales-report'),
    path('reports/deliveries/', views.deliveries_report, name='deliveries-report'),
    path('reports/stock/', views.stock_report, name='stock-report'),
]
