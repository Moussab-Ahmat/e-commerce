"""
Views for accounts app.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from .models import User, OTPVerification, CollaborationRequest
from .serializers import (
    UserSerializer, OTPRequestSerializer, OTPVerifySerializer, LoginSerializer,
    CollaborationRequestSerializer, SimpleLoginSerializer, RegisterSerializer
)
from .services import OTPService


class OTPRequestView(generics.GenericAPIView):
    """OTP request endpoint with rate limiting."""
    serializer_class = OTPRequestSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Generate and send OTP."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        
        try:
            otp = OTPService.create_otp(phone_number)
            return Response({
                'message': 'OTP sent successfully',
                'expires_in': OTPService.OTP_EXPIRY_MINUTES * 60,  # seconds
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )


class OTPVerifyView(generics.GenericAPIView):
    """OTP verification endpoint."""
    serializer_class = OTPVerifySerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Verify OTP."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp = serializer.validated_data['otp']
        otp.mark_as_verified()
        
        return Response({
            'message': 'OTP verified successfully',
            'otp_verification_token': otp.otp_code,  # Use OTP code as verification token
            'expires_in': 1800,  # 30 minutes in seconds
        }, status=status.HTTP_200_OK)


class LoginView(generics.GenericAPIView):
    """Login endpoint requiring OTP verification."""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Authenticate user and return JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Return current user."""
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token_view(request):
    """Refresh JWT token endpoint."""
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class CollaborationRequestCreateView(generics.CreateAPIView):
    """Collaboration request submission endpoint (public)."""
    serializer_class = CollaborationRequestSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'message': 'Your collaboration request has been submitted successfully.',
            'request': serializer.data
        }, status=status.HTTP_201_CREATED)


class SimpleLoginView(generics.GenericAPIView):
    """Simple login with email/phone + password (NO OTP)."""
    serializer_class = SimpleLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Authenticate user and return JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class RegisterView(generics.GenericAPIView):
    """User registration (NO OTP)."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Register new user and return JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'message': 'Account created successfully'
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_dev_otp(request):
    """Development endpoint to retrieve OTP code (DEBUG mode only)."""
    from django.conf import settings
    from .models import SMSLog

    if not settings.DEBUG:
        return Response(
            {'error': 'This endpoint is only available in DEBUG mode'},
            status=status.HTTP_403_FORBIDDEN
        )

    phone_number = request.query_params.get('phone_number')
    if not phone_number:
        return Response(
            {'error': 'phone_number parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get the latest OTP for this phone number
    latest_sms = SMSLog.objects.filter(
        phone_number=phone_number
    ).order_by('-created_at').first()

    if not latest_sms:
        return Response(
            {'error': 'No OTP found for this phone number'},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        'phone_number': phone_number,
        'otp_code': latest_sms.otp_code,
        'message': latest_sms.message,
        'created_at': latest_sms.created_at,
        'expires_in_minutes': 10
    }, status=status.HTTP_200_OK)
