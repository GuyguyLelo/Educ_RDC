"""
Authentification WebAuthn (biométrie appareil : empreinte, Face ID, Windows Hello).
"""
from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from administration.views import journaliser
from .models import CredentialBiometrique

User = get_user_model()

SESSION_REG_CHALLENGE = 'webauthn_reg_challenge'
SESSION_AUTH_CHALLENGE = 'webauthn_auth_challenge'


def _rp_id(request) -> str:
    configured = getattr(settings, 'WEBAUTHN_RP_ID', '') or ''
    if configured:
        return configured
    return request.get_host().split(':')[0]


def _origin(request) -> str:
    configured = getattr(settings, 'WEBAUTHN_ORIGIN', '') or ''
    if configured:
        return configured
    scheme = 'https' if request.is_secure() else 'http'
    return f'{scheme}://{request.get_host()}'


def _rp_name() -> str:
    return getattr(settings, 'WEBAUTHN_RP_NAME', 'Educ_RDC')


def _erreur_contexte_webauthn(request) -> str | None:
    """
    WebAuthn n’est autorisé que en HTTPS, ou en HTTP sur localhost / 127.0.0.1.
    Sinon le navigateur lève « The operation is insecure ».
    """
    host = (request.get_host() or '').split(':')[0].lower().strip('[]')
    if request.is_secure():
        return None
    if host in {'localhost', '127.0.0.1', '::1'}:
        return None
    return (
        'Biométrie impossible ici : le navigateur exige un contexte sécurisé. '
        'Ouvrez l’application via http://localhost ou http://127.0.0.1 '
        '(ou en HTTPS en production), pas via une IP / nom de machine du réseau.'
    )


def _json_body(request) -> dict[str, Any]:
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return {}


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'ok': False, 'detail': message}, status=status)


