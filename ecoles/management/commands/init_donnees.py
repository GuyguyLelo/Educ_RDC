"""
Commande : python manage.py init_donnees
Initialise la hiérarchie référentielle et les données démo.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from ecoles.models import (
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
)
from eleves.models import Eleve


class Command(BaseCommand):
    help = 'Initialise les données de démonstration Educ_RDC'

    def handle(self, *args, **options):
        User = get_user_model()

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

        provinces_admin = [
            ('Kinshasa', 'KIN'),
            ('Kongo Central', 'KOC'),
            ('Haut-Katanga', 'HKA'),
            ('Nord-Kivu', 'NKI'),
            ('Sud-Kivu', 'SKI'),
            ('Kasaï Oriental', 'KAO'),
        ]
        for nom, code in provinces_admin:
            ProvinceAdministrative.objects.get_or_create(
                code=code, defaults={'nom': nom},
            )

        kin = ProvinceAdministrative.objects.get(code='KIN')
        hka = ProvinceAdministrative.objects.get(code='HKA')
        nki = ProvinceAdministrative.objects.get(code='NKI')

        # Une province éducationnelle par province administrative (démo)
        pe_data = [
            ('PE Kinshasa', 'PE-KIN', kin),
            ('PE Haut-Katanga', 'PE-HKA', hka),
            ('PE Nord-Kivu', 'PE-NKI', nki),
        ]
        for nom, code, pa in pe_data:
            ProvinceEducationnelle.objects.get_or_create(
                code=code,
                defaults={'nom': nom, 'province_administrative': pa},
            )

        pe_kin = ProvinceEducationnelle.objects.get(code='PE-KIN')
        pe_hka = ProvinceEducationnelle.objects.get(code='PE-HKA')
        pe_nki = ProvinceEducationnelle.objects.get(code='PE-NKI')

        antennes_data = [
            ('Antenne Gombe', 'ANT-GOM', pe_kin, 'Avenue du Port, Gombe'),
            ('Antenne Lemba', 'ANT-LEM', pe_kin, 'Commune de Lemba'),
            ('Antenne Lubumbashi', 'ANT-LUB', pe_hka, 'Lubumbashi Centre'),
            ('Antenne Goma', 'ANT-GOM2', pe_nki, 'Goma Ville'),
        ]
        for nom, code, pe, adr in antennes_data:
            Antenne.objects.get_or_create(
                code=code,
                defaults={
                    'nom': nom,
                    'province_educationnelle': pe,
                    'adresse': adr,
                    'telephone': '+243800000000',
                },
            )

        ant_gombe = Antenne.objects.get(code='ANT-GOM')
        ant_lemba = Antenne.objects.get(code='ANT-LEM')
        ant_lub = Antenne.objects.get(code='ANT-LUB')

        ecoles_data = [
            ('EP Boyoma', 'ECO-KIN-001', 'publique', 'primaire', pe_kin, ant_gombe, 'Av. Tombalbaye'),
            ('Complexe Scolaire Matonge', 'ECO-KIN-002', 'conventionnee', 'mixte', pe_kin, ant_lemba, 'Matonge'),
            ('Lycée Kitumaini', 'ECO-HKA-001', 'publique', 'secondaire', pe_hka, ant_lub, 'Lubumbashi'),
        ]
        for nom, code, typ, niv, pe, ant, adr in ecoles_data:
            Ecole.objects.get_or_create(
                code=code,
                defaults={
                    'nom': nom,
                    'type_ecole': typ,
                    'niveau': niv,
                    'province_educationnelle': pe,
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

        if not User.objects.filter(username='agent_kin').exists():
            User.objects.create_user(
                username='agent_kin',
                password='agent123',
                first_name='Agent',
                last_name='Kinshasa',
                role='agent_provincial',
                province_administrative=kin,
                province_educationnelle=pe_kin,
            )

        self.stdout.write(self.style.SUCCESS('Données de démonstration initialisées.'))
