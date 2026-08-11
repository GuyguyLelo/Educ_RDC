"""
Géolocalisation approximative des utilisateurs (IP + option navigateur).
"""
from __future__ import annotations

import ipaddress
import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# Cache processus (évite de marteler l'API publique)
_GEO_CACHE: dict[str, dict[str, Any]] = {}


def ip_privee_ou_locale(ip: str) -> bool:
    if not ip:
        return True
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _label(parts: list[str]) -> str:
    return ', '.join(p for p in parts if p)


def geolocaliser_ip(ip: str) -> dict[str, Any]:
    """
    Résout une IP publique via ip-api.com (gratuit, sans clé).
    Retourne un dict sérialisable pour la session / API.
    """
    ip = (ip or '').strip()
    if not ip:
        return {
            'label': '—',
            'city': '',
            'region': '',
            'country': '',
            'country_code': '',
            'lat': None,
            'lon': None,
            'source': 'none',
        }
    if ip in _GEO_CACHE:
        return dict(_GEO_CACHE[ip])

    if ip_privee_ou_locale(ip):
        data = {
            'label': 'Réseau local',
            'city': '',
            'region': '',
            'country': '',
            'country_code': '',
            'lat': None,
            'lon': None,
            'source': 'local',
        }
        _GEO_CACHE[ip] = data
        return dict(data)

    data = {
        'label': 'Localisation indisponible',
        'city': '',
        'region': '',
        'country': '',
        'country_code': '',
        'lat': None,
        'lon': None,
        'source': 'ip',
    }
    try:
        url = (
            f'http://ip-api.com/json/{ip}'
            f'?fields=status,message,country,countryCode,regionName,city,lat,lon'
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'Educ_RDC/1.0'})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            payload = json.loads(resp.read().decode('utf-8', errors='replace'))
        if payload.get('status') == 'success':
            city = (payload.get('city') or '').strip()
            region = (payload.get('regionName') or '').strip()
            country = (payload.get('country') or '').strip()
            data = {
                'label': _label([city, region, country]) or country or '—',
                'city': city,
                'region': region,
                'country': country,
                'country_code': (payload.get('countryCode') or '').strip(),
                'lat': payload.get('lat'),
                'lon': payload.get('lon'),
                'source': 'ip',
            }
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.debug('GeoIP échec pour %s: %s', ip, exc)

    _GEO_CACHE[ip] = data
    return dict(data)


def geo_depuis_navigateur(lat, lon, accuracy=None, label: str = '') -> dict[str, Any]:
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return {
            'label': '—',
            'city': '',
            'region': '',
            'country': '',
            'country_code': '',
            'lat': None,
            'lon': None,
            'source': 'none',
        }
    acc = None
    try:
        if accuracy is not None:
            acc = float(accuracy)
    except (TypeError, ValueError):
        acc = None
    return {
        'label': (label or '').strip() or f'{lat_f:.4f}, {lon_f:.4f}',
        'city': '',
        'region': '',
        'country': '',
        'country_code': '',
        'lat': lat_f,
        'lon': lon_f,
        'accuracy': acc,
        'source': 'browser',
    }


def normaliser_geo(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            'label': '—',
            'city': '',
            'region': '',
            'country': '',
            'country_code': '',
            'lat': None,
            'lon': None,
            'source': 'none',
        }
    return {
        'label': raw.get('label') or '—',
        'city': raw.get('city') or '',
        'region': raw.get('region') or '',
        'country': raw.get('country') or '',
        'country_code': raw.get('country_code') or '',
        'lat': raw.get('lat'),
        'lon': raw.get('lon'),
        'accuracy': raw.get('accuracy'),
        'source': raw.get('source') or 'none',
    }
