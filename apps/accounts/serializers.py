"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import User, OTPVerification, CollaborationRequest


class UserSerializer(serializers.ModelSerializer):
    """User serializer."""
    
    class Meta:
        model = User
        fields = (
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'role', 'is_verified', 'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'is_verified', 'date_joined', 'last_login')


class OTPRequestSerializer(serializers.Serializer):
    """OTP request serializer."""
    phone_number = serializers.CharField(max_length=13)
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        from django.core.validators import RegexValidator
        validator = RegexValidator(
            regex=r'^\+235[0-9]{8}$',
            message='Phone number must be in format +235XXXXXXXX (Chad format)'
        )
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                'Phone number must be in format +235XXXXXXXX (Chad format)'
            )
        return value


class OTPVerifySerializer(serializers.Serializer):
    """OTP verification serializer."""
    phone_number = serializers.CharField(max_length=13)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate OTP code."""
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
        # Find valid OTP
        otp = OTPVerification.objects.filter(
            phone_number=phone_number,
            otp_code=otp_code,
            is_verified=False,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            raise serializers.ValidationError({
                'otp_code': 'Invalid or expired OTP code.'
            })
        
        attrs['otp'] = otp
        return attrs


class LoginSerializer(serializers.Serializer):
    """Login serializer requiring OTP verification."""
    phone_number = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True)
    otp_verification_token = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate credentials and OTP verification token."""
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        otp_token = attrs.get('otp_verification_token')
        
        # Authenticate user
        user = authenticate(
            request=self.context.get('request'),
            username=phone_number,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError({
                'phone_number': 'Invalid phone number or password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'phone_number': 'User account is disabled.'
            })
        
        # Verify OTP token
        otp = OTPVerification.objects.filter(
            phone_number=phone_number,
            otp_code=otp_token,
            is_verified=True,
            is_used=False,
            expires_at__gt=timezone.now() - timedelta(minutes=30)  # OTP token valid for 30 min after verification
        ).order_by('-created_at').first()
        
        if not otp:
            raise serializers.ValidationError({
                'otp_verification_token': 'Invalid or expired OTP verification token. Please verify OTP again.'
            })
        
        # Mark OTP token as used
        otp.mark_as_used()
        
        # Mark user as verified if not already
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
        
        attrs['user'] = user
        return attrs


class SimpleLoginSerializer(serializers.Serializer):
    """Simple login with email/phone + password (NO OTP)."""
    identifier = serializers.CharField(help_text='Email or phone number')
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate credentials."""
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        # Try to find user by email or phone
        user = None
        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'identifier': 'Invalid credentials.'
            })

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'identifier': 'Invalid credentials.'
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'identifier': 'User account is disabled.'
            })

        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.Serializer):
    """User registration (NO OTP)."""
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate registration data."""
        email = attrs.get('email', '').strip()
        phone_number = attrs.get('phone_number', '').strip()

        # At least one of email or phone is required
        if not email and not phone_number:
            raise serializers.ValidationError(
                'Either email or phone number is required.'
            )

        # Check if email already exists
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'This email is already registered.'
            })

        # Check if phone already exists
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({
                'phone_number': 'This phone number is already registered.'
            })

        return attrs

    def create(self, validated_data):
        """Create new user."""
        email = validated_data.get('email', '').strip()
        phone_number = validated_data.get('phone_number', '').strip()
        password = validated_data.get('password')
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()

        user = User.objects.create_user(
            phone_number=phone_number if phone_number else None,
            email=email if email else None,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_verified=True  # Auto-verify since no OTP
        )

        return user


class CollaborationRequestSerializer(serializers.ModelSerializer):
    """Serializer for collaboration request submissions."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)

    class Meta:
        model = CollaborationRequest
        fields = (
            'id', 'full_name', 'phone_number', 'email',
            'request_type', 'request_type_display',
            'business_name', 'business_type', 'business_address',
            'business_city', 'business_region',
            'description', 'product_categories', 'estimated_products',
            'status', 'status_display',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')

    def validate_phone_number(self, value):
        """Validate phone number format."""
        import re
        # Allow various phone formats
        if not re.match(r'^[\+]?[0-9]{8,15}$', value.replace(' ', '')):
            raise serializers.ValidationError('Please enter a valid phone number')
        return value
