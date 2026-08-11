"""
Contrôle des connexions hors République démocratique du Congo.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from .geoip import geolocaliser_ip, ip_privee_ou_locale
from .models import AutorisationAccesExterieur
from .monitoring import client_ip


def est_hors_rdc(geo: dict[str, Any] | None, ip: str) -> bool:
    """True si connexion clairement hors RDC. IP locale/privée = autorisée."""
    if ip_privee_ou_locale(ip):
        return False
    geo = geo or {}
    code = (geo.get('country_code') or '').strip().upper()
    if not code:
        return False
    return code != 'CD'


def analyser_localisation_requete(request) -> tuple[str, dict[str, Any], bool]:
    ip = client_ip(request)
    geo = geolocaliser_ip(ip)
    return ip, geo, est_hors_rdc(geo, ip)


def a_autorisation_valide(utilisateur, ip: str) -> bool:
    if not utilisateur or not getattr(utilisateur, 'is_authenticated', False):
        return False
    if getattr(utilisateur, 'est_admin', False) or getattr(utilisateur, 'is_superuser', False):
        return True
    now = timezone.now()
    return AutorisationAccesExterieur.objects.filter(
        utilisateur=utilisateur,
        statut=AutorisationAccesExterieur.Statut.AUTORISE,
    ).filter(
        Q(date_expiration__isnull=True) | Q(date_expiration__gt=now)
    ).filter(
        Q(adresse_ip=ip) | Q(adresse_ip='0.0.0.0')
    ).exists()


def creer_ou_rafraichir_demande(utilisateur, ip: str, geo: dict[str, Any]) -> AutorisationAccesExterieur:
    recente = AutorisationAccesExterieur.objects.filter(
        utilisateur=utilisateur,
        adresse_ip=ip,
        statut=AutorisationAccesExterieur.Statut.EN_ATTENTE,
        date_demande__gte=timezone.now() - timedelta(hours=24),
    ).first()
    if recente:
        recente.geo_label = geo.get('label') or recente.geo_label
        recente.country_code = geo.get('country_code') or recente.country_code
        recente.save(update_fields=['geo_label', 'country_code'])
        return recente
    return AutorisationAccesExterieur.objects.create(
        utilisateur=utilisateur,
        adresse_ip=ip or '0.0.0.0',
        geo_label=(geo.get('label') or '')[:255],
        country_code=(geo.get('country_code') or '')[:8],
        statut=AutorisationAccesExterieur.Statut.EN_ATTENTE,
    )


def autoriser_demande(
    demande: AutorisationAccesExterieur,
    admin,
    *,
    jours: int = 7,
    toutes_ip: bool = False,
    motif: str = '',
) -> AutorisationAccesExterieur:
    demande.statut = AutorisationAccesExterieur.Statut.AUTORISE
    demande.decide_par = admin
    demande.date_decision = timezone.now()
    demande.date_expiration = timezone.now() + timedelta(days=max(1, int(jours or 7)))
    if toutes_ip:
        demande.adresse_ip = '0.0.0.0'
        demande.motif = (motif or 'Autorisation toutes IP').strip()[:255]
    else:
        demande.motif = (motif or '').strip()[:255]
    demande.save()
    AutorisationAccesExterieur.objects.filter(
        utilisateur=demande.utilisateur,
        adresse_ip=demande.adresse_ip,
        statut=AutorisationAccesExterieur.Statut.EN_ATTENTE,
    ).exclude(pk=demande.pk).update(
        statut=AutorisationAccesExterieur.Statut.REFUSE,
        decide_par=admin,
        date_decision=timezone.now(),
        motif='Clos automatiquement après autorisation',
    )
    return demande


def refuser_demande(demande: AutorisationAccesExterieur, admin, motif: str = '') -> AutorisationAccesExterieur:
    demande.statut = AutorisationAccesExterieur.Statut.REFUSE
    demande.decide_par = admin
    demande.date_decision = timezone.now()
    demande.date_expiration = None
    demande.motif = (motif or 'Refusé par administrateur').strip()[:255]
    demande.save()
    return demande


def revoquer_demande(demande: AutorisationAccesExterieur, admin, motif: str = '') -> AutorisationAccesExterieur:
    demande.statut = AutorisationAccesExterieur.Statut.REVOQUE
    demande.decide_par = admin
    demande.date_decision = timezone.now()
    demande.motif = (motif or 'Révoqué par administrateur').strip()[:255]
    demande.save()
    return demande


def serialiser_autorisation(obj: AutorisationAccesExterieur) -> dict:
    u = obj.utilisateur
    return {
        'id': obj.pk,
        'user_id': u.pk if u else None,
        'username': u.username if u else '',
        'nom_complet': (u.get_full_name() or u.username) if u else '',
        'role': getattr(u, 'role', '') if u else '',
        'role_display': u.get_role_display() if u else '',
        'adresse_ip': obj.adresse_ip,
        'toutes_ip': obj.adresse_ip == '0.0.0.0',
        'geo_label': obj.geo_label,
        'country_code': obj.country_code,
        'statut': obj.statut,
        'statut_display': obj.get_statut_display(),
        'date_demande': obj.date_demande.isoformat() if obj.date_demande else None,
        'date_decision': obj.date_decision.isoformat() if obj.date_decision else None,
        'date_expiration': obj.date_expiration.isoformat() if obj.date_expiration else None,
        'decide_par': obj.decide_par.get_username() if obj.decide_par_id else '',
        'motif': obj.motif,
        'est_valide': obj.est_valide,
    }
