"""
Services for accounts app.
"""
import random
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.conf import settings
from .models import OTPVerification, SMSLog, User


class OTPService:
    """Service for OTP generation and verification."""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    RATE_LIMIT_MINUTES = 1
    MAX_OTP_PER_HOUR = 5
    
    @classmethod
    def generate_otp(cls):
        """Generate a 6-digit OTP code."""
        return str(random.randint(100000, 999999)).zfill(cls.OTP_LENGTH)
    
    @classmethod
    def check_rate_limit(cls, phone_number):
        """Check if phone number has exceeded rate limit."""
        cache_key = f'otp_rate_limit:{phone_number}'
        count = cache.get(cache_key, 0)
        
        if count >= cls.MAX_OTP_PER_HOUR:
            return False, 'Rate limit exceeded. Please try again later.'
        
        return True, None
    
    @classmethod
    def increment_rate_limit(cls, phone_number):
        """Increment rate limit counter."""
        cache_key = f'otp_rate_limit:{phone_number}'
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, timeout=3600)  # 1 hour
    
    @classmethod
    def create_otp(cls, phone_number):
        """Create and send OTP."""
        # Check rate limit
        allowed, error = cls.check_rate_limit(phone_number)
        if not allowed:
            raise ValueError(error)
        
        # Generate OTP
        otp_code = cls.generate_otp()
        
        # Create OTP record
        expires_at = timezone.now() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
        otp = OTPVerification.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        # Increment rate limit
        cls.increment_rate_limit(phone_number)
        
        # Send SMS (mocked)
        cls.send_sms(phone_number, otp_code)
        
        return otp
    
    @classmethod
    def send_sms(cls, phone_number, otp_code):
        """Mock SMS sending - log to SMSLog table."""
        message = f'Your OTP code is: {otp_code}. Valid for 10 minutes.'
        
        sms_log = SMSLog.objects.create(
            phone_number=phone_number,
            message=message,
            otp_code=otp_code,
            status='SENT'
        )
        sms_log.sent_at = timezone.now()
        sms_log.save(update_fields=['sent_at'])
        
        return sms_log
    
    @classmethod
    def verify_otp(cls, phone_number, otp_code):
        """Verify OTP code."""
        otp = OTPVerification.objects.filter(
            phone_number=phone_number,
            otp_code=otp_code,
            is_verified=False,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            return None, 'Invalid or expired OTP code.'
        
        # Mark as verified
        otp.mark_as_verified()
        
        # Mark user as verified if exists
        try:
            user = User.objects.get(phone_number=phone_number)
            if not user.is_verified:
                user.is_verified = True
                user.save(update_fields=['is_verified'])
        except User.DoesNotExist:
            pass
        
        return otp, None

