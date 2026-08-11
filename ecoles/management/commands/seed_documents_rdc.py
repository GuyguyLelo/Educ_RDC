"""
Commande : python manage.py seed_documents_rdc
Charge des documents de test basés sur des références publiques
de l'enseignement national en RDC (MINEDU-NC / EPSP).
"""
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from ecoles.models import Arrete


# Sources publiques (MINEDU-NC, presse, manuel officiel)
DOCUMENTS_TEST = [
    {
        'numero': 'LOI-CADRE/14/004/2014',
        'objet': "Loi-cadre n°14/004 portant organisation de l'enseignement national",
        'type_arrete': Arrete.TypeDocument.AUTRE,
        'date_arrete': date(2014, 2, 11),
        'signataire': 'Président de la République',
        'autorite': 'République Démocratique du Congo',
        'description': (
            'Cadre juridique de référence de l’enseignement national en RDC. '
            'Cité dans le Manuel de procédure de création et d’agrément des établissements '
            '(MINEDU-NC, 2025). Donnée de test / référentiel.'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'MINEDU-NC/CABMINETAT/004/2025',
        'objet': (
            'Arrêté ministériel relatif aux critères de création des établissements '
            'publics d’enseignement maternel, primaire et secondaire'
        ),
        'type_arrete': Arrete.TypeDocument.ARRETE,
        'date_arrete': date(2025, 3, 3),
        'signataire': 'Raissa Malu',
        'autorite': 'MINEDU-NC',
        'description': (
            'Arrêté ministériel n° MINEDU NC/CABMINETAT/004/2025 du 03/03/2025 — '
            'critères de création des établissements publics. Référence officielle '
            'du Manuel de procédure MINEDU-NC. Donnée de test.'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'MINEDU-NC/CABMINETAT/005/2025',
        'objet': (
            'Arrêté ministériel relatif à la procédure de création des établissements '
            'publics et des bureaux gestionnaires'
        ),
        'type_arrete': Arrete.TypeDocument.ARRETE,
        'date_arrete': date(2025, 3, 3),
        'signataire': 'Raissa Malu',
        'autorite': 'MINEDU-NC',
        'description': (
            'Arrêté ministériel n° MINEDU NC/CABMINETAT/005/2025 du 03/03/2025 — '
            'procédure de création / bureaux gestionnaires. Référence officielle '
            'du Manuel de procédure MINEDU-NC. Donnée de test.'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'MINEDU-NC/CABMIN/CARTE-SCOLAIRE/2025',
        'objet': (
            'Arrêté fixant les procédures d’octroi des décisions de création, '
            'd’agrément et de restructuration des établissements scolaires '
            '(carte scolaire nationale)'
        ),
        'type_arrete': Arrete.TypeDocument.ARRETE,
        'date_arrete': date(2025, 12, 30),
        'signataire': 'Raissa Malu',
        'autorite': 'MINEDU-NC',
        'description': (
            'Arrêté structurant signé par la Ministre d’État Raissa Malu '
            '(communiqué / presse, 30 déc. 2025) — cadre procédural unifié pour '
            'création, agrément et restructuration. Donnée de test (n° interne '
            'de démonstration).'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'MINEDU-NC/MANUEL/AGREMENT/2025',
        'objet': (
            'Manuel de procédure de création et d’agrément des établissements '
            'scolaires publics et privés'
        ),
        'type_arrete': Arrete.TypeDocument.AUTRE,
        'date_arrete': date(2025, 10, 16),
        'signataire': 'Raissa Malu',
        'autorite': 'MINEDU-NC',
        'description': (
            'Document officiel publié sur edu-nc.gouv.cd (16 oct. 2025). '
            'Source : https://edu-nc.gouv.cd/wp-content/uploads/2025/10/'
            'Manuel-de-procedures-Obtention-Des-Arretes-_-ii-1.pdf'
        ),
        'fichier_local': 'manuel_procedures_agrement_minedu_nc_2025.pdf',
    },
    {
        'numero': 'DEMO/AGR/EPSP/KIN/2024/001',
        'objet': "Décision d'agrément — École primaire de démonstration (Kinshasa)",
        'type_arrete': Arrete.TypeDocument.AGREMENT,
        'date_arrete': date(2024, 6, 15),
        'signataire': 'Secrétaire Général à l’Éducation Nationale',
        'autorite': 'MINEDU-NC / PROVED Kinshasa',
        'description': (
            'Document fictif de démonstration pour tester le rattachement '
            'école ↔ référentiel documentaire. Ne pas utiliser comme acte officiel.'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'DEMO/AUT/EPSP/LUB/2024/012',
        'objet': "Autorisation d'ouverture — Collège de démonstration (Lubumbashi)",
        'type_arrete': Arrete.TypeDocument.AUTORISATION,
        'date_arrete': date(2024, 8, 20),
        'signataire': 'PROVED Haut-Katanga',
        'autorite': 'PROVED Haut-Katanga',
        'description': (
            'Document fictif de démonstration (autorisation d’ouverture). '
            'Destiné aux tests de la gestion documentaire.'
        ),
        'fichier_local': None,
    },
    {
        'numero': 'DEMO/CONV/EPSP/GOM/2023/007',
        'objet': 'Convention de gestion — établissement conventionné (Goma)',
        'type_arrete': Arrete.TypeDocument.CONVENTION,
        'date_arrete': date(2023, 9, 1),
        'signataire': 'Coordonnateur national des écoles conventionnées',
        'autorite': 'EPSP / Église partenaire (démo)',
        'description': (
            'Document fictif de démonstration (convention). '
            'Pour tests UI / rattachement école.'
        ),
        'fichier_local': None,
    },
]


class Command(BaseCommand):
    help = 'Charge des documents RDC (référentiel) comme données de test'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-fichier',
            action='store_true',
            help='Réattache le PDF même si le document existe déjà',
        )

    def handle(self, *args, **options):
        media_dir = Path(settings.MEDIA_ROOT) / 'referentiel' / 'arretes'
        media_dir.mkdir(parents=True, exist_ok=True)
        created = updated = 0

        for spec in DOCUMENTS_TEST:
            obj, was_created = Arrete.objects.update_or_create(
                numero=spec['numero'],
                defaults={
                    'objet': spec['objet'],
                    'type_arrete': spec['type_arrete'],
                    'date_arrete': spec['date_arrete'],
                    'signataire': spec['signataire'],
                    'autorite': spec['autorite'],
                    'description': spec['description'],
                    'actif': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            local_name = spec.get('fichier_local')
            if local_name:
                local_path = media_dir / local_name
                if local_path.is_file() and (
                    options['force_fichier'] or not obj.fichier
                ):
                    with local_path.open('rb') as fh:
                        obj.fichier.save(local_name, File(fh), save=True)
                    self.stdout.write(f'  Fichier joint : {local_name}')

            self.stdout.write(
                f"  {'+' if was_created else '~'} {obj.numero} — {obj.get_type_arrete_display()}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Documents référentiel : {created} créé(s), {updated} mis à jour. '
                f'Total actifs : {Arrete.objects.filter(actif=True).count()}.'
            )
        )
