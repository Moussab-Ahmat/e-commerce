"""
Custom permissions for Admin API.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission class that allows only users with role='ADMIN'.
    """
    message = 'Access denied. Admin role required.'

    def has_permission(self, request, view):
        """
        Check if user is authenticated and has ADMIN role.
        """
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'ADMIN'
        )


class IsAdminUser(permissions.BasePermission):
    """
    Alias for IsAdmin permission (for clarity in different contexts).
    """
    message = 'Access denied. Admin role required.'

    def has_permission(self, request, view):
        """
        Check if user is authenticated and has ADMIN role.
        """
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'ADMIN'
        )
