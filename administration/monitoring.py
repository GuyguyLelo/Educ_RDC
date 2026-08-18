"""
Suivi de présence des utilisateurs connectés (sessions Django).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# Considéré « en ligne » si activité récente
SEUIL_EN_LIGNE = timedelta(minutes=15)


def client_ip(request) -> str:
    if not request:
        return ''
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


def enregistrer_presence(request) -> None:
    """Met à jour les métadonnées de présence dans la session (throttlé ~60 s)."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return
    session = getattr(request, 'session', None)
    if session is None:
        return

    now = timezone.now()
    last_raw = session.get('_presence_at')
    last = parse_datetime(last_raw) if last_raw else None
    if last and timezone.is_naive(last):
        last = timezone.make_aware(last, timezone.get_current_timezone())
    if last and (now - last) < timedelta(seconds=60):
        return

    from .geoip import geolocaliser_ip, normaliser_geo

    ip = client_ip(request)
    session['_presence_at'] = now.isoformat()
    session['_presence_ip'] = ip
    ua = request.META.get('HTTP_USER_AGENT') or ''
    session['_presence_ua'] = ua[:220]
    session['_presence_username'] = request.user.get_username()

    # Conserver une géoloc navigateur plus précise si déjà présente
    geo_existante = normaliser_geo(session.get('_presence_geo'))
    if geo_existante.get('source') == 'browser' and geo_existante.get('lat') is not None:
        pass
    else:
        session['_presence_geo'] = geolocaliser_ip(ip)
    session.modified = True


def _parse_presence_at(raw: Any):
    if not raw:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        dt = parse_datetime(str(raw))
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def lister_sessions_actives(*, seuil_en_ligne: timedelta = SEUIL_EN_LIGNE) -> list[dict]:
    """Liste les sessions non expirées avec utilisateur authentifié."""
    User = get_user_model()
    now = timezone.now()
    sessions = Session.objects.filter(expire_date__gte=now).order_by('-expire_date')

    user_ids: set[int] = set()
    decoded_rows: list[tuple[Session, dict]] = []
    for sess in sessions:
        try:
            data = sess.get_decoded()
        except Exception:
            continue
        uid = data.get('_auth_user_id')
        if not uid:
            continue
        try:
            user_ids.add(int(uid))
        except (TypeError, ValueError):
            continue
        decoded_rows.append((sess, data))

    users = {
        u.pk: u
        for u in User.objects.filter(pk__in=user_ids).select_related(
            'ecole', 'province_educationnelle', 'antenne', 'classe',
        )
    }

    result: list[dict] = []
    for sess, data in decoded_rows:
        try:
            uid = int(data.get('_auth_user_id'))
        except (TypeError, ValueError):
            continue
        user = users.get(uid)
        if not user:
            continue

        presence_at = _parse_presence_at(data.get('_presence_at'))
        en_ligne = bool(presence_at and (now - presence_at) <= seuil_en_ligne)

        rattachement = (
            getattr(user.ecole, 'nom', None)
            or getattr(user.antenne, 'nom', None)
            or getattr(user.province_educationnelle, 'nom', None)
            or '—'
        )

        from .geoip import geolocaliser_ip, normaliser_geo

        ip = data.get('_presence_ip') or ''
        geo = normaliser_geo(data.get('_presence_geo'))
        if (not geo.get('label') or geo.get('label') == '—' or geo.get('source') == 'none') and ip:
            geo = geolocaliser_ip(ip)

        result.append({
            'session_key': sess.session_key,
            'user_id': user.pk,
            'username': user.username,
            'nom_complet': user.get_full_name() or user.username,
            'role': user.role,
            'role_display': user.get_role_display(),
            'email': user.email or '',
            'rattachement': rattachement,
            'is_active': user.is_active,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'presence_at': presence_at.isoformat() if presence_at else None,
            'ip': ip,
            'geo': geo,
            'geo_label': geo.get('label') or '—',
            'geo_lat': geo.get('lat'),
            'geo_lon': geo.get('lon'),
            'geo_source': geo.get('source') or 'none',
            'user_agent': data.get('_presence_ua') or '',
            'expire_date': sess.expire_date.isoformat() if sess.expire_date else None,
            'en_ligne': en_ligne,
            'est_session_courante': False,
        })

    # Plus récents d'abord
    result.sort(
        key=lambda r: (r['en_ligne'], r['presence_at'] or r['last_login'] or ''),
        reverse=True,
    )
    return result


