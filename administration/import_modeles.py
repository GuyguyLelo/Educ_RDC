"""
Génération des modèles Excel pour l'importation de données.
Alignés sur les modèles actuels (classes, GPS écoles, N° identification…).
"""
from __future__ import annotations

import io
from typing import Callable

from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utilisateurs.permissions import EstNationalOuAdmin

from eleves.import_utils import generer_modele_xlsx as generer_modele_eleves
from ecoles.import_personnel import generer_modele_xlsx as generer_modele_personnel
from ecoles.import_classes import generer_modele_xlsx as generer_modele_classes


def _xlsx_response(content: bytes, filename: str) -> HttpResponse:
    from urllib.parse import quote
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    safe_ascii = filename.encode('ascii', 'replace').decode('ascii').replace('?', '_')
    response['Content-Disposition'] = (
        f'attachment; filename="{safe_ascii}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return response


def _build_workbook(
    sheet_title: str,
    headers: list[str],
    rows: list[list],
    instructions: list[tuple[str, str]] | None = None,
) -> bytes:
    wb = Workbook()
    if instructions:
        info = wb.active
        info.title = 'Instructions'
        info.append(['Champ / Info', 'Description'])
        for label, desc in instructions:
            info.append([label, desc])
        ws = wb.create_sheet(sheet_title[:31])
    else:
        ws = wb.active
        ws.title = sheet_title[:31]

    ws.append(headers)
    for row in rows:
        ws.append(row)

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 14), 48)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generer_modele_ecoles() -> bytes:
    headers = [
        'nom', 'code', 'numero_agrement', 'type_ecole', 'niveau',
        'adresse', 'telephone', 'email', 'latitude', 'longitude',
        'directeur', 'effectif_mat', 'effectif_prim', 'effectif_sec',
        'antenne_code',
    ]
    rows = [
        [
            'EP Demo Lukunga', '7-999001', 'AGR/EPSP/2026/001', 'publique', 'primaire',
            'Av. de la Paix N°12', '+243810000010', 'ep.demo@educ.cd',
            '-4.3250000', '15.3222000', 'Directeur Demo', 20, 180, 0, 'ANT-DEMO',
        ],
        [
            'CS Espoir', '7-999002', '', 'conventionnee', 'mixte',
            'Q/Sans Fil', '+243810000011', '',
            '', '', 'Mme Espoir', 15, 120, 90, 'ANT-DEMO',
        ],
    ]
    instructions = [
        ('nom', 'Obligatoire — nom de l\'établissement'),
        ('code', 'Obligatoire — code unique école'),
        ('numero_agrement', 'Optionnel — N° d\'agrément'),
        ('type_ecole', 'publique | privee | conventionnee'),
        ('niveau', 'maternelle | primaire | secondaire | mixte'),
        ('adresse', 'Obligatoire'),
        ('telephone / email', 'Optionnels'),
        ('latitude / longitude', 'Optionnels — coordonnées GPS décimales'),
        ('directeur', 'Optionnel'),
        ('effectif_mat / prim / sec', 'Effectifs déclarés (entiers)'),
        ('antenne_code', 'Obligatoire — code de l\'antenne de rattachement'),
        ('Ordre recommandé', 'PA → PE → Antennes → Écoles → Classes → Élèves / Personnel'),
    ]
    return _build_workbook('Ecoles', headers, rows, instructions)


def generer_modele_provinces_admin() -> bytes:
    headers = ['nom', 'code']
    rows = [
        ['Kinshasa', 'PA-KIN'],
        ['Kongo Central', 'PA-KC'],
    ]
    instructions = [
        ('nom', 'Obligatoire'),
        ('code', 'Obligatoire — code unique'),
    ]
    return _build_workbook('Provinces_admin', headers, rows, instructions)


