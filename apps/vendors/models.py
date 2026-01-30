"""
Vendor and Shop models for multi-vendor marketplace.
"""
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone


class Shop(models.Model):
    """
    Vendor's shop/store.
    Each vendor has ONE shop.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        INACTIVE = 'INACTIVE', 'Inactive'

    # Ownership - OneToOne relationship with User
    vendor = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='shop',
        limit_choices_to={'role': 'VENDOR'},
        help_text='Vendor who owns this shop'
    )

    # Shop Details
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='shops/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='shops/banners/', null=True, blank=True)

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Business Info
    business_license = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    # Status & Performance
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    total_sales = models.BigIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_shops',
        limit_choices_to={'role': 'ADMIN'}
    )

    class Meta:
        db_table = 'shops'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'status']),
            models.Index(fields=['status', 'is_verified']),
            models.Index(fields=['vendor']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def activate(self, admin_user):
        """Activate shop (called by admin)."""
        self.status = self.Status.ACTIVE
        self.is_verified = True
        self.approved_at = timezone.now()
        self.approved_by = admin_user
        self.save(update_fields=['status', 'is_verified', 'approved_at', 'approved_by'])

    def suspend(self):
        """Suspend shop for policy violations."""
        self.status = self.Status.SUSPENDED
        self.save(update_fields=['status'])

    @property
    def products_count(self):
        """Get total number of active products."""
        return self.products.filter(is_active=True).count()

    @property
    def pending_orders_count(self):
        """Get number of pending order items."""
        return self.order_items.filter(item_status='PENDING').count()
