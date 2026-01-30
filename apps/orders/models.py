"""
Order models: Order and OrderItem.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.validators import validate_xaf_amount
from core.exceptions import InvalidOrderStatusError


class Order(models.Model):
    """Order model with status machine."""
    
    class Status(models.TextChoices):
        PENDING_CONFIRMATION = 'PENDING_CONFIRMATION', 'Pending Confirmation'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PICKING = 'PICKING', 'Picking'
        PACKED = 'PACKED', 'Packed'
        PROCESSING = 'PROCESSING', 'Processing'
        READY_FOR_DELIVERY = 'READY_FOR_DELIVERY', 'Ready for Delivery'
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
        DELIVERED = 'DELIVERED', 'Delivered'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'
    
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    
    # Status machine
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_CONFIRMATION,
        db_index=True
    )
    
    # Pricing (all in integer XAF)
    subtotal = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        default=0,
        help_text='Subtotal in XAF'
    )
    delivery_fee = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        default=0,
        help_text='Delivery fee in XAF'
    )
    total = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        default=0,
        help_text='Total amount in XAF'
    )
    
    # Delivery information
    # Delivery zone (DEPRECATED - use lat/lng instead)
    delivery_zone = models.ForeignKey(
        'delivery.DeliveryZone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text='DEPRECATED: Use latitude/longitude instead'
    )

    # Location-based delivery
    delivery_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Delivery location latitude'
    )
    delivery_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Delivery location longitude'
    )

    # Address fields
    delivery_address_line1 = models.CharField(max_length=255, blank=True)
    delivery_address_line2 = models.CharField(max_length=255, blank=True)
    delivery_city = models.CharField(max_length=100, blank=True)
    delivery_region = models.CharField(max_length=100, blank=True)
    delivery_postal_code = models.CharField(max_length=20, blank=True)
    delivery_phone = models.CharField(max_length=15)
    
    # Payment (COD only for MVP)
    payment_method = models.CharField(max_length=20, default='COD')
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    
    # Idempotency
    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='Idempotency key to prevent duplicate orders'
    )
    
    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Tracking & Delivery Estimation
    courier = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courier_orders',
        limit_choices_to={'role': 'COURIER'},
        help_text='Assigned delivery courier'
    )
    estimated_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated minutes until delivery'
    )
    last_status_update = models.DateTimeField(
        default=timezone.now,
        help_text='Timestamp of last status change'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['idempotency_key']),
        ]
    
    def __str__(self):
        return f'Order {self.order_number}'
    
    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        valid_transitions = {
            self.Status.PENDING_CONFIRMATION: [self.Status.CONFIRMED, self.Status.CANCELLED],
            self.Status.CONFIRMED: [self.Status.PICKING, self.Status.CANCELLED],
            self.Status.PICKING: [self.Status.PACKED, self.Status.CANCELLED],
            self.Status.PACKED: [self.Status.READY_FOR_DELIVERY, self.Status.CANCELLED],
            self.Status.PROCESSING: [self.Status.READY_FOR_DELIVERY, self.Status.CANCELLED],
            self.Status.READY_FOR_DELIVERY: [self.Status.OUT_FOR_DELIVERY, self.Status.CANCELLED],
            self.Status.OUT_FOR_DELIVERY: [self.Status.DELIVERED, self.Status.CANCELLED],
            self.Status.DELIVERED: [self.Status.COMPLETED, self.Status.REFUNDED],
            self.Status.COMPLETED: [],
            self.Status.CANCELLED: [],
            self.Status.REFUNDED: [],
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_status(self, new_status, user=None, estimated_minutes=None):
        """Transition order status with validation."""
        if not self.can_transition_to(new_status):
            raise InvalidOrderStatusError(
                f'Cannot transition from {self.status} to {new_status}'
            )

        old_status = self.status
        self.status = new_status
        self.last_status_update = timezone.now()

        # Update estimated delivery time if provided
        if estimated_minutes is not None:
            self.estimated_minutes = estimated_minutes

        # Update timestamps
        if new_status == self.Status.CONFIRMED:
            self.confirmed_at = timezone.now()
        elif new_status == self.Status.CANCELLED:
            self.cancelled_at = timezone.now()
        elif new_status == self.Status.DELIVERED:
            self.delivered_at = timezone.now()
            self.estimated_minutes = 0  # Order delivered

        update_fields = [
            'status', 'last_status_update', 'estimated_minutes',
            'confirmed_at', 'cancelled_at', 'delivered_at', 'updated_at'
        ]
        self.save(update_fields=update_fields)

        return self

    def assign_courier(self, courier):
        """Assign a courier to the order."""
        if courier.role != 'COURIER':
            raise ValueError('User must have COURIER role')
        self.courier = courier
        self.save(update_fields=['courier', 'updated_at'])
        return self
    
    def calculate_totals(self):
        """Calculate order totals."""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total = self.subtotal + self.delivery_fee
        self.save(update_fields=['subtotal', 'total'])


class OrderItem(models.Model):
    """Order item model."""

    class ItemStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PREPARING = 'PREPARING', 'Preparing'
        READY = 'READY', 'Ready'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    # Multi-vendor: Track which shop this item is from
    shop = models.ForeignKey(
        'vendors.Shop',
        on_delete=models.PROTECT,
        related_name='order_items',
        null=True,
        blank=True,
        help_text='Shop that fulfills this item'
    )

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Price per unit at time of order (XAF)'
    )
    total_price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Total price for this item (XAF)'
    )

    # Multi-vendor: Item-level status for vendor tracking
    item_status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.PENDING,
        db_index=True,
        help_text='Vendor-level status for this item'
    )

    class Meta:
        db_table = 'order_items'
        unique_together = [['order', 'product']]
        indexes = [
            models.Index(fields=['shop', 'item_status']),
            models.Index(fields=['order', 'item_status']),
        ]

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    def save(self, *args, **kwargs):
        """Calculate total price and set shop from product."""
        self.total_price = self.unit_price * self.quantity

        # Auto-set shop from product if not provided
        if not self.shop_id and self.product and hasattr(self.product, 'shop'):
            self.shop = self.product.shop

        super().save(*args, **kwargs)

    def update_status(self, new_status):
        """Update item status."""
        if new_status not in [choice[0] for choice in self.ItemStatus.choices]:
            raise ValueError(f'Invalid status: {new_status}')
        self.item_status = new_status
        self.save(update_fields=['item_status'])