@ensure_csrf_cookie
@require_http_methods(['GET'])
def webauthn_status(request):
    """Indique si l’utilisateur courant a des credentials (profil)."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'ok': True,
            'autorise': False,
            'enroles': 0,
            'credentials': [],
        })
    autorise = bool(getattr(request.user, 'connexion_biometrique', False))
    creds = list(
        request.user.credentials_biometriques.values(
            'id', 'nom_appareil', 'date_creation', 'date_dernier_usage',
        )
    )
    for c in creds:
        if c.get('date_creation'):
            c['date_creation'] = c['date_creation'].isoformat()
        if c.get('date_dernier_usage'):
            c['date_dernier_usage'] = c['date_dernier_usage'].isoformat()
    return JsonResponse({
        'ok': True,
        'autorise': autorise,
        'enroles': len(creds),
        'credentials': creds,
    })


@require_http_methods(['POST'])
def webauthn_register_begin(request):
    if not request.user.is_authenticated:
        return _json_error('Connexion requise pour enregistrer la biométrie.', 401)
    err_ctx = _erreur_contexte_webauthn(request)
    if err_ctx:
        return _json_error(err_ctx, 403)
    if not getattr(request.user, 'connexion_biometrique', False):
        return _json_error(
            'La connexion biométrique n’est pas autorisée pour ce compte. '
            'Contactez un administrateur.',
            403,
        )

    existing = list(
        CredentialBiometrique.objects.filter(utilisateur=request.user).values_list(
            'credential_id', flat=True,
        )
    )
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid))
        for cid in existing
    ]
    options = generate_registration_options(
        rp_id=_rp_id(request),
        rp_name=_rp_name(),
        user_id=str(request.user.pk).encode('utf-8'),
        user_name=request.user.username,
        user_display_name=request.user.get_full_name() or request.user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    request.session[SESSION_REG_CHALLENGE] = bytes_to_base64url(options.challenge)
    request.session.modified = True
    return JsonResponse({'ok': True, 'options': json.loads(options_to_json(options))})


@require_http_methods(['POST'])
def webauthn_register_complete(request):
    if not request.user.is_authenticated:
        return _json_error('Connexion requise.', 401)
    if not getattr(request.user, 'connexion_biometrique', False):
        return _json_error(
            'La connexion biométrique n’est pas autorisée pour ce compte.',
            403,
        )
    challenge = request.session.get(SESSION_REG_CHALLENGE)
    if not challenge:
        return _json_error('Challenge d’enregistrement expiré. Réessayez.')

    body = _json_body(request)
    credential = body.get('credential')
    nom = (body.get('nom_appareil') or 'Appareil biométrique').strip()[:120]
    if not credential:
        return _json_error('Réponse biométrique manquante.')

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
        )
    except Exception as exc:
        return _json_error(f'Échec de l’enregistrement biométrique : {exc}')

    cid = bytes_to_base64url(verification.credential_id)
    CredentialBiometrique.objects.update_or_create(
        credential_id=cid,
        defaults={
            'utilisateur': request.user,
            'public_key': verification.credential_public_key,
            'sign_count': verification.sign_count,
            'transports': body.get('transports') or [],
            'nom_appareil': nom or 'Appareil biométrique',
        },
    )
    request.session.pop(SESSION_REG_CHALLENGE, None)
    journaliser(
        request.user,
        'Enregistrement biométrique',
        nom,
        request=request,
    )
    return JsonResponse({'ok': True, 'detail': 'Biométrie enregistrée. Vous pourrez vous connecter sans mot de passe.'})


@ensure_csrf_cookie
@require_http_methods(['POST'])
def webauthn_login_begin(request):
    err_ctx = _erreur_contexte_webauthn(request)
    if err_ctx:
        return _json_error(err_ctx, 403)
    body = _json_body(request)
    username = (body.get('username') or '').strip()
    allow = []
    if username:
        user = User.objects.filter(username__iexact=username, is_active=True).first()
        if not user:
            return _json_error('Aucun compte trouvé pour cet identifiant.', 404)
        if not getattr(user, 'connexion_biometrique', False):
            return _json_error(
                'La connexion biométrique n’est pas autorisée pour ce compte.',
                403,
            )
        creds = CredentialBiometrique.objects.filter(utilisateur=user)
        if not creds.exists():
            return _json_error(
                'Aucune biométrie enregistrée pour ce compte. '
                'Connectez-vous par mot de passe puis activez-la dans Mon profil.',
                404,
            )
        allow = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in creds
        ]
    else:
        # Découverte (clés résidentes) — tous les appareils connus côté serveur
        # optionnel : laisser allow vide pour usernameless
        pass

    options = generate_authentication_options(
        rp_id=_rp_id(request),
        allow_credentials=allow or None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    request.session[SESSION_AUTH_CHALLENGE] = bytes_to_base64url(options.challenge)
    request.session.modified = True
    return JsonResponse({'ok': True, 'options': json.loads(options_to_json(options))})


@require_http_methods(['POST'])
def webauthn_login_complete(request):
    from administration.acces_exterieur import (
        a_autorisation_valide,
        analyser_localisation_requete,
        creer_ou_rafraichir_demande,
    )

    challenge = request.session.get(SESSION_AUTH_CHALLENGE)
    if not challenge:
        return _json_error('Challenge de connexion expiré. Réessayez.')

    body = _json_body(request)
    credential = body.get('credential')
    if not credential:
        return _json_error('Réponse biométrique manquante.')

    raw_id = credential.get('rawId') or credential.get('id')
    if not raw_id:
        return _json_error('Identifiant biométrique manquant.')

    try:
        stored = CredentialBiometrique.objects.select_related('utilisateur').get(
            credential_id=raw_id if isinstance(raw_id, str) else bytes_to_base64url(raw_id),
        )
    except CredentialBiometrique.DoesNotExist:
        # rawId parfois déjà base64url
        try:
            cid = bytes_to_base64url(base64url_to_bytes(raw_id)) if isinstance(raw_id, str) else bytes_to_base64url(raw_id)
            stored = CredentialBiometrique.objects.select_related('utilisateur').get(credential_id=cid)
        except Exception:
            return _json_error('Appareil biométrique non reconnu.', 404)

    user = stored.utilisateur
    if not user.is_active:
        return _json_error('Compte désactivé.', 403)
    if not getattr(user, 'connexion_biometrique', False):
        return _json_error(
            'La connexion biométrique n’est pas autorisée pour ce compte.',
            403,
        )

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            credential_public_key=bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
        )
    except Exception as exc:
        return _json_error(f'Échec de la vérification biométrique : {exc}')

    stored.sign_count = verification.new_sign_count
    stored.date_dernier_usage = timezone.now()
    stored.save(update_fields=['sign_count', 'date_dernier_usage'])
    request.session.pop(SESSION_AUTH_CHALLENGE, None)

    ip, geo, hors = analyser_localisation_requete(request)
    if hors and not a_autorisation_valide(user, ip):
        demande = creer_ou_rafraichir_demande(user, ip, geo)
        journaliser(
            user,
            'Connexion biométrique hors RDC refusée',
            f'IP {ip} — demande #{demande.pk}',
            request=request,
        )
        return _json_error(
            'Connexion hors RDC : une autorisation administrateur est requise.',
            403,
        )

    login(request, user)
    request.session['_presence_ip'] = ip
    request.session['_presence_geo'] = geo
    request.session.modified = True
    journaliser(
        user,
        'Connexion biométrique',
        f'IP {ip} — {stored.nom_appareil}',
        request=request,
    )
    return JsonResponse({
        'ok': True,
        'detail': f'Bienvenue, {user.get_full_name() or user.username} !',
        'redirect': '/dashboard/',
    })


@require_http_methods(['POST'])
def webauthn_delete(request):
    if not request.user.is_authenticated:
        return _json_error('Connexion requise.', 401)
    body = _json_body(request)
    cred_id = body.get('id')
    if not cred_id:
        return _json_error('Identifiant requis.')
    deleted, _ = CredentialBiometrique.objects.filter(
        utilisateur=request.user, pk=cred_id,
    ).delete()
    if not deleted:
        return _json_error('Identifiant introuvable.', 404)
    journaliser(request.user, 'Suppression biométrie', f'#{cred_id}', request=request)
    return JsonResponse({'ok': True, 'detail': 'Identifiant biométrique retiré.'})
