from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in {'admin', 'manager'})


class IsSecurityOfficer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in {'admin', 'security'})


class IsAdminOrProductManager(BasePermission):
    """Allows product management access to administrators and store managers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in {'admin', 'manager'})


class CanViewSecurityEvents(BasePermission):
    """Allows security officers and admins to view all security events."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in {'admin', 'security'})


class HasAnyRole(BasePermission):
    def has_permission(self, request, view):
        allowed_roles = getattr(view, 'allowed_roles', ())
        return bool(request.user and request.user.is_authenticated and request.user.role in allowed_roles)


class IsAdminRoleOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
