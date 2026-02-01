"""
Views for notifications app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes as perm_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import NotificationLog, PushNotification
from .serializers import (
    NotificationLogSerializer,
    PushNotificationSerializer,
    UpdateFcmTokenSerializer,
)


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification log viewset (admin only)."""
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only staff can access."""
        if self.request.user.is_staff:
            return NotificationLog.objects.select_related(
                'order', 'delivery'
            ).order_by('-created_at')
        return NotificationLog.objects.none()


class PushNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Push notification history for the authenticated user."""
    serializer_class = PushNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PushNotification.objects.filter(user=self.request.user)

        # Filter by is_read
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # Filter by notification_type
        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        return queryset

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark a single notification as read."""
        try:
            notification = PushNotification.objects.get(pk=pk, user=request.user)
        except PushNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(PushNotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user."""
        count = PushNotification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response({'marked_read': count})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Return the count of unread notifications."""
        count = PushNotification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return Response({'unread_count': count})


@api_view(['POST'])
@perm_classes([IsAuthenticated])
def update_fcm_token(request):
    """Save or update the user's FCM token."""
    serializer = UpdateFcmTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    token = serializer.validated_data['fcm_token']
    request.user.fcm_token = token if token else None
    request.user.save(update_fields=['fcm_token'])

    return Response({'message': 'FCM token updated successfully'})
