"""Courier API permissions."""
from rest_framework import permissions


class IsCourier(permissions.BasePermission):
    """Permission check for courier users."""

    message = 'Access denied. Courier role required.'

    def has_permission(self, request, view):
        """Check if user is authenticated and has COURIER role."""
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'COURIER'
        )
