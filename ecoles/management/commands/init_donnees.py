"""
Commande : python manage.py init_donnees
Initialise provinces, antennes, écoles démo et compte admin.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from ecoles.models import Province, Antenne, Ecole
from eleves.models import Eleve


class Command(BaseCommand):
    help = 'Initialise les données de démonstration Educ_RDC'

    def handle(self, *args, **options):
        User = get_user_model()

        # Superutilisateur / admin
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@educrdc.cd',
                password='admin123',
                first_name='Admin',
                last_name='National',
                role='admin',
            )
            self.stdout.write(self.style.SUCCESS(f'Admin créé : admin / admin123 ({admin})'))
        else:
            self.stdout.write('Admin déjà existant.')

        provinces_data = [
            ('Kinshasa', 'KIN'),
            ('Kongo Central', 'KOC'),
            ('Haut-Katanga', 'HKA'),
            ('Nord-Kivu', 'NKI'),
            ('Sud-Kivu', 'SKI'),
            ('Kasaï Oriental', 'KAO'),
        ]

        for nom, code in provinces_data:
            Province.objects.get_or_create(code=code, defaults={'nom': nom})

        kin = Province.objects.get(code='KIN')
        hka = Province.objects.get(code='HKA')
        nki = Province.objects.get(code='NKI')

        antennes_data = [
            ('Antenne Gombe', 'ANT-GOM', kin, 'Avenue du Port, Gombe'),
            ('Antenne Lemba', 'ANT-LEM', kin, 'Commune de Lemba'),
            ('Antenne Lubumbashi', 'ANT-LUB', hka, 'Lubumbashi Centre'),
            ('Antenne Goma', 'ANT-GOM2', nki, 'Goma Ville'),
        ]

        for nom, code, prov, adr in antennes_data:
            Antenne.objects.get_or_create(
                code=code,
                defaults={'nom': nom, 'province': prov, 'adresse': adr, 'telephone': '+243800000000'},
            )

        ant_gombe = Antenne.objects.get(code='ANT-GOM')
        ant_lemba = Antenne.objects.get(code='ANT-LEM')
        ant_lub = Antenne.objects.get(code='ANT-LUB')

        ecoles_data = [
            ('EP Boyoma', 'ECO-KIN-001', 'publique', 'primaire', kin, ant_gombe, 'Av. Tombalbaye'),
            ('Complexe Scolaire Matonge', 'ECO-KIN-002', 'conventionnee', 'mixte', kin, ant_lemba, 'Matonge'),
            ('Lycée Kitumaini', 'ECO-HKA-001', 'publique', 'secondaire', hka, ant_lub, 'Lubumbashi'),
        ]

        for nom, code, typ, niv, prov, ant, adr in ecoles_data:
            Ecole.objects.get_or_create(
                code=code,
                defaults={
                    'nom': nom,
                    'type_ecole': typ,
                    'niveau': niv,
                    'province': prov,
                    'antenne': ant,
                    'adresse': adr,
                    'directeur': 'Directeur Démo',
                    'telephone': '+243900000000',
                },
            )

        ecole = Ecole.objects.get(code='ECO-KIN-001')
        eleves_demo = [
            ('ELV-2026-001', 'Kabila', 'Joseph', 'Patrick', '2014-03-12', 'M', '5ème primaire'),
            ('ELV-2026-002', 'Mwanza', 'Marie', 'Grace', '2015-07-21', 'F', '4ème primaire'),
            ('ELV-2026-003', 'Tshisekedi', 'Jean', 'Luc', '2013-11-05', 'M', '6ème primaire'),
        ]
        for mat, nom, postnom, prenom, dnaiss, sexe, classe in eleves_demo:
            Eleve.objects.get_or_create(
                matricule=mat,
                defaults={
                    'nom': nom,
                    'postnom': postnom,
                    'prenom': prenom,
                    'date_naissance': dnaiss,
                    'sexe': sexe,
                    'ecole': ecole,
                    'classe': classe,
                    'lieu_naissance': 'Kinshasa',
                    'nom_tuteur': 'Tuteur Démo',
                    'telephone_tuteur': '+243810000000',
                },
            )

        # Agents démo
        if not User.objects.filter(username='agent_kin').exists():
            User.objects.create_user(
                username='agent_kin',
                password='agent123',
                first_name='Agent',
                last_name='Kinshasa',
                role='agent_provincial',
                province=kin,
            )

        self.stdout.write(self.style.SUCCESS('Données de démonstration initialisées.'))
