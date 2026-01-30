"""
Views for risk app.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Blacklist, CodLimitRule
from .serializers import BlacklistSerializer, CodLimitRuleSerializer


class BlacklistViewSet(viewsets.ModelViewSet):
    """Blacklist viewset (admin only)."""
    queryset = Blacklist.objects.all()
    serializer_class = BlacklistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only staff can access."""
        if self.request.user.is_staff:
            return Blacklist.objects.all()
        return Blacklist.objects.none()


class CodLimitRuleViewSet(viewsets.ModelViewSet):
    """COD limit rule viewset (admin only)."""
    queryset = CodLimitRule.objects.all()
    serializer_class = CodLimitRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only staff can access."""
        if self.request.user.is_staff:
            return CodLimitRule.objects.all()
        return CodLimitRule.objects.none()