def generer_modele_provinces_educ() -> bytes:
    headers = ['nom', 'code', 'province_administrative_code']
    rows = [
        ['PE Kinshasa-Est', 'PE-KIN-E', 'PA-KIN'],
        ['PE Kinshasa-Ouest', 'PE-KIN-O', 'PA-KIN'],
    ]
    instructions = [
        ('nom', 'Obligatoire'),
        ('code', 'Obligatoire — code unique'),
        ('province_administrative_code', 'Obligatoire — code PA existante'),
    ]
    return _build_workbook('Provinces_educ', headers, rows, instructions)


def generer_modele_antennes() -> bytes:
    headers = ['nom', 'code', 'province_educationnelle_code', 'adresse', 'telephone']
    rows = [
        ['Antenne Gombe', 'ANT-GOM', 'PE-KIN-E', 'Av. Tombalbaye', '+243810000100'],
        ['Antenne Demo', 'ANT-DEMO', 'PE-KIN-E', 'C/Mont-Ngafula', '+243810000101'],
    ]
    instructions = [
        ('nom', 'Obligatoire'),
        ('code', 'Obligatoire — code unique'),
        ('province_educationnelle_code', 'Obligatoire — code PE existante'),
        ('adresse / telephone', 'Optionnels'),
    ]
    return _build_workbook('Antennes', headers, rows, instructions)


MODELES: dict[str, dict] = {
    'classes': {
        'cle': 'classes',
        'titre': 'Classes scolaires',
        'description': (
            'Classes créées par l\'administratif de l\'école — '
            'à importer avant les élèves et les comptes enseignants.'
        ),
        'fichier': 'modele_import_classes.xlsx',
        'obligatoires': ['nom'],
        'colonnes': ['nom', 'code', 'ecole_code', 'active'],
        'url': '/api/modeles-import/classes/',
        'generer': generer_modele_classes,
        'categorie': 'opérationnel',
        'notes': (
            'Le nom doit être repris à l\'identique dans l\'import élèves. '
            'Ordre : Classes → Élèves → Enseignants (classe titulaire).'
        ),
    },
    'eleves': {
        'cle': 'eleves',
        'titre': 'Élèves',
        'description': (
            'Import massif des élèves (matricule, N° identification / permanent / impôt, '
            'classe existante de l\'école…).'
        ),
        'fichier': 'modele_import_eleves.xlsx',
        'obligatoires': ['matricule', 'nom', 'prenom', 'date_naissance', 'sexe', 'classe'],
        'colonnes': [
            'matricule', 'numero_identification', 'numero_permanent', 'numero_impot',
            'nom', 'postnom', 'prenom', 'date_naissance', 'sexe', 'classe',
            'ecole_code', 'lieu_naissance', 'adresse',
            'nom_pere', 'telephone_pere', 'email_pere',
            'nom_mere', 'telephone_mere', 'email_mere',
            'lien_tuteur', 'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
        ],
        'url': '/api/modeles-import/eleves/',
        'generer': generer_modele_eleves,
        'categorie': 'opérationnel',
        'notes': (
            'Listes déroulantes Excel (protégées) pour sexe, classe, ecole_code, lien_tuteur. '
            'classe = nom exact d\'une classe déjà créée pour l\'école '
            '(admin école : classes de son établissement préchargées). '
            'Parents optionnels (père / mère / tuteur + contacts).'
        ),
    },
    'personnels': {
        'cle': 'personnels',
        'titre': 'Personnel scolaire',
        'description': 'Agents et enseignants rattachés à une école (import depuis la fiche école).',
        'fichier': 'modele_import_personnel.xlsx',
        'obligatoires': ['nom', 'prenom', 'sexe'],
        'colonnes': [
            'matricule', 'nom', 'postnom', 'prenom', 'sexe', 'fonction',
            'telephone', 'email', 'date_naissance', 'date_prise_service',
        ],
        'url': '/api/modeles-import/personnels/',
        'generer': generer_modele_personnel,
        'categorie': 'opérationnel',
        'notes': (
            'sexe: M|F — fonction: directeur|directeur_etudes|enseignant|secretaire|'
            'comptable|surveillant|prefet|autre'
        ),
    },
    'ecoles': {
        'cle': 'ecoles',
        'titre': 'Écoles',
        'description': 'Établissements scolaires — GPS, effectifs, rattachement via code antenne.',
        'fichier': 'modele_import_ecoles.xlsx',
        'obligatoires': ['nom', 'code', 'adresse', 'antenne_code'],
        'colonnes': [
            'nom', 'code', 'numero_agrement', 'type_ecole', 'niveau',
            'adresse', 'telephone', 'email', 'latitude', 'longitude',
            'directeur', 'effectif_mat', 'effectif_prim', 'effectif_sec',
            'antenne_code',
        ],
        'url': '/api/modeles-import/ecoles/',
        'generer': generer_modele_ecoles,
        'categorie': 'opérationnel',
        'notes': (
            'type_ecole: publique|privee|conventionnee — '
            'niveau: maternelle|primaire|secondaire|mixte — '
            'latitude/longitude optionnels (GPS).'
        ),
    },
    'provinces-administratives': {
        'cle': 'provinces-administratives',
        'titre': 'Provinces administratives',
        'description': 'Niveau 1 de la hiérarchie territoriale.',
        'fichier': 'modele_import_provinces_admin.xlsx',
        'obligatoires': ['nom', 'code'],
        'colonnes': ['nom', 'code'],
        'url': '/api/modeles-import/provinces-administratives/',
        'generer': generer_modele_provinces_admin,
        'categorie': 'referentiel',
    },
    'provinces-educationnelles': {
        'cle': 'provinces-educationnelles',
        'titre': 'Provinces éducationnelles',
        'description': 'Niveau 2 — liées à une province administrative par son code.',
        'fichier': 'modele_import_provinces_educ.xlsx',
        'obligatoires': ['nom', 'code', 'province_administrative_code'],
        'colonnes': ['nom', 'code', 'province_administrative_code'],
        'url': '/api/modeles-import/provinces-educationnelles/',
        'generer': generer_modele_provinces_educ,
        'categorie': 'referentiel',
    },
    'antennes': {
        'cle': 'antennes',
        'titre': 'Antennes',
        'description': 'Niveau 3 — liées à une province éducationnelle par son code.',
        'fichier': 'modele_import_antennes.xlsx',
        'obligatoires': ['nom', 'code', 'province_educationnelle_code'],
        'colonnes': ['nom', 'code', 'province_educationnelle_code', 'adresse', 'telephone'],
        'url': '/api/modeles-import/antennes/',
        'generer': generer_modele_antennes,
        'categorie': 'referentiel',
    },
}


