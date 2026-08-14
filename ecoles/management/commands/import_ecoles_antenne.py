"""
Import générique d'une liste d'écoles par antenne.

Exemples :
  python manage.py import_ecoles_antenne --file ecoles/data/nsele1_ecoles.txt \\
      --pe-code PE-PLT --pe-nom "Direction provinciale de Plateau" \\
      --antenne-code ANT-NSELE1 --antenne-nom "Antenne de Nsele 1"

  python manage.py import_ecoles_antenne --file ecoles/data/mont_ngafula2_ecoles.txt \\
      --pe-code PE-LKG --pe-nom "Direction provinciale de Lukunga" \\
      --antenne-code ANT-MN2 --antenne-nom "Antenne de Mont-Ngafula 2"
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
    'CONVENTIONNE FRATERNITE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE ISLAMIQUE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE KIMBANGUISTE': Ecole.TypeEcole.CONVENTIONNEE,
    'CONVENTIONNE PROTESTANTE': Ecole.TypeEcole.CONVENTIONNEE,
    'PRIVE AGREE': Ecole.TypeEcole.PRIVEE,
    'SALUTISTE': Ecole.TypeEcole.CONVENTIONNEE,
    'E.R.C': Ecole.TypeEcole.CONVENTIONNEE,
    'ADVENTISTE': Ecole.TypeEcole.CONVENTIONNEE,
}

NULLISH = {'null', 'nulle', 'none', '-', '', '-0', 'n ull', 'ull'}
CODE_RE = re.compile(r'^(\d+-\d+|\d{8,})$')
ADDR_START = re.compile(
    r'(?i)(?<![A-Z0-9])(AV\.?|AVE\.?|AVENUE|CAMP|Q/|QUARTIER|VILLAGE|ILE|BLV\.?|BLD\.?|'
    r'BOULEVARD|CIMETIERE|REF\.?|OCC/|VA\.|RTE |ROUTE |LOCALITE |CITE |TEMPLE |'
    r'KIPOYI|IFENGE|DIABENA|KANDE|HABACUC|MBAKALA|MALENGI|MBANZA|BUDJA|'
    r'TUWISANA|TSINASAMBA|ARUIMI|BULUNGU|NSINGI|KITENGE|TELECOM|PEM?BLE|'
    r'MALANGU|LIFOBO|KALEMBA|MAYILO|MUSENDI|MUSANGU|BAS CONGO|ARUIMI|'
    r'MAKUTA|MAMAN KATE|LUPINI|KIBASA|MONGENGA|DES AVEUGLES|MITENDI|'
    r'KIMVULA|MBENSEKE|SANS[- ]?FIL|SAY[A]|MATADI)\b',
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
    text = text.replace('FRANÃ‡OIS', 'FRANCOIS').replace('PÃˆRE', 'PERE')
    text = text.replace('Ã‰TOILES', 'ETOILES').replace('CÅ’UR', 'COEUR')
    text = text.replace('ChrÃ©tienne', 'Chretienne')
    # null collé au texte
    text = re.sub(r'([A-Za-z0-9/°])null\b', r'\1 null', text, flags=re.I)
    text = re.sub(r'([A-Za-z0-9/°])NULL\b', r'\1 NULL', text)
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
    if n.startswith('EP ') or n.startswith('E.P') or n.startswith('ECOLE PRIMAIRE'):
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
        'IT ', 'I.T', 'ITAC', 'ITP', 'ITI', 'ITIP', 'COLLEGE', 'COL ', 'COL.',
        'CRS ', 'COMPLEXE', 'ACADEMIE',
    )):
        return Ecole.Niveau.SECONDAIRE
    if n.startswith('CS ') or n.startswith('C.S') or n.startswith('GS ') or n.startswith('G.S'):
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

    # "1 CODE ..." ou "CODE ..." (après rupture de page)
    m = re.match(r'^(?:1\s+)?(\S+)\s+(.+)$', line)
    if not m:
        return None
    code, rest = m.group(1), m.group(2)
    if not CODE_RE.match(code):
        return None

    # normaliser fins du type "-0 0 0 0"
    rest = re.sub(r'\s+-0\s+(\d+)\s+(\d+)\s+(\d+)\s*$', r' null 0 \1 \2 \3', rest)
    rest = re.sub(r'\s+--\s+(\d+)\s+(\d+)\s+(\d+)\s*$', r' null 0 \1 \2 \3', rest)

    m_num = re.search(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', rest)
    if not m_num:
        return None
    mat, prim, sec, effectifs = (int(m_num.group(i)) for i in range(1, 5))
    rest = rest[:m_num.start()].strip()

    tokens = rest.split()
    if not tokens:
        return None
    agrement = tokens[-1]
    body = ' '.join(tokens[:-1]).strip()
    micro_ok = agrement.upper().startswith('MICRO') or agrement.upper() in {
        'AUTORGE', 'AUTORISA', 'MICROPLAN',
    }
    if is_null(agrement):
        agrement = ''
    elif not re.search(r'\d', agrement) and not micro_ok:
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


def normalize_source_text(text: str) -> str:
    """Découpe un blob collé en lignes école + sections."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'Page\s+\d+/\d+', '\n', text, flags=re.I)
    text = re.sub(r'_{5,}', '\n', text)
    # Sections "N. TITRE"
    text = re.sub(r'(?=\d+\.\s+(?:NON CONVENTIONNE|CONVENTIONNE|PRIVE|SALUTISTE|E\.R\.C|ADVENTISTE))', '\n', text, flags=re.I)
    text = re.sub(r'#\s*CODE ECOLE[^\n]*', '\n', text, flags=re.I)
    # Écoles : "1 CODE" ou CODE collé après page
    text = re.sub(r'(?<!\d)(1\s+)(\d+-\d+|\d{8,})\s+', r'\n1 \2 ', text)
    text = re.sub(r'(?<=\n|\s)(?<!1 )(\d+-\d+|\d{8,})\s+', r'\n1 \1 ', text)
    text = re.sub(r'([A-Za-z0-9/°])null\b', r'\1 null', text, flags=re.I)
    return text


