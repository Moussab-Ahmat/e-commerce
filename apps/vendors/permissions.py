"""
Custom permissions for vendor endpoints.
"""
from rest_framework import permissions


class IsVendor(permissions.BasePermission):
    """
    Allow only users with VENDOR role.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'VENDOR'
        )


class IsVendorOwner(permissions.BasePermission):
    """
    Allow only the vendor who owns the shop/resource.
    Works with Shop, Product, or OrderItem objects.
    """

    def has_object_permission(self, request, view, obj):
        # Check if user is authenticated and is a vendor
        if not (request.user and request.user.is_authenticated and request.user.role == 'VENDOR'):
            return False

        # Handle different object types
        if hasattr(obj, 'vendor'):
            # Shop object
            return obj.vendor == request.user
        elif hasattr(obj, 'shop'):
            # Product or OrderItem - check shop ownership
            return hasattr(request.user, 'shop') and obj.shop == request.user.shop

        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access for all users.
    Write access only for admin users.
    """

    def has_permission(self, request, view):
        # Read permissions allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admin
        return request.user and request.user.is_staff


class IsVendorOrAdmin(permissions.BasePermission):
    """
    Allow access for vendors and admins only.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'VENDOR' or request.user.is_staff)
        )