def catalogue_modeles() -> list[dict]:
    items = []
    for meta in MODELES.values():
        items.append({
            'cle': meta['cle'],
            'titre': meta['titre'],
            'description': meta['description'],
            'fichier': meta['fichier'],
            'obligatoires': meta['obligatoires'],
            'colonnes': meta['colonnes'],
            'url': meta['url'],
            'categorie': meta['categorie'],
            'notes': meta.get('notes', ''),
        })
    return items


def reponse_modele(cle: str) -> HttpResponse | None:
    meta = MODELES.get(cle)
    if not meta:
        return None
    generer = meta['generer']
    result = generer()
    if isinstance(result, tuple) and len(result) == 2:
        contenu, nom_fichier = result
        return _xlsx_response(contenu, nom_fichier)
    return _xlsx_response(result, meta['fichier'])


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstNationalOuAdmin])
def api_liste_modeles_import(request):
    """Catalogue des modèles Excel disponibles."""
    return Response({'count': len(MODELES), 'results': catalogue_modeles()})


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstNationalOuAdmin])
def api_telecharger_modele_import(request, cle: str):
    """Télécharge un modèle Excel par clé."""
    response = reponse_modele(cle)
    if response is None:
        return Response(
            {'detail': f'Modèle inconnu « {cle} ». Clés : {", ".join(MODELES)}'},
            status=404,
        )
    return response
