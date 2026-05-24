from rest_framework.permissions import BasePermission
from .models import Admin


class IsSiteAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        site = getattr(request, "current_site", None)
        if not site:
            return False
        return Admin.objects.filter(site=site, user=request.user).exists()


class IsPlatformSuperuser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
