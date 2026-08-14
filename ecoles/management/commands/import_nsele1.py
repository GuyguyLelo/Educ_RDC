"""
Import écoles — Direction provinciale de Plateau / Antenne Nsele 1.
Usage: python manage.py import_nsele1
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from ecoles.models import (
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
)

SECTION_TYPES = {
    'NON CONVENTIONNE': Ecole.TypeEcole.PUBLIQUE,
    'CONVENTIONNE CATHOLIQUE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE ISLAMIQUE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE KIMBANGUISTE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE PROTESTANTE': Ecole.TypeEcole.CONVENTIONNEE,
    'PRIVE AGREE': Ecole.TypeEcole.PRIVEE,
    'E.R.C': Ecole.TypeEcole.CONVENTIONNEE,
    'ADVENTISTE': Ecole.TypeEcole.CONVENTIONNEE,
}

NULLISH = {'null', 'nulle', 'none', '-', ''}
ADDR_START = re.compile(
    r'(?i)(?<![A-Z0-9])(AV\.?|AVE\.?|AVENUE|CAMP|Q/|QUARTIER|VILLAGE|ILE|BLV\.?|BLD\.?|'
    r'BOULEVARD|CIMETIERE|REF\.?|OCC/|VA\.)(?:\s|$|/)',
)


def clean_text(value: str) -> str:
    if value is None:
        return ''
    text = str(value)
    text = text.replace('N?', 'N°').replace('NÂ°', 'N°').replace('Ã‰', 'É')
    text = text.replace('Ã¨', 'è').replace('Ã©', 'é').replace('Ã ', 'à')
    text = text.replace('RÃ‰VÃ‰REND', 'REVEREND').replace('COLLÃˆGE', 'COLLEGE')
    text = text.replace('LYCÃ‰E', 'LYCEE').replace('Ã‰COLE', 'ECOLE')
    text = text.replace('THÃ‰RÃˆSE', 'THERESE').replace('GENEVIÃˆVE', 'GENEVIEVE')
    text = text.replace('DÃ‰LIVRANCE', 'DELIVRANCE').replace('CHRÃ‰TIENNE', 'CHRETIENNE')
    text = text.replace('Ã‰LISABETH', 'ELISABETH').replace('SACRE C?UR', 'SACRE COEUR')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_null(value: str) -> bool:
    return clean_text(value).lower() in NULLISH


def guess_niveau(nom: str, mat: int, prim: int, sec: int) -> str:
    n = nom.upper()
    if 'CRECHE' in n or 'CRÈCHE' in n or n.startswith('EC ') or n.startswith('E.C'):
        return Ecole.Niveau.CRECHE
    if n.startswith('EM ') or n.startswith('E.M') or 'MATERNELLE' in n or 'PRESCOLAIRE' in n:
        return Ecole.Niveau.MATERNELLE
    if n.startswith('EP ') or n.startswith('E.P'):
        return Ecole.Niveau.PRIMAIRE
    flags = sum(1 for x in (mat, prim, sec) if x > 0)
    if flags > 1:
        return Ecole.Niveau.MIXTE
    if sec > 0 and prim == 0 and mat == 0:
        return Ecole.Niveau.SECONDAIRE
    if prim > 0 and sec == 0 and mat == 0:
        return Ecole.Niveau.PRIMAIRE
    if mat > 0 and prim == 0 and sec == 0:
        return Ecole.Niveau.MATERNELLE
    if any(n.startswith(p) for p in (
        'INSTITUT', 'INST ', 'INSTUTIT', 'LYCEE', 'LYC', 'ITC', 'ITAV', 'ITCI',
        'IT ', 'I.T', 'COLLEGE', 'COL ', 'CRS ',
    )):
        return Ecole.Niveau.SECONDAIRE
    if n.startswith('CS ') or n.startswith('C.S') or n.startswith('GS '):
        return Ecole.Niveau.MIXTE
    return Ecole.Niveau.MIXTE


def split_nom_adresse(middle: str):
    middle = clean_text(middle)
    if not middle:
        return 'École sans nom', ''
    m = ADDR_START.search(middle)
    if m and m.start() > 2:
        nom = middle[:m.start()].strip(' -,')
        adresse = middle[m.start():].strip()
        return nom or middle, adresse
    return middle, ''


def parse_school_line(line: str, type_ecole: str):
    line = clean_text(line)
    if not line:
        return None
    if line.startswith('Page ') or line.startswith('# CODE') or 'LISTE DES ECOLES' in line:
        return None
    if line.startswith('DIRECTION ') or 'MATERNELLE :' in line or 'PRIMAIRE :' in line:
        return None
    if re.match(r'^\d+\.\s+', line):
        return None

    m = re.match(r'^1\s+(\S+)\s+(.+)$', line)
    if not m:
        return None
    code, rest = m.group(1), m.group(2)

    m_num = re.search(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', rest)
    if not m_num:
        return None
    mat, prim, sec, effectifs = (int(m_num.group(i)) for i in range(1, 5))
    rest = rest[:m_num.start()].strip()

    # Agrément = dernier jeton (souvent null ou numéro)
    tokens = rest.split()
    if not tokens:
        return None
    agrement = tokens[-1]
    body = ' '.join(tokens[:-1]).strip()
    if is_null(agrement):
        agrement = ''
    elif not re.search(r'\d', agrement) and agrement.upper() not in ('MICROPLAN', 'MICROPLAN20', 'MICROPLAN2020', 'MICROPLAN2021', 'MICROPLAN2015', 'MICROPLAN2019', 'AUTORISA', 'MICRO'):
        # le dernier jeton fait partie du nom/adresse
        body = rest
        agrement = ''

    nom, adresse = split_nom_adresse(body)
    if is_null(adresse):
        adresse = 'Non renseignée'
    if not nom:
        nom = f'École {code}'

    return {
        'code': code[:30],
        'nom': nom[:200],
        'adresse': adresse[:255] or 'Non renseignée',
        'numero_agrement': agrement[:50],
        'type_ecole': type_ecole,
        'niveau': guess_niveau(nom, mat, prim, sec),
        'effectif_mat': mat,
        'effectif_prim': prim,
        'effectif_sec': sec,
        'effectifs': effectifs,
    }


class Command(BaseCommand):
    help = 'Importe les écoles Antenne Nsele 1 (Direction provinciale de Plateau)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(Path(__file__).resolve().parents[2] / 'data' / 'nsele1_ecoles.txt'),
            help='Fichier texte source',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Fichier introuvable: {path}'))
            return

        kin, _ = ProvinceAdministrative.objects.get_or_create(
            code='KIN', defaults={'nom': 'Kinshasa', 'actif': True},
        )
        pe, _ = ProvinceEducationnelle.objects.get_or_create(
            code='PE-PLT',
            defaults={
                'nom': 'Direction provinciale de Plateau',
                'province_administrative': kin,
                'actif': True,
            },
        )
        if pe.province_administrative_id != kin.id:
            pe.province_administrative = kin
            pe.nom = 'Direction provinciale de Plateau'
            pe.save()

        antenne, _ = Antenne.objects.get_or_create(
            code='ANT-NSELE1',
            defaults={
                'nom': 'Antenne de Nsele 1',
                'province_educationnelle': pe,
                'adresse': 'Nsele, Kinshasa',
                'actif': True,
            },
        )
        if antenne.province_educationnelle_id != pe.id:
            antenne.province_educationnelle = pe
            antenne.nom = 'Antenne de Nsele 1'
            antenne.save()

        type_ecole = Ecole.TypeEcole.PUBLIQUE
        created = updated = skipped = 0
        buffer = []

        def flush_buffer():
            nonlocal created, updated, skipped, buffer
            if not buffer:
                return
            line = ' '.join(buffer)
            buffer = []
            row = parse_school_line(line, type_ecole)
            if not row:
                skipped += 1
                return
            obj, was_created = Ecole.objects.update_or_create(
                code=row['code'],
                defaults={
                    'nom': row['nom'],
                    'adresse': row['adresse'],
                    'numero_agrement': row['numero_agrement'],
                    'type_ecole': row['type_ecole'],
                    'niveau': row['niveau'],
                    'effectif_mat': row['effectif_mat'],
                    'effectif_prim': row['effectif_prim'],
                    'effectif_sec': row['effectif_sec'],
                    'effectifs': row['effectifs'],
                    'province_educationnelle': pe,
                    'antenne': antenne,
                    'active': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
            line = raw.strip()
            if not line:
                flush_buffer()
                continue

            section = re.match(r'^(\d+)\.\s+(.+)$', line)
            if section:
                flush_buffer()
                title = clean_text(section.group(2)).upper()
                for key, value in SECTION_TYPES.items():
                    if title.startswith(key):
                        type_ecole = value
                        break
                continue

            # nouvelle ligne école
            if re.match(r'^1\s+\S+', line):
                flush_buffer()
                buffer = [line]
                # si la ligne contient déjà les 4 effectifs, on flush
                if re.search(r'\s+\d+\s+\d+\s+\d+\s+\d+\s*$', line):
                    flush_buffer()
                continue

            if buffer:
                buffer.append(line)
                joined = ' '.join(buffer)
                if re.search(r'\s+\d+\s+\d+\s+\d+\s+\d+\s*$', joined):
                    flush_buffer()

        flush_buffer()

        total = Ecole.objects.filter(antenne=antenne).count()
        self.stdout.write(self.style.SUCCESS(
            f'Import Nsele 1 terminé — créées: {created}, mises à jour: {updated}, '
            f'ignorées: {skipped}, total antenne: {total}'
        ))
