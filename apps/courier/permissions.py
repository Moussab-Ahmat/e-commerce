"""
Custom permissions for courier app.
"""
from rest_framework import permissions


class IsCourierUser(permissions.BasePermission):
    """Permission to allow only courier users."""
    
    def has_permission(self, request, view):
        """Check if user has COURIER role or is a delivery agent."""
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Check if user has COURIER role
        if hasattr(request.user, 'role') and request.user.role == 'COURIER':
            return True
        
        # Check if user is a delivery agent
        if hasattr(request.user, 'delivery_agent'):
            return True
        
        return False
