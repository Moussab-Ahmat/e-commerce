"""
URLs for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationLogViewSet, PushNotificationViewSet, update_fcm_token

router = DefaultRouter()
router.register(r'logs', NotificationLogViewSet, basename='notification-log')
router.register(r'push', PushNotificationViewSet, basename='push-notification')

urlpatterns = [
    path('update-fcm-token/', update_fcm_token, name='update-fcm-token'),
    path('', include(router.urls)),
]
