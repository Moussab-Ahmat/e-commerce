"""
Invoice and reporting models.
"""
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    """Invoice linked to an order."""

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    invoice_number = models.CharField(max_length=20, unique=True, db_index=True)
    pdf_file = models.FileField(upload_to='invoices/', blank=True)
    total_amount = models.BigIntegerField(default=0, help_text='Total at generation time (XAF)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} - Order {self.order.order_number}'

    @classmethod
    def generate_invoice_number(cls):
        """Generate next invoice number: INV-YYYY-XXXXX."""
        year = timezone.now().year
        prefix = f'INV-{year}-'
        last = cls.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()

        if last:
            last_seq = int(last.invoice_number.split('-')[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1

        return f'{prefix}{next_seq:05d}'


class InvoiceSent(models.Model):
    """History of invoice email sends."""

    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='sends'
    )
    sent_to = models.EmailField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'invoice_sends'
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.invoice.invoice_number} → {self.sent_to} ({self.status})'
