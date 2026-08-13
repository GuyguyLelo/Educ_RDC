"""Liaison fiches Personnel ↔ comptes utilisateurs école."""
from __future__ import annotations

from django.core.exceptions import ValidationError

from .models import PersonnelEcole


def lier_personnel_a_utilisateur(personnel: PersonnelEcole, user) -> PersonnelEcole:
    """Attache un compte plateforme à une fiche personnel existante."""
    if not personnel or not user:
        raise ValidationError('Personnel et utilisateur sont requis.')
    if not user.ecole_id or personnel.ecole_id != user.ecole_id:
        raise ValidationError("Le personnel et le compte doivent appartenir à la même école.")
    if personnel.utilisateur_id and personnel.utilisateur_id != user.pk:
        raise ValidationError('Cette fiche personnel a déjà un compte associé.')
    autre = PersonnelEcole.objects.filter(utilisateur_id=user.pk).exclude(pk=personnel.pk).first()
    if autre:
        raise ValidationError('Ce compte est déjà lié à une autre fiche personnel.')

    personnel.utilisateur = user
    # Aligner contacts utiles sans écraser l'identité déjà saisie
    if user.telephone and not personnel.telephone:
        personnel.telephone = user.telephone
    if user.email and not personnel.email:
        personnel.email = user.email
    personnel.actif = bool(user.is_active)
    personnel.save()
    return personnel


def appliquer_identite_personnel_sur_utilisateur(user, personnel: PersonnelEcole):
    """Recopie l'identité de la fiche personnel vers le compte (source de vérité)."""
    if not user or not personnel:
        return user
    user.first_name = (personnel.prenom or '').strip()
    user.last_name = ' '.join(
        p for p in [personnel.nom, personnel.postnom] if (p or '').strip()
    ).strip() or (personnel.nom or '').strip()
    if personnel.email:
        user.email = personnel.email
    if personnel.telephone:
        user.telephone = personnel.telephone
    user.save(update_fields=['first_name', 'last_name', 'email', 'telephone'])
    return user


def synchroniser_personnel_depuis_utilisateur(user) -> PersonnelEcole | None:
    """
    Met à jour la fiche déjà liée (pas de création automatique).
    Flux métier : Personnel d'abord, puis compte.
    """
    if not user or not user.pk:
        return None
    personnel = PersonnelEcole.objects.filter(utilisateur_id=user.pk).first()
    if not personnel:
        return None
    personnel.actif = bool(user.is_active)
    if user.telephone and not personnel.telephone:
        personnel.telephone = user.telephone
    if user.email and not personnel.email:
        personnel.email = user.email
    personnel.save(update_fields=['actif', 'telephone', 'email', 'date_modification'])
    return personnel
