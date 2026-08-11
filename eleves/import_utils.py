"""
Import d'élèves depuis Excel (.xlsx) ou CSV / TSV.

Colonnes attendues :
  matricule;numero_identification;numero_permanent;numero_impot;nom;postnom;prenom;
  date_naissance;sexe;classe;ecole_code;lieu_naissance;adresse;
  nom_pere;postnom_pere;prenom_pere;telephone_pere;email_pere;profession_pere;
  nom_mere;postnom_mere;prenom_mere;telephone_mere;email_mere;profession_mere;
  lien_tuteur;nom_tuteur;telephone_tuteur;email_tuteur

Champs obligatoires : matricule, nom, prenom, date_naissance, sexe, classe
École : ecole_code dans la ligne, sinon ecole_id / ecole_code par défaut.
Classe : nom exact d'une classe déjà créée pour l'école (pas de création auto).
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from django.db import transaction
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook

from ecoles.models import Classe, Ecole
from .models import Eleve


def _resoudre_classe(ecole, nom_classe: str) -> Classe:
    nom = (nom_classe or '').strip()
    if not nom:
        raise ValueError('classe manquante')
    existante = Classe.objects.filter(ecole=ecole, nom__iexact=nom).first()
    if not existante:
        raise ValueError(
            f'Classe inconnue « {nom} » pour cette école. '
            'Créez-la d\'abord (fiche école ou import Classes).'
        )
    return existante

REQUIRED = ('matricule', 'nom', 'prenom', 'date_naissance', 'sexe', 'classe')

HEADER_ALIASES = {
    'matricule': 'matricule',
    'mat': 'matricule',
    'numero_identification': 'numero_identification',
    'numero identification': 'numero_identification',
    'n° identification': 'numero_identification',
    'no_identification': 'numero_identification',
    'num_identification': 'numero_identification',
    'nid': 'numero_identification',
    'numero_permanent': 'numero_permanent',
    'numero permanent': 'numero_permanent',
    'n° permanent': 'numero_permanent',
    'no_permanent': 'numero_permanent',
    'num_permanent': 'numero_permanent',
    'npp': 'numero_permanent',
    'numero_impot': 'numero_impot',
    'numero impot': 'numero_impot',
    'n° impot': 'numero_impot',
    'n° impôt': 'numero_impot',
    'numero_impôt': 'numero_impot',
    'nif': 'numero_impot',
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
    'nom_pere': 'nom_pere',
    'père': 'nom_pere',
    'pere': 'nom_pere',
    'postnom_pere': 'postnom_pere',
    'prenom_pere': 'prenom_pere',
    'telephone_pere': 'telephone_pere',
    'tel_pere': 'telephone_pere',
    'email_pere': 'email_pere',
    'profession_pere': 'profession_pere',
    'nom_mere': 'nom_mere',
    'mère': 'nom_mere',
    'mere': 'nom_mere',
    'postnom_mere': 'postnom_mere',
    'prenom_mere': 'prenom_mere',
    'telephone_mere': 'telephone_mere',
    'tel_mere': 'telephone_mere',
    'email_mere': 'email_mere',
    'profession_mere': 'profession_mere',
    'lien_tuteur': 'lien_tuteur',
    'lien': 'lien_tuteur',
    'nom_tuteur': 'nom_tuteur',
    'tuteur': 'nom_tuteur',
    'telephone_tuteur': 'telephone_tuteur',
    'telephone': 'telephone_tuteur',
    'téléphone_tuteur': 'telephone_tuteur',
    'tel_tuteur': 'telephone_tuteur',
    'email_tuteur': 'email_tuteur',
}

MODELE_HEADERS = [
    'matricule', 'numero_identification', 'numero_permanent', 'numero_impot',
    'nom', 'postnom', 'prenom', 'date_naissance', 'sexe', 'classe',
    'ecole_code', 'lieu_naissance', 'adresse',
    'nom_pere', 'postnom_pere', 'prenom_pere', 'telephone_pere', 'email_pere', 'profession_pere',
    'nom_mere', 'postnom_mere', 'prenom_mere', 'telephone_mere', 'email_mere', 'profession_mere',
    'lien_tuteur', 'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
]

PARENT_TEXT_FIELDS = (
    'nom_pere', 'postnom_pere', 'prenom_pere', 'telephone_pere', 'email_pere', 'profession_pere',
    'nom_mere', 'postnom_mere', 'prenom_mere', 'telephone_mere', 'email_mere', 'profession_mere',
    'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
)


def _parse_lien_tuteur(value: Any) -> str:
    raw = _cell_str(value).lower()
    if not raw:
        return ''
    mapping = {
        'pere': Eleve.LienTuteur.PERE,
        'père': Eleve.LienTuteur.PERE,
        'mere': Eleve.LienTuteur.MERE,
        'mère': Eleve.LienTuteur.MERE,
        'tuteur': Eleve.LienTuteur.TUTEUR,
        'tuteur_legal': Eleve.LienTuteur.TUTEUR,
        'tuteur légal': Eleve.LienTuteur.TUTEUR,
        'oncle_tante': Eleve.LienTuteur.ONCLE_TANTE,
        'oncle': Eleve.LienTuteur.ONCLE_TANTE,
        'tante': Eleve.LienTuteur.ONCLE_TANTE,
        'grand_parent': Eleve.LienTuteur.GRAND_PARENT,
        'grand-parent': Eleve.LienTuteur.GRAND_PARENT,
        'grandparent': Eleve.LienTuteur.GRAND_PARENT,
        'autre': Eleve.LienTuteur.AUTRE,
    }
    if raw in mapping:
        return mapping[raw]
    valid = {c.value for c in Eleve.LienTuteur}
    if raw in valid:
        return raw
    raise ValueError(
        f'Lien tuteur invalide « {value} » '
        '(pere, mere, tuteur, oncle_tante, grand_parent, autre)'
    )


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


def _cell_str(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _cell_str(value)
    if not raw:
        raise ValueError('Date de naissance manquante')
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Date invalide « {raw} » (attendu AAAA-MM-JJ ou JJ/MM/AAAA)')


def _parse_sexe(value: Any) -> str:
    raw = _cell_str(value).upper()
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


def _rows_from_xlsx(data: bytes) -> list[dict[str, str]]:
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        headers_raw = next(rows_iter)
    except StopIteration as exc:
        raise ValueError('Fichier Excel vide.') from exc

    headers = [_normalize_header(_cell_str(h)) for h in headers_raw]
    if not any(headers):
        raise ValueError('En-tête Excel introuvable.')

    missing = [f for f in REQUIRED if f not in headers]
    if missing:
        raise ValueError(
            'Colonnes obligatoires manquantes : ' + ', '.join(missing)
            + '. Attendu : matricule, nom, prenom, date_naissance, sexe, classe, …'
        )

    rows: list[dict[str, str]] = []
    for i, values in enumerate(rows_iter, start=2):
        if values is None or not any(v not in (None, '') for v in values):
            continue
        row: dict[str, str] = {'_ligne': str(i)}
        for idx, header in enumerate(headers):
            if not header:
                continue
            row[header] = _cell_str(values[idx] if idx < len(values) else '')
        rows.append(row)
    return rows


def _rows_from_csv(contenu: str | bytes) -> list[dict[str, str]]:
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
    if missing:
        raise ValueError(
            'Colonnes obligatoires manquantes : ' + ', '.join(missing)
            + '. Attendu : matricule;nom;prenom;date_naissance;sexe;classe;ecole_code;…'
        )

    rows: list[dict[str, str]] = []
    for i, raw in enumerate(reader, start=2):
        if not any((v or '').strip() for v in raw.values()):
            continue
        row = {canon: (raw.get(original) or '').strip() for canon, original in mapping.items()}
        row['_ligne'] = str(i)
        rows.append(row)
    return rows


def lire_lignes(contenu: str | bytes, filename: str = '') -> list[dict[str, str]]:
    """Parse Excel ou CSV et renvoie une liste de dicts normalisés."""
    name = (filename or '').lower()
    if isinstance(contenu, str):
        return _rows_from_csv(contenu)

    data = bytes(contenu)
    if name.endswith(('.xlsx', '.xlsm')) or data[:2] == b'PK':
        try:
            return _rows_from_xlsx(data)
        except Exception as exc:  # noqa: BLE001
            if name.endswith(('.xlsx', '.xlsm')):
                raise ValueError(f'Lecture Excel impossible : {exc}') from exc
    return _rows_from_csv(data)


def importer_eleves(
    contenu: str | bytes,
    *,
    ecole_id: int | None = None,
    ecole_code: str | None = None,
    filename: str = '',
    update_existing: bool = True,
) -> dict[str, Any]:
    """
    Importe les élèves. Retourne un résumé :
    {created, updated, skipped, errors: [{ligne, message}], total}
    """
    rows = lire_lignes(contenu, filename=filename)

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

                classe = _resoudre_classe(ecole, row.get('classe', ''))
                defaults = {
                    'numero_identification': (row.get('numero_identification') or '').strip() or None,
                    'numero_permanent': (row.get('numero_permanent') or '').strip() or None,
                    'numero_impot': (row.get('numero_impot') or '').strip() or None,
                    'nom': row['nom'].strip(),
                    'postnom': row.get('postnom', '').strip(),
                    'prenom': row['prenom'].strip(),
                    'date_naissance': _parse_date(row['date_naissance']),
                    'lieu_naissance': row.get('lieu_naissance', '').strip(),
                    'sexe': _parse_sexe(row['sexe']),
                    'ecole': ecole,
                    'classe': classe,
                    'adresse': row.get('adresse', '').strip(),
                    'lien_tuteur': _parse_lien_tuteur(row.get('lien_tuteur', '')),
                }
                for key in PARENT_TEXT_FIELDS:
                    defaults[key] = row.get(key, '').strip()
                for key in ('nom', 'prenom'):
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
            except Exception as exc:  # noqa: BLE001
                errors.append({'ligne': ligne, 'message': str(exc)})

    return {
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'errors': errors[:50],
        'errors_count': len(errors),
        'total': len(rows),
    }


def generer_modele_xlsx() -> bytes:
    wb = Workbook()
    info = wb.active
    info.title = 'Instructions'
    info.append(['Champ', 'Description'])
    info.append(['matricule', 'Optionnel à la création UI — format AAAA-0001 ; obligatoire à l’import'])
    info.append(['numero_identification', 'Auto — code école + n° d’ordre du matricule'])
    info.append(['numero_permanent', 'Optionnel — unique si renseigné'])
    info.append(['numero_impot', 'Optionnel — unique si renseigné'])
    info.append(['nom / prenom', 'Obligatoires'])
    info.append(['postnom', 'Optionnel'])
    info.append(['date_naissance', 'Obligatoire — AAAA-MM-JJ'])
    info.append(['sexe', 'Obligatoire — M ou F'])
    info.append([
        'classe',
        'Obligatoire — nom exact d\'une classe déjà créée pour l\'école',
    ])
    info.append(['ecole_code', 'Code école (sinon école choisie à l\'import)'])
    info.append(['lieu_naissance / adresse', 'Optionnels'])
    info.append(['nom_pere / postnom_pere / prenom_pere / telephone_pere / email_pere / profession_pere', 'Optionnels'])
    info.append(['nom_mere / postnom_mere / prenom_mere / telephone_mere / email_mere / profession_mere', 'Optionnels'])
    info.append(['lien_tuteur', 'Optionnel — pere|mere|tuteur|oncle_tante|grand_parent|autre'])
    info.append(['nom_tuteur / telephone_tuteur / email_tuteur', 'Optionnels'])
    info.append(['', ''])
    info.append(['Ordre recommandé', '1) Classes  2) Élèves  3) Comptes enseignants'])

    ws = wb.create_sheet('Eleves')
    ws.append(MODELE_HEADERS)
    ws.append([
        'ELV-2026-DEMO-001', 'ID-KIN-001', 'NP-2026-0001',
        'KABONGO', 'MUTOMBO', 'Jean', '2015-03-12', 'M',
        '6ème Primaire', '7-136755', 'Kinshasa', 'Av. de la Libération',
        'KABONGO', 'ILUNGA', 'Pierre', '+243810000010', 'pierre.kabongo@email.cd', 'Commerçant',
        'MWAMBA', 'KABONGO', 'Jeanne', '+243810000011', 'jeanne.mwamba@email.cd', 'Enseignante',
        'mere', 'MWAMBA Jeanne', '+243810000011', 'jeanne.mwamba@email.cd',
    ])
    ws.append([
        'ELV-2026-DEMO-002', 'ID-KIN-002', 'NP-2026-0002',
        'MUKENDI', '', 'Marie', '2016-07-21', 'F',
        '5ème Primaire', '7-136755', 'Kinshasa', 'C/Gombe',
        'MUKENDI', '', 'Joseph', '+243810000020', '', 'Chauffeur',
        'KALALA', '', 'Sophie', '+243810000021', '', '',
        'pere', 'MUKENDI Joseph', '+243810000020', '',
    ])
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 14), 48)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def reponse_modele_xlsx() -> HttpResponse:
    response = HttpResponse(
        generer_modele_xlsx(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="modele_import_eleves.xlsx"'
    return response
