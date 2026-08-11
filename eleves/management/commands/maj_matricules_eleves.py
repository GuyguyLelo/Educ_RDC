"""
Réattribue les matricules élèves au format AAAA-0001
et recalcule les numéros d'identification (code école + ordre).

  python manage.py maj_matricules_eleves
  python manage.py maj_matricules_eleves --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from eleves.models import Eleve
from eleves.services import (
    annee_pour_matricule,
    composer_matricule,
    composer_numero_identification,
    generer_qr_eleve,
)


class Command(BaseCommand):
    help = 'Met à jour les matricules élèves au format AAAA-0001'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les changements sans les enregistrer',
        )
        parser.add_argument(
            '--annee',
            type=int,
            default=None,
            help='Année forcée (sinon année scolaire active / année civile)',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        annee = options['annee'] or annee_pour_matricule()
        eleves = list(
            Eleve.objects.select_related('ecole')
            .order_by('date_inscription', 'id')
        )
        if not eleves:
            self.stdout.write('Aucun élève à traiter.')
            return

        plan = []
        for i, eleve in enumerate(eleves, start=1):
            nouveau_mat = composer_matricule(annee, i)
            code = eleve.ecole.code if eleve.ecole_id else None
            nouveau_nid = composer_numero_identification(code, nouveau_mat)
            plan.append((eleve, nouveau_mat, nouveau_nid))
            self.stdout.write(
                f'  {eleve.matricule} -> {nouveau_mat}'
                f' | NID {eleve.numero_identification or "-"} -> {nouveau_nid or "-"}'
                f' ({eleve.nom_complet})'
            )

        if dry:
            self.stdout.write(self.style.WARNING(
                f'Dry-run : {len(plan)} élève(s), année {annee} — aucune écriture.'
            ))
            return

        with transaction.atomic():
            # Phase 1 : valeurs temporaires (évite collisions unique)
            for idx, (eleve, _, _) in enumerate(plan):
                Eleve.objects.filter(pk=eleve.pk).update(
                    matricule=f'__TMP_MAT_{eleve.pk}_{idx}',
                    numero_identification=f'__TMP_NID_{eleve.pk}_{idx}',
                )

            # Phase 2 : format définitif AAAA-0001
            for eleve, nouveau_mat, nouveau_nid in plan:
                Eleve.objects.filter(pk=eleve.pk).update(
                    matricule=nouveau_mat,
                    numero_identification=nouveau_nid,
                )

        # Régénérer les QR (contenu lié au matricule)
        regeneres = 0
        for eleve, _, _ in plan:
            eleve.refresh_from_db()
            if generer_qr_eleve(eleve, force=True):
                regeneres += 1

        self.stdout.write(self.style.SUCCESS(
            f'{len(plan)} matricule(s) mis à jour (année {annee}), '
            f'{regeneres} QR régénéré(s).'
        ))
