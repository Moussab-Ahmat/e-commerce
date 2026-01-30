"""
Tests for accounts app.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import OTPVerification, SMSLog
from apps.accounts.services import OTPService

User = get_user_model()


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user_data():
    """User data fixture."""
    return {
        'phone_number': '+23512345678',
        'password': 'testpass123',
        'first_name': 'Test',
        'last_name': 'User',
        'role': User.Role.CUSTOMER,
    }


@pytest.fixture
def user(user_data):
    """Create a test user."""
    return User.objects.create_user(**user_data)


@pytest.mark.django_db
class TestOTPFlow:
    """Test OTP request and verification flow."""
    
    def test_otp_request_success(self, api_client, user_data):
        """Test successful OTP request."""
        url = '/api/auth/otp/request/'
        response = api_client.post(url, {'phone_number': user_data['phone_number']})
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'expires_in' in response.data
        assert response.data['expires_in'] == OTPService.OTP_EXPIRY_MINUTES * 60
        
        # Check OTP was created
        otp = OTPVerification.objects.filter(phone_number=user_data['phone_number']).first()
        assert otp is not None
        assert otp.is_verified is False
        assert otp.is_used is False
        
        # Check SMS was logged
        sms_log = SMSLog.objects.filter(phone_number=user_data['phone_number']).first()
        assert sms_log is not None
        assert sms_log.status == 'SENT'
        assert sms_log.otp_code == otp.otp_code
    
    def test_otp_request_invalid_phone_format(self, api_client):
        """Test OTP request with invalid phone format."""
        url = '/api/auth/otp/request/'
        response = api_client.post(url, {'phone_number': '12345678'})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_otp_request_rate_limiting(self, api_client, user_data):
        """Test OTP rate limiting."""
        url = '/api/auth/otp/request/'
        phone_number = user_data['phone_number']
        
        # Clear cache
        cache.clear()
        
        # Request OTP multiple times (exceed rate limit)
        for i in range(OTPService.MAX_OTP_PER_HOUR + 1):
            response = api_client.post(url, {'phone_number': phone_number})
        
        # Last request should be rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert 'error' in response.data
    
    def test_otp_verify_success(self, api_client, user_data):
        """Test successful OTP verification."""
        # Request OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user_data['phone_number']})
        
        # Get OTP code
        otp = OTPVerification.objects.filter(phone_number=user_data['phone_number']).first()
        
        # Verify OTP
        verify_url = '/api/auth/otp/verify/'
        response = api_client.post(verify_url, {
            'phone_number': user_data['phone_number'],
            'otp_code': otp.otp_code
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'otp_verification_token' in response.data
        
        # Check OTP is marked as verified
        otp.refresh_from_db()
        assert otp.is_verified is True
    
    def test_otp_verify_invalid_code(self, api_client, user_data):
        """Test OTP verification with invalid code."""
        # Request OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user_data['phone_number']})
        
        # Try to verify with wrong code
        verify_url = '/api/auth/otp/verify/'
        response = api_client.post(verify_url, {
            'phone_number': user_data['phone_number'],
            'otp_code': '000000'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_otp_verify_expired(self, api_client, user_data):
        """Test OTP verification with expired code."""
        # Create expired OTP
        expired_time = timezone.now() - timedelta(minutes=11)
        otp = OTPVerification.objects.create(
            phone_number=user_data['phone_number'],
            otp_code='123456',
            expires_at=expired_time
        )
        
        # Try to verify expired OTP
        verify_url = '/api/auth/otp/verify/'
        response = api_client.post(verify_url, {
            'phone_number': user_data['phone_number'],
            'otp_code': otp.otp_code
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_otp_verify_already_used(self, api_client, user_data):
        """Test OTP verification with already used code."""
        # Request and verify OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user_data['phone_number']})
        
        otp = OTPVerification.objects.filter(phone_number=user_data['phone_number']).first()
        
        verify_url = '/api/auth/otp/verify/'
        api_client.post(verify_url, {
            'phone_number': user_data['phone_number'],
            'otp_code': otp.otp_code
        })
        
        # Try to verify again with same code
        response = api_client.post(verify_url, {
            'phone_number': user_data['phone_number'],
            'otp_code': otp.otp_code
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestJWTAuth:
    """Test JWT authentication flow."""
    
    def test_login_without_otp_verification(self, api_client, user):
        """Test login without OTP verification token fails."""
        url = '/api/auth/login/'
        response = api_client.post(url, {
            'phone_number': user.phone_number,
            'password': 'testpass123',
            'otp_verification_token': 'invalid'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_success(self, api_client, user):
        """Test successful login with OTP verification."""
        # Request and verify OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user.phone_number})
        
        otp = OTPVerification.objects.filter(phone_number=user.phone_number).first()
        
        verify_url = '/api/auth/otp/verify/'
        verify_response = api_client.post(verify_url, {
            'phone_number': user.phone_number,
            'otp_code': otp.otp_code
        })
        otp_verification_token = verify_response.data['otp_verification_token']
        
        # Login with OTP verification token
        login_url = '/api/auth/login/'
        response = api_client.post(login_url, {
            'phone_number': user.phone_number,
            'password': 'testpass123',
            'otp_verification_token': otp_verification_token
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        
        # Check OTP is marked as used
        otp.refresh_from_db()
        assert otp.is_used is True
        
        # Check user is marked as verified
        user.refresh_from_db()
        assert user.is_verified is True
    
    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        # Request and verify OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user.phone_number})
        
        otp = OTPVerification.objects.filter(phone_number=user.phone_number).first()
        
        verify_url = '/api/auth/otp/verify/'
        verify_response = api_client.post(verify_url, {
            'phone_number': user.phone_number,
            'otp_code': otp.otp_code
        })
        otp_verification_token = verify_response.data['otp_verification_token']
        
        # Try login with wrong password
        login_url = '/api/auth/login/'
        response = api_client.post(login_url, {
            'phone_number': user.phone_number,
            'password': 'wrongpassword',
            'otp_verification_token': otp_verification_token
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_expired_otp_token(self, api_client, user):
        """Test login with expired OTP verification token."""
        # Create expired verified OTP
        expired_time = timezone.now() - timedelta(minutes=31)
        otp = OTPVerification.objects.create(
            phone_number=user.phone_number,
            otp_code='123456',
            is_verified=True,
            expires_at=expired_time
        )
        
        # Try login with expired token
        login_url = '/api/auth/login/'
        response = api_client.post(login_url, {
            'phone_number': user.phone_number,
            'password': 'testpass123',
            'otp_verification_token': otp.otp_code
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_token_refresh(self, api_client, user):
        """Test JWT token refresh."""
        # Request and verify OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user.phone_number})
        
        otp = OTPVerification.objects.filter(phone_number=user.phone_number).first()
        
        verify_url = '/api/auth/otp/verify/'
        verify_response = api_client.post(verify_url, {
            'phone_number': user.phone_number,
            'otp_code': otp.otp_code
        })
        otp_verification_token = verify_response.data['otp_verification_token']
        
        # Login to get tokens
        login_url = '/api/auth/login/'
        login_response = api_client.post(login_url, {
            'phone_number': user.phone_number,
            'password': 'testpass123',
            'otp_verification_token': otp_verification_token
        })
        refresh_token = login_response.data['refresh']
        
        # Refresh token
        refresh_url = '/api/auth/token/refresh/'
        response = api_client.post(refresh_url, {'refresh': refresh_token})
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_authenticated_endpoint(self, api_client, user):
        """Test accessing authenticated endpoint."""
        # Request and verify OTP first
        request_url = '/api/auth/otp/request/'
        api_client.post(request_url, {'phone_number': user.phone_number})
        
        otp = OTPVerification.objects.filter(phone_number=user.phone_number).first()
        
        verify_url = '/api/auth/otp/verify/'
        verify_response = api_client.post(verify_url, {
            'phone_number': user.phone_number,
            'otp_code': otp.otp_code
        })
        otp_verification_token = verify_response.data['otp_verification_token']
        
        # Login to get tokens
        login_url = '/api/auth/login/'
        login_response = api_client.post(login_url, {
            'phone_number': user.phone_number,
            'password': 'testpass123',
            'otp_verification_token': otp_verification_token
        })
        access_token = login_response.data['access']
        
        # Access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_url = '/api/auth/profile/'
        response = api_client.get(profile_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['phone_number'] == user.phone_number


@pytest.mark.django_db
class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, user_data):
        """Test user creation."""
        user = User.objects.create_user(**user_data)
        
        assert user.phone_number == user_data['phone_number']
        assert user.check_password(user_data['password'])
        assert user.role == User.Role.CUSTOMER
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_verified is False
    
    def test_create_superuser(self, user_data):
        """Test superuser creation."""
        user = User.objects.create_superuser(
            phone_number=user_data['phone_number'],
            password=user_data['password']
        )
        
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == User.Role.ADMIN
    
    def test_user_roles(self, user_data):
        """Test user roles."""
        for role in User.Role:
            user = User.objects.create_user(
                phone_number=f'+235{role.value}12345',
                password='testpass',
                role=role
            )
            assert user.has_role(role)
    
    def test_phone_number_validation(self):
        """Test phone number validation."""
        with pytest.raises(Exception):  # ValidationError or IntegrityError
            User.objects.create_user(
                phone_number='12345678',  # Invalid format
                password='testpass'
            )


@pytest.mark.django_db
class TestOTPService:
    """Test OTP service methods."""
    
    def test_generate_otp(self):
        """Test OTP generation."""
        otp = OTPService.generate_otp()
        
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_rate_limit_check(self):
        """Test rate limit checking."""
        cache.clear()
        phone_number = '+23512345678'
        
        # Should be allowed initially
        allowed, error = OTPService.check_rate_limit(phone_number)
        assert allowed is True
        assert error is None
        
        # Increment to max
        for _ in range(OTPService.MAX_OTP_PER_HOUR):
            OTPService.increment_rate_limit(phone_number)
        
        # Should be blocked
        allowed, error = OTPService.check_rate_limit(phone_number)
        assert allowed is False
        assert error is not None
    
    def test_create_otp(self, user_data):
        """Test OTP creation."""
        cache.clear()
        phone_number = user_data['phone_number']
        
        otp = OTPService.create_otp(phone_number)
        
        assert otp.phone_number == phone_number
        assert len(otp.otp_code) == 6
        assert otp.is_verified is False
        assert otp.is_used is False
        assert otp.expires_at > timezone.now()
        
        # Check SMS was logged
        sms_log = SMSLog.objects.filter(phone_number=phone_number).first()
        assert sms_log is not None
        assert sms_log.status == 'SENT'
    
    def test_verify_otp(self, user_data):
        """Test OTP verification."""
        cache.clear()
        phone_number = user_data['phone_number']
        
        # Create OTP
        otp = OTPService.create_otp(phone_number)
        
        # Verify OTP
        verified_otp, error = OTPService.verify_otp(phone_number, otp.otp_code)
        
        assert verified_otp is not None
        assert error is None
        assert verified_otp.is_verified is True
        
        # Try to verify again (should fail)
        verified_otp2, error2 = OTPService.verify_otp(phone_number, otp.otp_code)
        assert verified_otp2 is None
        assert error2 is not None

