"""
Account models with custom User and OTP verification.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    """Custom user manager supporting email or phone as identifier."""

    def create_user(self, phone_number=None, email=None, password=None, **extra_fields):
        """Create and save a regular user with email OR phone."""
        if not phone_number and not email:
            raise ValueError('Either phone number or email must be set')

        # Use email or phone as the identifier
        if email:
            email = self.normalize_email(email)

        user = self.model(
            phone_number=phone_number,
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number=None, email=None, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number=phone_number, email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model supporting email or phone as identifier."""

    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        VENDOR = 'VENDOR', 'Vendor'
        ADMIN = 'ADMIN', 'Admin'
        WAREHOUSE = 'WAREHOUSE', 'Warehouse'
        COURIER = 'COURIER', 'Courier'

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='Phone number (optional if email provided)'
    )
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        help_text='Email address (optional if phone provided)'
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    # Use email as primary identifier, fallback to phone
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['is_verified']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) | models.Q(phone_number__isnull=False),
                name='user_must_have_email_or_phone'
            )
        ]

    def __str__(self):
        return self.email or self.phone_number or str(self.id)

    def get_identifier(self):
        """Return the user's identifier (email or phone)."""
        return self.email or self.phone_number

    def get_full_name(self):
        """Return full name."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.get_identifier()

    def has_role(self, role):
        """Check if user has specific role."""
        return self.role == role

    def clean(self):
        """Validate that at least email or phone is provided."""
        super().clean()
        if not self.email and not self.phone_number:
            raise ValidationError('Either email or phone number must be provided.')


class OTPVerification(models.Model):
    """OTP verification model."""

    phone_number = models.CharField(max_length=20, db_index=True)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False, db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['phone_number', 'is_verified', 'is_used']),
            models.Index(fields=['phone_number', 'expires_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone_number} - {self.otp_code}'

    def is_valid(self):
        """Check if OTP is valid (not expired, not verified, not used)."""
        return (
            not self.is_verified and
            not self.is_used and
            timezone.now() < self.expires_at
        )

    def mark_as_verified(self):
        """Mark OTP as verified."""
        self.is_verified = True
        self.save(update_fields=['is_verified'])

    def mark_as_used(self):
        """Mark OTP as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])


class SMSLog(models.Model):
    """SMS log for mocking SMS sending."""

    phone_number = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    otp_code = models.CharField(max_length=6, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('SENT', 'Sent'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING',
        db_index=True
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sms_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'SMS to {self.phone_number} - {self.status}'


class CollaborationRequest(models.Model):
    """Collaboration request model for shop owners and partners."""

    class RequestType(models.TextChoices):
        SHOP_OWNER = 'SHOP_OWNER', 'Shop Owner'
        SUPPLIER = 'SUPPLIER', 'Supplier'
        COURIER = 'COURIER', 'Courier'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    # Contact Information
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    # Business Information
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.SHOP_OWNER,
        db_index=True
    )
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100, blank=True)
    business_address = models.TextField()
    business_city = models.CharField(max_length=100)
    business_region = models.CharField(max_length=100)

    # Additional Information
    description = models.TextField(
        blank=True,
        help_text='Description of the business and collaboration interest'
    )
    product_categories = models.TextField(
        blank=True,
        help_text='Product categories (comma separated)'
    )
    estimated_products = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated number of products'
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'collaboration_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['request_type', 'status']),
            models.Index(fields=['phone_number']),
        ]

    def __str__(self):
        return f'{self.business_name} - {self.full_name} ({self.get_status_display()})'

    def approve(self, user):
        """Approve the collaboration request."""
        self.status = self.Status.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

    def reject(self, user, notes=''):
        """Reject the collaboration request."""
        self.status = self.Status.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_notes', 'updated_at'])
