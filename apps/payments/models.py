"""
Payment models for COD (Cash on Delivery) transactions.
"""
from django.db import models
from django.core.validators import MinValueValidator
from core.validators import validate_xaf_amount


class Payment(models.Model):
    """Payment model for COD transactions."""
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='payment'
    )
    payment_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Payment details (all in integer XAF)
    amount = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Payment amount in XAF'
    )
    
    # Payment method (COD only for MVP)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('COD', 'Cash on Delivery'),
        ],
        default='COD'
    )
    
    # Payment status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('COLLECTED', 'Collected'),
            ('FAILED', 'Failed'),
            ('REFUNDED', 'Refunded'),
        ],
        default='PENDING',
        db_index=True
    )
    
    # COD specific fields
    collected_by = models.ForeignKey(
        'deliveries.DeliveryAgent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_payments'
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f'Payment {self.payment_number} - {self.amount} XAF'


class PaymentHistory(models.Model):
    """Payment history for audit trail."""
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='history'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_history'
        ordering = ['-created_at']