class Command(BaseCommand):
    help = 'Importe une liste d\'écoles pour une antenne (fichier texte)'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Fichier texte source')
        parser.add_argument('--pe-code', required=True, help='Code province éducationnelle')
        parser.add_argument('--pe-nom', required=True, help='Nom province éducationnelle')
        parser.add_argument('--antenne-code', required=True, help='Code antenne')
        parser.add_argument('--antenne-nom', required=True, help='Nom antenne')
        parser.add_argument('--pa-code', default='KIN', help='Code province administrative')
        parser.add_argument('--pa-nom', default='Kinshasa', help='Nom province administrative')
        parser.add_argument('--normalize', action='store_true', help='Normaliser un blob collé')

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Fichier introuvable: {path}'))
            return

        raw = path.read_text(encoding='utf-8', errors='replace')
        if options['normalize'] or '\n' not in raw.strip()[:200] or raw.count('\n') < 20:
            raw = normalize_source_text(raw)

        kin, _ = ProvinceAdministrative.objects.get_or_create(
            code=options['pa_code'],
            defaults={'nom': options['pa_nom'], 'actif': True},
        )
        pe, _ = ProvinceEducationnelle.objects.get_or_create(
            code=options['pe_code'],
            defaults={
                'nom': options['pe_nom'],
                'province_administrative': kin,
                'actif': True,
            },
        )
        if pe.nom != options['pe_nom'] or pe.province_administrative_id != kin.id:
            pe.nom = options['pe_nom']
            pe.province_administrative = kin
            pe.save()

        antenne, _ = Antenne.objects.get_or_create(
            code=options['antenne_code'],
            defaults={
                'nom': options['antenne_nom'],
                'province_educationnelle': pe,
                'adresse': options['antenne_nom'],
                'actif': True,
            },
        )
        if antenne.nom != options['antenne_nom'] or antenne.province_educationnelle_id != pe.id:
            antenne.nom = options['antenne_nom']
            antenne.province_educationnelle = pe
            antenne.save()

        type_ecole = Ecole.TypeEcole.PUBLIQUE
        created = updated = skipped = 0

        for raw_line in raw.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            section = re.match(r'^(\d+)\.\s+(.+)$', line)
            if section:
                title = clean_text(section.group(2)).upper()
                for key, value in SECTION_TYPES.items():
                    if title.startswith(key):
                        type_ecole = value
                        break
                continue

            # ignorer faux positifs (noms de personnes sans code école)
            if re.match(r'^1\s+[A-Z]', line) and not re.search(r'\d+-\d+|\d{8,}', line):
                skipped += 1
                continue

            row = parse_school_line(line, type_ecole)
            if not row:
                skipped += 1
                continue

            _, was_created = Ecole.objects.update_or_create(
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

        total = Ecole.objects.filter(antenne=antenne).count()
        self.stdout.write(self.style.SUCCESS(
            f'Import {options["antenne_nom"]} — créées: {created}, mises à jour: {updated}, '
            f'ignorées: {skipped}, total antenne: {total}'
        ))
