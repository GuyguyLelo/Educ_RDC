"""Charge sections / options / classes du programme EPSP RDC pour une école."""
from django.core.management.base import BaseCommand, CommandError

from ecoles.models import Ecole
from ecoles.programme_rdc import charger_programme_rdc


class Command(BaseCommand):
    help = (
        'Charge le référentiel sections/options/classes (programme RDC EPSP). '
        'Par défaut : options sélectionnées (--options). '
        'Utilisez --tout uniquement pour installer l\'intégralité du niveau.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--ecole', type=int, help='ID de l\'école')
        parser.add_argument('--code', type=str, help='Code de l\'école')
        parser.add_argument(
            '--niveau',
            choices=['creche', 'maternelle', 'prescolaire', 'primaire', 'secondaire', 'tous'],
            default='tous',
            help='Niveau à charger (défaut: tous ; prescolaire = crèche + maternelle)',
        )
        parser.add_argument(
            '--options',
            type=str,
            help='Codes options séparés par des virgules (ex: COUPE,MP,TC-CTEB)',
        )
        parser.add_argument(
            '--sections',
            type=str,
            help='Codes sections séparés par des virgules (ex: CTEB,SC)',
        )
        parser.add_argument(
            '--tout',
            action='store_true',
            help='Charger TOUTES les options du niveau (non recommandé)',
        )
        parser.add_argument(
            '--toutes',
            action='store_true',
            help='Appliquer à toutes les écoles actives',
        )

    def handle(self, *args, **options):
        niveau = options['niveau']
        opt_codes = [
            c.strip() for c in (options.get('options') or '').split(',') if c.strip()
        ]
        sec_codes = [
            c.strip() for c in (options.get('sections') or '').split(',') if c.strip()
        ]
        tout = options['tout']
        if not tout and not opt_codes and not sec_codes:
            raise CommandError(
                'Indiquez --options COUPE,MP (ou --sections CTEB) '
                'ou --tout pour l\'intégralité.'
            )

        if options['toutes']:
            ecoles = Ecole.objects.filter(active=True)
        elif options['ecole']:
            ecoles = Ecole.objects.filter(pk=options['ecole'])
        elif options['code']:
            ecoles = Ecole.objects.filter(code=options['code'])
        else:
            raise CommandError('Indiquez --ecole, --code ou --toutes.')

        if not ecoles.exists():
            raise CommandError('Aucune école trouvée.')

        for ecole in ecoles:
            n = niveau
            if niveau == 'tous':
                if ecole.niveau == Ecole.Niveau.CRECHE:
                    n = 'creche'
                elif ecole.niveau == Ecole.Niveau.MATERNELLE:
                    n = 'prescolaire'
                elif ecole.niveau == Ecole.Niveau.PRIMAIRE:
                    n = 'primaire'
                elif ecole.niveau == Ecole.Niveau.SECONDAIRE:
                    n = 'secondaire'
            stats = charger_programme_rdc(
                ecole.id,
                niveau=n,
                option_codes=opt_codes,
                section_codes=sec_codes,
                tout=tout,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'{ecole.code}: +{stats["sections_created"]} sec, '
                    f'+{stats["options_created"]} opt, '
                    f'+{stats["classes_created"]} classes ({n})'
                )
            )
