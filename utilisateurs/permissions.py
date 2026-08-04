"""
Permissions par rôle pour l'API Educ_RDC.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class EstAuthentifie(BasePermission):
    """Accès réservé aux utilisateurs authentifiés."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class EstAdmin(BasePermission):
    """Accès réservé aux administrateurs."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.est_admin or request.user.is_superuser)
        )


class EstNationalOuAdmin(BasePermission):
    """Accès national ou admin."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.est_national
        )


class LecturePourTousEcritureAdmin(BasePermission):
    """Lecture pour tous les authentifiés, écriture pour admin/national."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.est_national or request.user.role in (
            'agent_provincial',
            'agent_antenne',
            'admin',
        )
