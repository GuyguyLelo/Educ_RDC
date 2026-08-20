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
    """Lecture pour tous les authentifiés, écriture admin national ou admin école."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, 'est_agent_territorial', False):
            return False
        return user.est_national or user.role in ('admin', 'admin_ecole')


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
        if getattr(user, 'est_agent_territorial', False):
            return False
        return bool(
            getattr(user, 'est_enseignant', False)
            or getattr(user, 'est_national', False)
            or user.role in ('admin', 'admin_ecole')
        )


class GestionCartesBiometrie(BasePermission):
    """
    Cartes et biométrie : lecture agents territoriaux (périmètre via queryset),
    écriture réservée à l'administration nationale.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        user = request.user
        if user.est_national:
            return True
        if request.method in SAFE_METHODS:
            return getattr(user, 'est_agent_territorial', False)
        return False


class GestionPaiements(BasePermission):
    """
    Paiements : national CRUD ; admin école CRUD sur son établissement ;
    agents territoriaux lecture seule (périmètre via queryset).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        user = request.user
        if user.est_national:
            return True
        if getattr(user, 'est_agent_territorial', False):
            return request.method in SAFE_METHODS
        if user.role == 'admin_ecole' and user.ecole_id:
            return True
        return False


class GestionClassesEcole(BasePermission):
    """
    Sections / options / classes : lecture pour authentifiés ;
    écriture réservée à l'administration nationale (pas admin_ecole).
    """

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
