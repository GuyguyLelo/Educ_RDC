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
    """Lecture pour tous les authentifiés, écriture pour rôles opérationnels."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        # Enseignant : lecture seule (élèves de sa classe ; pas de cartes)
        return request.user.est_national or request.user.role in (
            'agent_province_admin',
            'agent_provincial',
            'agent_antenne',
            'admin',
            'admin_ecole',
        )


class EcriturePhotoEleve(BasePermission):
    """
    Autorise le changement de photo élève pour les rôles opérationnels
    et l'enseignant (limité à sa classe via le queryset).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            getattr(user, 'est_enseignant', False)
            or getattr(user, 'est_national', False)
            or user.role in (
                'agent_province_admin',
                'agent_provincial',
                'admin',
                'admin_ecole',
            )
        )


class GestionClassesEcole(BasePermission):
    """Lecture pour authentifiés ; écriture réservée à l'administration nationale."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return bool(getattr(request.user, 'est_national', False))


class GestionUtilisateurs(BasePermission):
    """
    Admin national : CRUD global.
    Administratif école : CRUD des comptes de son école (admin_ecole / enseignant).
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.est_admin or user.is_superuser:
            return True
        return user.role == 'admin_ecole' and bool(user.ecole_id)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.est_admin or user.is_superuser:
            return True
        if user.role != 'admin_ecole' or not user.ecole_id:
            return False
        return (
            obj.ecole_id == user.ecole_id
            and obj.role in ('admin_ecole', 'enseignant')
        )
