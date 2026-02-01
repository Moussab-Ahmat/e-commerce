"""
Serializers for notifications app.
"""
from rest_framework import serializers
from .models import NotificationLog, PushNotification


class NotificationLogSerializer(serializers.ModelSerializer):
    """Notification log serializer."""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    delivery_number = serializers.CharField(source='delivery.delivery_number', read_only=True)

    class Meta:
        model = NotificationLog
        fields = (
            'id', 'recipient_phone', 'notification_type', 'notification_type_display',
            'message', 'status', 'status_display',
            'retry_count', 'max_retries', 'last_retry_at', 'error_message',
            'order', 'order_number', 'delivery', 'delivery_number',
            'created_at', 'sent_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'sent_at', 'updated_at', 'last_retry_at'
        )


class PushNotificationSerializer(serializers.ModelSerializer):
    """Push notification serializer for user-facing notification history."""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    class Meta:
        model = PushNotification
        fields = (
            'id', 'title', 'body', 'data',
            'notification_type', 'notification_type_display',
            'is_read', 'created_at',
        )
        read_only_fields = ('id', 'title', 'body', 'data', 'notification_type', 'created_at')


class UpdateFcmTokenSerializer(serializers.Serializer):
    """Serializer for updating user's FCM token."""
    fcm_token = serializers.CharField(max_length=255, allow_blank=True)
