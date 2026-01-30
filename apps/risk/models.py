"""
Risk models: Blacklist and CodLimitRule.
"""
from django.db import models
from django.core.validators import RegexValidator
from core.validators import validate_xaf_amount


class Blacklist(models.Model):
    """Phone number blacklist."""
    
    phone_validator = RegexValidator(
        regex=r'^\+235[0-9]{8}$',
        message='Phone number must be in format +235XXXXXXXX (Chad format)'
    )
    
    phone_number = models.CharField(
        max_length=13,
        unique=True,
        validators=[phone_validator],
        db_index=True,
        help_text='Blacklisted phone number'
    )
    reason = models.TextField(help_text='Reason for blacklisting')
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_blacklists'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'blacklists'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.phone_number} - {self.reason[:50]}'


class CodLimitRule(models.Model):
    """COD limit rule per day."""
    
    limit_amount_xaf = models.BigIntegerField(
        validators=[validate_xaf_amount],
        help_text='Maximum COD amount per day in XAF'
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cod_limit_rules'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'COD Limit: {self.limit_amount_xaf} XAF/day'
    
    @classmethod
    def get_active_limit(cls):
        """Get active COD limit rule."""
        return cls.objects.filter(is_active=True).order_by('-created_at').first()
    
    @classmethod
    def get_daily_cod_total(cls, user, date=None):
        """Get total COD amount for user on a given date."""
        from django.utils import timezone
        from apps.orders.models import Order
        
        if date is None:
            date = timezone.now().date()
        
        # Get confirmed orders for the day
        orders = Order.objects.filter(
            user=user,
            status__in=[Order.Status.CONFIRMED, Order.Status.PROCESSING, 
                       Order.Status.READY_FOR_DELIVERY, Order.Status.OUT_FOR_DELIVERY,
                       Order.Status.DELIVERED, Order.Status.COMPLETED],
            payment_method='COD',
            confirmed_at__date=date
        )
        
        return sum(order.total for order in orders)