def resume_sessions(sessions: list[dict]) -> dict:
    uniques = {s['user_id'] for s in sessions}
    en_ligne = sum(1 for s in sessions if s['en_ligne'])
    par_role_sessions: dict[str, int] = {}
    par_role_uniques: dict[str, set] = {}
    for s in sessions:
        label = s.get('role_display') or s.get('role') or '?'
        par_role_sessions[label] = par_role_sessions.get(label, 0) + 1
        par_role_uniques.setdefault(label, set()).add(s['user_id'])
    return {
        'sessions': len(sessions),
        'utilisateurs_uniques': len(uniques),
        'en_ligne': en_ligne,
        'par_role': {k: len(v) for k, v in par_role_uniques.items()},
        'par_role_sessions': par_role_sessions,
    }


def supprimer_session(session_key: str) -> bool:
    uid = None
    sess = Session.objects.filter(session_key=session_key).first()
    if sess:
        try:
            uid = int(sess.get_decoded().get('_auth_user_id'))
        except (TypeError, ValueError, Exception):
            uid = None
    deleted, _ = Session.objects.filter(session_key=session_key).delete()
    if deleted and uid:
        User = get_user_model()
        User.objects.filter(pk=uid, session_key_courante=session_key).update(
            session_key_courante='',
        )
    return deleted > 0


MSG_DEJA_EN_LIGNE = (
    'Ce compte a déjà une session en ligne. '
    'Déconnectez-vous d’abord de l’autre appareil avant de vous reconnecter.'
)


def _session_appartient(data: dict, user_id) -> bool:
    try:
        return int(data.get('_auth_user_id')) == int(user_id)
    except (TypeError, ValueError):
        return False


def _session_est_en_ligne(data: dict, now=None) -> bool:
    now = now or timezone.now()
    presence_at = _parse_presence_at(data.get('_presence_at'))
    return bool(presence_at and (now - presence_at) <= SEUIL_EN_LIGNE)


def _decoder_session(sess: Session) -> dict | None:
    try:
        return sess.get_decoded()
    except Exception:
        return None


def trouver_session_concurrente(user, *, exclure_session_key: str | None = None):
    """Autre session Django encore valide pour cet utilisateur, ou None."""
    now = timezone.now()
    exclure = exclure_session_key or ''
    stored = getattr(user, 'session_key_courante', '') or ''
    if stored and stored != exclure:
        sess = Session.objects.filter(
            session_key=stored, expire_date__gte=now,
        ).first()
        if sess:
            data = _decoder_session(sess)
            if data and _session_appartient(data, user.pk):
                return sess, data

    for sess in Session.objects.filter(expire_date__gte=now).iterator():
        if sess.session_key == exclure:
            continue
        data = _decoder_session(sess)
        if data and _session_appartient(data, user.pk):
            return sess, data
    return None


def session_concurrente_en_ligne(user, *, exclure_session_key: str | None = None) -> bool:
    """True si l'utilisateur a déjà une session en ligne ailleurs."""
    found = trouver_session_concurrente(user, exclure_session_key=exclure_session_key)
    if not found:
        return False
    _sess, data = found
    now = timezone.now()
    if _session_est_en_ligne(data, now):
        return True
    last = getattr(user, 'last_login', None)
    if last:
        if timezone.is_naive(last):
            last = timezone.make_aware(last, timezone.get_current_timezone())
        if (now - last) <= SEUIL_EN_LIGNE:
            return True
    return False


def invalider_sessions_utilisateur(user_id, *, exclure_session_key: str | None = None) -> int:
    """Supprime les autres sessions authentifiées de cet utilisateur."""
    now = timezone.now()
    exclure = exclure_session_key or ''
    n = 0
    for sess in Session.objects.filter(expire_date__gte=now).iterator():
        if sess.session_key == exclure:
            continue
        data = _decoder_session(sess)
        if data and _session_appartient(data, user_id):
            sess.delete()
            n += 1
    return n


def activer_session_connexion(user, request) -> None:
    """Après login : mémoriser la session courante et fermer les autres."""
    if not request.session.session_key:
        request.session.save()
    key = request.session.session_key or ''
    invalider_sessions_utilisateur(user.pk, exclure_session_key=key)
    User = get_user_model()
    User.objects.filter(pk=user.pk).update(session_key_courante=key)
    user.session_key_courante = key


def liberer_session_connexion(user, session_key: str | None = None) -> None:
    """Oublie la session mémorisée (déconnexion ou kick)."""
    if not user or not getattr(user, 'pk', None):
        return
    stored = getattr(user, 'session_key_courante', '') or ''
    if session_key and stored and stored != session_key:
        return
    User = get_user_model()
    User.objects.filter(pk=user.pk).update(session_key_courante='')
    user.session_key_courante = ''
