"""
Importer des élèves depuis un Excel (.xlsx) ou CSV.

Exemple :
  python manage.py import_eleves --file eleves.xlsx
  python manage.py import_eleves --file eleves/data/modele_import_eleves.csv --ecole-code 7-136755
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from eleves.import_utils import importer_eleves


class Command(BaseCommand):
    help = 'Importe des élèves depuis un fichier Excel ou CSV (matricule unique).'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Chemin du fichier .xlsx ou .csv')
        parser.add_argument('--ecole-code', default='', help='Code école par défaut si absent du fichier')
        parser.add_argument('--ecole-id', type=int, default=None, help='ID école par défaut')
        parser.add_argument(
            '--no-update',
            action='store_true',
            help='Ne pas mettre à jour les matricules déjà existants',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.is_file():
            raise CommandError(f'Fichier introuvable : {path}')

        contenu = path.read_bytes()
        try:
            result = importer_eleves(
                contenu,
                ecole_id=options.get('ecole_id'),
                ecole_code=options.get('ecole_code') or None,
                filename=path.name,
                update_existing=not options['no_update'],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Import terminé — {result['total']} ligne(s) : "
            f"{result['created']} créé(s), {result['updated']} mis à jour, "
            f"{result['skipped']} ignoré(s), {result['errors_count']} erreur(s)."
        ))
        for err in result['errors']:
            self.stdout.write(self.style.WARNING(
                f"  Ligne {err['ligne']} : {err['message']}"
            ))
