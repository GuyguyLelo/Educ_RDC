"""Tests périmètre et droits d'écriture — agent province administrative."""
from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ecoles.models import (
    Antenne,
    Ecole,
    ProvinceAdministrative,
    ProvinceEducationnelle,
)
from eleves.models import Eleve
from utilisateurs.models import Utilisateur


class AgentProvinceAdminCrudTests(APITestCase):
    """L'agent PA consulte son territoire ; toute insertion métier est refusée."""

    @classmethod
    def setUpTestData(cls):
        cls.pa_kin = ProvinceAdministrative.objects.create(nom='Kinshasa', code='PA-KIN')
        cls.pa_kat = ProvinceAdministrative.objects.create(nom='Katanga', code='PA-KAT')
        cls.pe_kin = ProvinceEducationnelle.objects.create(
            nom='PE Kinshasa', code='PE-KIN', province_administrative=cls.pa_kin,
        )
        cls.pe_kat = ProvinceEducationnelle.objects.create(
            nom='PE Katanga', code='PE-KAT', province_administrative=cls.pa_kat,
        )
        cls.antenne_kin = Antenne.objects.create(
            nom='Antenne Kin', code='ANT-KIN', province_educationnelle=cls.pe_kin,
        )
        cls.ecole_kin = Ecole.objects.create(
            nom='Ecole Kin', code='EC-KIN-01', adresse='Av. Test',
            province_educationnelle=cls.pe_kin, antenne=cls.antenne_kin,
        )
        cls.eleve_kin = Eleve.objects.create(
            matricule='2026-0001', nom='Kabongo', prenom='Marie',
            date_naissance=date(2012, 3, 10), sexe=Eleve.Sexe.FEMININ, ecole=cls.ecole_kin,
        )
        cls.agent_pa = Utilisateur.objects.create_user(
            username='agent_pa_kin', password='MotDePasse123!',
            role=Utilisateur.Role.AGENT_PROVINCE_ADMIN,
            province_administrative=cls.pa_kin,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.agent_pa)

    def test_interdit_creation_province_educationnelle(self):
        res = self.client.post(
            reverse('province-educationnelle-list'),
            {'nom': 'PE X', 'code': 'PE-X', 'province_administrative': self.pa_kin.pk},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_interdit_creation_ecole(self):
        res = self.client.post(
            reverse('ecole-list'),
            {
                'nom': 'Nouvelle', 'code': 'EC-NEW', 'adresse': 'X',
                'province_educationnelle': self.pe_kin.pk, 'antenne': self.antenne_kin.pk,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_interdit_creation_eleve(self):
        res = self.client.post(
            reverse('eleve-list'),
            {
                'nom': 'Test', 'prenom': 'X', 'date_naissance': '2010-01-01',
                'sexe': 'M', 'ecole': self.ecole_kin.pk,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_lecture_ecoles_perimetre(self):
        res = self.client.get(reverse('ecole-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {row['id'] for row in res.data['results']}
        self.assertEqual(ids, {self.ecole_kin.pk})


class AdminEcoleSansCreationClassesTests(APITestCase):
    """L'admin école ne crée ni n'affecte la structure scolaire (classes)."""

    @classmethod
    def setUpTestData(cls):
        cls.pa = ProvinceAdministrative.objects.create(nom='Kinshasa', code='PA-AE')
        cls.pe = ProvinceEducationnelle.objects.create(
            nom='PE Kin', code='PE-AE', province_administrative=cls.pa,
        )
        cls.antenne = Antenne.objects.create(
            nom='Antenne AE', code='ANT-AE', province_educationnelle=cls.pe,
        )
        cls.ecole = Ecole.objects.create(
            nom='Ecole AE', code='EC-AE-01', adresse='Av. AE',
            province_educationnelle=cls.pe, antenne=cls.antenne,
        )
        cls.admin_ecole = Utilisateur.objects.create_user(
            username='admin_ecole_ae', password='MotDePasse123!',
            role=Utilisateur.Role.ADMIN_ECOLE, ecole=cls.ecole,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.admin_ecole)

    def test_interdit_creation_classe(self):
        res = self.client.post(
            reverse('classe-list'),
            {'nom': '6e A', 'ecole': self.ecole.pk, 'code': '6A'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_interdit_affecter_structure(self):
        url = reverse('ecole-affecter-structure', args=[self.ecole.pk])
        res = self.client.post(url, {'options': ['COUPE'], 'niveau': 'tous'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_lecture_classes_autorisee(self):
        res = self.client.get(reverse('classe-list'), {'ecole': self.ecole.pk})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
