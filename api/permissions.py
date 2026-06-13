"""
Fichier : permissions.py
Application : api
Description : Permissions DRF basées sur les rôles SMARTOPS.
"""

from rest_framework.permissions import BasePermission


class IsAdminOrManager(BasePermission):
    """Accès réservé aux administrateurs et gestionnaires."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'manager')


class IsAdminOnly(BasePermission):
    """Accès réservé aux administrateurs."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsTechnicianOwner(BasePermission):
    """
    Un technicien ne peut accéder qu'à ses propres tickets.
    Les managers et admins ont un accès complet.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role in ('admin', 'manager'):
            return True
        try:
            return obj.technician == request.user.technician_profile
        except Exception:
            return False
