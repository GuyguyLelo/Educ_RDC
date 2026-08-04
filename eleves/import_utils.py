"""
Import d'élèves depuis un fichier CSV / TSV.
Colonnes attendues (séparateur ; ou , détecté automatiquement) :

  matricule;nom;postnom;prenom;date_naissance;sexe;classe;ecole_code;
  lieu_naissance;adresse;nom_tuteur;telephone_tuteur

Champs obligatoires : matricule, nom, prenom, date_naissance, sexe, classe
École : ecole_code dans la ligne, sinon ecole_id / ecole_code par défaut.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from django.db import transaction

from ecoles.models import Ecole
from .models import Eleve

REQUIRED = ('matricule', 'nom', 'prenom', 'date_naissance', 'sexe', 'classe')

HEADER_ALIASES = {
    'matricule': 'matricule',
    'mat': 'matricule',
    'nom': 'nom',
    'postnom': 'postnom',
    'post-nom': 'postnom',
    'prenom': 'prenom',
    'prénom': 'prenom',
    'date_naissance': 'date_naissance',
    'date naissance': 'date_naissance',
    'date de naissance': 'date_naissance',
    'naissance': 'date_naissance',
    'sexe': 'sexe',
    'genre': 'sexe',
    'classe': 'classe',
    'ecole_code': 'ecole_code',
    'code_ecole': 'ecole_code',
    'code ecole': 'ecole_code',
    'ecole': 'ecole_code',
    'lieu_naissance': 'lieu_naissance',
    'lieu de naissance': 'lieu_naissance',
    'adresse': 'adresse',
    'nom_tuteur': 'nom_tuteur',
    'tuteur': 'nom_tuteur',
    'telephone_tuteur': 'telephone_tuteur',
    'telephone': 'telephone_tuteur',
    'téléphone_tuteur': 'telephone_tuteur',
    'tel_tuteur': 'telephone_tuteur',
}


def _normalize_header(value: str) -> str:
    raw = (value or '').strip().lower()
    spaced = re.sub(r'[\s_]+', ' ', raw)
    underscored = spaced.replace(' ', '_')
    return (
        HEADER_ALIASES.get(raw)
        or HEADER_ALIASES.get(spaced)
        or HEADER_ALIASES.get(underscored)
        or underscored
    )


def _detect_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=';,\t|')
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ';' if sample.count(';') >= sample.count(',') else ','
        return dialect


def _parse_date(value: str) -> date:
    raw = (value or '').strip()
    if not raw:
        raise ValueError('Date de naissance manquante')
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Date invalide « {raw} » (attendu AAAA-MM-JJ ou JJ/MM/AAAA)')


def _parse_sexe(value: str) -> str:
    raw = (value or '').strip().upper()
    if raw in ('M', 'H', 'MASCULIN', 'HOMME', 'GARCON', 'GARÇON'):
        return Eleve.Sexe.MASCULIN
    if raw in ('F', 'FEMININ', 'FÉMININ', 'FEMME', 'FILLE'):
        return Eleve.Sexe.FEMININ
    raise ValueError(f'Sexe invalide « {value} » (M ou F)')


def _decode_bytes(data: bytes) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def lire_lignes(contenu: str | bytes) -> list[dict[str, str]]:
    """Parse le CSV et renvoie une liste de dicts normalisés."""
    text = _decode_bytes(contenu) if isinstance(contenu, (bytes, bytearray)) else contenu
    text = text.strip()
    if not text:
        raise ValueError('Fichier vide.')

    sample = text[:4096]
    dialect = _detect_dialect(sample)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError('En-tête CSV introuvable.')

    mapping = {_normalize_header(h): h for h in reader.fieldnames if h}
    missing = [f for f in REQUIRED if f not in mapping]
    # ecole_code peut être fourni par défaut hors fichier
    if missing:
        raise ValueError(
            'Colonnes obligatoires manquantes : ' + ', '.join(missing)
            + '. Attendu : matricule;nom;prenom;date_naissance;sexe;classe;ecole_code;…'
        )

    rows: list[dict[str, str]] = []
    for i, raw in enumerate(reader, start=2):
        if not any((v or '').strip() for v in raw.values()):
            continue
        row = {}
        for canon, original in mapping.items():
            row[canon] = (raw.get(original) or '').strip()
        row['_ligne'] = str(i)
        rows.append(row)
    return rows


def importer_eleves(
    contenu: str | bytes,
    *,
    ecole_id: int | None = None,
    ecole_code: str | None = None,
    update_existing: bool = True,
) -> dict[str, Any]:
    """
    Importe les élèves. Retourne un résumé :
    {created, updated, skipped, errors: [{ligne, message}], total}
    """
    rows = lire_lignes(contenu)

    ecole_defaut = None
    if ecole_id:
        ecole_defaut = Ecole.objects.filter(pk=ecole_id).first()
        if not ecole_defaut:
            raise ValueError(f'École introuvable (id={ecole_id}).')
    elif ecole_code:
        ecole_defaut = Ecole.objects.filter(code=ecole_code.strip()).first()
        if not ecole_defaut:
            raise ValueError(f'École introuvable (code={ecole_code}).')

    ecole_cache: dict[str, Ecole] = {}
    created = updated = skipped = 0
    errors: list[dict[str, str]] = []

    with transaction.atomic():
        for row in rows:
            ligne = row.get('_ligne', '?')
            try:
                matricule = row.get('matricule', '').strip()
                if not matricule:
                    raise ValueError('Matricule manquant')

                code = (row.get('ecole_code') or '').strip()
                ecole = ecole_defaut
                if code:
                    if code not in ecole_cache:
                        ecole_cache[code] = Ecole.objects.filter(code=code).first()
                    ecole = ecole_cache[code]
                    if not ecole:
                        raise ValueError(f'École inconnue (code={code})')
                if not ecole:
                    raise ValueError('École non précisée (colonne ecole_code ou école par défaut)')

                defaults = {
                    'nom': row['nom'].strip(),
                    'postnom': row.get('postnom', '').strip(),
                    'prenom': row['prenom'].strip(),
                    'date_naissance': _parse_date(row['date_naissance']),
                    'lieu_naissance': row.get('lieu_naissance', '').strip(),
                    'sexe': _parse_sexe(row['sexe']),
                    'ecole': ecole,
                    'classe': row['classe'].strip(),
                    'adresse': row.get('adresse', '').strip(),
                    'nom_tuteur': row.get('nom_tuteur', '').strip(),
                    'telephone_tuteur': row.get('telephone_tuteur', '').strip(),
                }
                for key in ('nom', 'prenom', 'classe'):
                    if not defaults[key]:
                        raise ValueError(f'{key} manquant')

                existing = Eleve.objects.filter(matricule=matricule).first()
                if existing:
                    if not update_existing:
                        skipped += 1
                        continue
                    for k, v in defaults.items():
                        setattr(existing, k, v)
                    existing.save()
                    updated += 1
                else:
                    Eleve.objects.create(matricule=matricule, **defaults)
                    created += 1
            except Exception as exc:  # noqa: BLE001 — collecter les erreurs ligne à ligne
                errors.append({'ligne': ligne, 'message': str(exc)})

    return {
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'errors': errors[:50],
        'errors_count': len(errors),
        'total': len(rows),
    }
