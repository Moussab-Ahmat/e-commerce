"""
Notification models.
"""
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone


class NotificationType(models.TextChoices):
    """Notification type choices."""
    ORDER_CONFIRMATION = 'ORDER_CONFIRMATION', 'Order Confirmation'
    ORDER_REMINDER = 'ORDER_REMINDER', 'Order Reminder'
    ORDER_DELIVERED = 'ORDER_DELIVERED', 'Order Delivered'
    ORDER_FAILED = 'ORDER_FAILED', 'Order Failed'
    DELIVERY_ASSIGNED = 'DELIVERY_ASSIGNED', 'Delivery Assigned'
    DELIVERY_IN_TRANSIT = 'DELIVERY_IN_TRANSIT', 'Delivery In Transit'


class PushNotificationType(models.TextChoices):
    """Push notification type choices for clients and couriers."""
    # Client notifications
    ORDER_CONFIRMED = 'order_confirmed', 'Commande confirmee'
    COURIER_ASSIGNED = 'courier_assigned', 'Livreur assigne'
    ORDER_PICKED_UP = 'order_picked_up', 'Commande recuperee'
    ORDER_ON_THE_WAY = 'order_on_the_way', 'Livreur en route'
    ORDER_DELIVERED = 'order_delivered', 'Commande livree'
    ORDER_CANCELLED = 'order_cancelled', 'Commande annulee'
    PROMOTION = 'promotion', 'Promotion'
    BACK_IN_STOCK = 'back_in_stock', 'Retour en stock'
    # Courier notifications
    DELIVERY_ASSIGNED = 'delivery_assigned', 'Livraison assignee'
    DELIVERY_CANCELLED = 'delivery_cancelled', 'Livraison annulee'
    ADDRESS_CHANGED = 'address_changed', 'Adresse modifiee'
    DAILY_REMINDER = 'daily_reminder', 'Rappel quotidien'


class PushNotification(models.Model):
    """
    Push notification history model.
    Stores all push notifications sent to users (clients and couriers).
    Data is stored in PostgreSQL, NOT in Firebase.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_notifications',
        db_index=True
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(null=True, blank=True, help_text='Extra data payload')
    notification_type = models.CharField(
        max_length=30,
        choices=PushNotificationType.choices,
        db_index=True
    )
    is_read = models.BooleanField(default=False, db_index=True)
    is_sent = models.BooleanField(default=False, help_text='Whether FCM send succeeded')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'push_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.notification_type} -> {self.user} ({self.created_at:%Y-%m-%d %H:%M})'


class NotificationStatus(models.TextChoices):
    """Notification status choices."""
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'
    RETRYING = 'RETRYING', 'Retrying'


class NotificationLog(models.Model):
    """Notification log model."""
    
    phone_validator = RegexValidator(
        regex=r'^\+235[0-9]{8}$',
        message='Phone number must be in format +235XXXXXXXX (Chad format)'
    )
    
    # Recipient
    recipient_phone = models.CharField(
        max_length=13,
        validators=[phone_validator],
        db_index=True,
        help_text='Recipient phone number'
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True
    )
    message = models.TextField(help_text='Notification message')
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True
    )
    
    # Retry tracking
    retry_count = models.IntegerField(default=0, help_text='Number of retry attempts')
    max_retries = models.IntegerField(default=3, help_text='Maximum retry attempts')
    last_retry_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, help_text='Last error message')
    
    # Related objects (optional, for context)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    delivery = models.ForeignKey(
        'deliveries.Delivery',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_phone', 'status']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f'{self.notification_type} to {self.recipient_phone} ({self.status})'
    
    def can_retry(self):
        """Check if notification can be retried."""
        return (
            self.status in [NotificationStatus.PENDING, NotificationStatus.FAILED, NotificationStatus.RETRYING] and
            self.retry_count < self.max_retries
        )
    
    def mark_retrying(self):
        """Mark notification as retrying."""
        self.status = NotificationStatus.RETRYING
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['status', 'retry_count', 'last_retry_at', 'updated_at'])
    
    def mark_sent(self):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_failed(self, error_message=''):
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])
