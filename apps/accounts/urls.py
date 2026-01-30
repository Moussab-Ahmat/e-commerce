"""
URLs for accounts app.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    OTPRequestView, OTPVerifyView, LoginView,
    UserProfileView, refresh_token_view, CollaborationRequestCreateView,
    get_dev_otp, SimpleLoginView, RegisterView
)

urlpatterns = [
    # Simple auth (NO OTP)
    path('simple-login/', SimpleLoginView.as_view(), name='simple-login'),
    path('register/', RegisterView.as_view(), name='register'),

    # OTP-based auth (legacy)
    path('otp/request/', OTPRequestView.as_view(), name='otp-request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('otp/dev/', get_dev_otp, name='dev-otp'),  # Development only
    path('login/', LoginView.as_view(), name='login'),

    # Common
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('collaboration/request/', CollaborationRequestCreateView.as_view(), name='collaboration-request'),
]
