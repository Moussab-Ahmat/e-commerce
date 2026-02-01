from django.contrib import admin
from .models import Invoice, InvoiceSent


class InvoiceSentInline(admin.TabularInline):
    model = InvoiceSent
    extra = 0
    readonly_fields = ['sent_to', 'sent_at', 'status', 'error_message']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'total_amount', 'created_at']
    search_fields = ['invoice_number', 'order__order_number']
    list_filter = ['created_at']
    readonly_fields = ['invoice_number', 'order', 'pdf_file', 'total_amount', 'created_at']
    inlines = [InvoiceSentInline]


@admin.register(InvoiceSent)
class InvoiceSentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'sent_to', 'sent_at', 'status']
    list_filter = ['status', 'sent_at']
    search_fields = ['sent_to', 'invoice__invoice_number']
