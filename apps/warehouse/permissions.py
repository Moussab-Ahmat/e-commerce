"""
Custom permissions for warehouse app.
"""
from rest_framework import permissions


class IsWarehouseUser(permissions.BasePermission):
    """Permission to allow only warehouse users."""
    
    def has_permission(self, request, view):
        """Check if user has WAREHOUSE role."""
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'WAREHOUSE'
        )
