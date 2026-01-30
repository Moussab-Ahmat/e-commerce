"""
Delivery models with status machine.
"""
from django.db import models
from django.core.validators import MinValueValidator
from core.exceptions import InvalidDeliveryStatusError


class DeliveryStatus(models.TextChoices):
    """Delivery status choices with state machine."""
    PENDING = 'PENDING', 'Pending'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    PICKED_UP = 'PICKED_UP', 'Picked Up'
    IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
    DELIVERED = 'DELIVERED', 'Delivered'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RETURNED = 'RETURNED', 'Returned'


class DeliveryAgent(models.Model):
    """Delivery agent model."""
    
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='delivery_agent'
    )
    agent_id = models.CharField(max_length=50, unique=True, db_index=True)
    vehicle_type = models.CharField(
        max_length=50,
        choices=[
            ('MOTORCYCLE', 'Motorcycle'),
            ('CAR', 'Car'),
            ('TRUCK', 'Truck'),
            ('BICYCLE', 'Bicycle'),
        ],
        default='MOTORCYCLE'
    )
    vehicle_number = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    
    # Location tracking (for future GPS integration)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_agents'
        ordering = ['agent_id']
    
    def __str__(self):
        return f'{self.agent_id} - {self.user.get_full_name()}'


class Delivery(models.Model):
    """Delivery model with status machine."""
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    delivery_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Zone and fee (denormalized from order for performance)
    zone = models.ForeignKey(
        'delivery.DeliveryZone',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='deliveries',
        help_text='Delivery zone'
    )
    fee = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Delivery fee in XAF'
    )
    
    # Status machine
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True
    )
    
    # Agent assignment (courier)
    agent = models.ForeignKey(
        DeliveryAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries'
    )
    
    # Delivery details
    estimated_delivery_date = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    
    # Delivery address (denormalized from order for performance)
    delivery_address_line1 = models.CharField(max_length=255)
    delivery_address_line2 = models.CharField(max_length=255, blank=True)
    delivery_city = models.CharField(max_length=100)
    delivery_region = models.CharField(max_length=100)
    delivery_postal_code = models.CharField(max_length=20, blank=True)
    delivery_phone = models.CharField(max_length=15)
    
    # Delivery notes
    delivery_notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)  # If delivery failed
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'deliveries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['delivery_number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['agent', 'status']),
        ]
    
    def __str__(self):
        return f'Delivery {self.delivery_number}'
    
    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        valid_transitions = {
            DeliveryStatus.PENDING: [DeliveryStatus.ASSIGNED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED],
            DeliveryStatus.ASSIGNED: [DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED],
            DeliveryStatus.PICKED_UP: [DeliveryStatus.IN_TRANSIT, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED],
            DeliveryStatus.IN_TRANSIT: [DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.RETURNED],
            DeliveryStatus.DELIVERED: [DeliveryStatus.COMPLETED, DeliveryStatus.FAILED],
            DeliveryStatus.COMPLETED: [],
            DeliveryStatus.FAILED: [DeliveryStatus.ASSIGNED, DeliveryStatus.RETURNED],
            DeliveryStatus.CANCELLED: [],
            DeliveryStatus.RETURNED: [],
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_status(self, new_status, user=None):
        """Transition delivery status with validation."""
        if not self.can_transition_to(new_status):
            raise InvalidDeliveryStatusError(
                f'Cannot transition from {self.status} to {new_status}'
            )
        
        old_status = self.status
        self.status = new_status
        
        # Update timestamps
        from django.utils import timezone
        if new_status == DeliveryStatus.ASSIGNED:
            self.assigned_at = timezone.now()
        elif new_status == DeliveryStatus.PICKED_UP:
            self.picked_up_at = timezone.now()
        elif new_status == DeliveryStatus.DELIVERED:
            self.actual_delivery_date = timezone.now()
        elif new_status == DeliveryStatus.COMPLETED:
            self.completed_at = timezone.now()
        elif new_status == DeliveryStatus.CANCELLED:
            self.cancelled_at = timezone.now()
        
        self.save(update_fields=['status', 'assigned_at', 'picked_up_at', 'actual_delivery_date', 'completed_at', 'cancelled_at', 'updated_at'])
        
        # Log status change
        DeliveryStatusHistory.objects.create(
            delivery=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=user
        )
        
        return self


class DeliveryStatusHistory(models.Model):
    """Track delivery status changes for audit."""
    
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='status_history'
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
        db_table = 'delivery_status_history'
        ordering = ['-created_at']

