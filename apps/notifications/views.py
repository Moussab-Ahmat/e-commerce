"""
Views for notifications app.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import NotificationLog
from .serializers import NotificationLogSerializer


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
