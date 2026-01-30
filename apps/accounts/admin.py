"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification, SMSLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_verified', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_verified', 'date_joined')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """Admin interface for OTP Verification model."""
    list_display = ('phone_number', 'otp_code', 'is_verified', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'is_used', 'created_at')
    search_fields = ('phone_number', 'otp_code')
    readonly_fields = ('created_at', 'expires_at')
    
    fieldsets = (
        ('OTP Information', {
            'fields': ('phone_number', 'otp_code', 'is_verified', 'is_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    """Admin interface for SMS Log model."""
    list_display = ('phone_number', 'otp_code', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at')
    search_fields = ('phone_number', 'otp_code', 'message')
    readonly_fields = ('created_at', 'sent_at')
    
    fieldsets = (
        ('SMS Information', {
            'fields': ('phone_number', 'message', 'otp_code', 'status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at')
        }),
    )
