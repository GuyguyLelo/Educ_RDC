"""Vues API — Structures hiérarchiques et écoles."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from .models import (
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
    PersonnelEcole,
)
from .serializers import (
    ProvinceAdministrativeSerializer,
    ProvinceEducationnelleSerializer,
    AntenneSerializer,
    EcoleSerializer,
    PersonnelEcoleSerializer,
)


class ProvinceAdministrativeViewSet(viewsets.ModelViewSet):
    queryset = ProvinceAdministrative.objects.all()
    serializer_class = ProvinceAdministrativeSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom', 'code']


class ProvinceEducationnelleViewSet(viewsets.ModelViewSet):
    queryset = ProvinceEducationnelle.objects.select_related('province_administrative').all()
    serializer_class = ProvinceEducationnelleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        pa = self.request.query_params.get('province_administrative')
        if pa:
            qs = qs.filter(province_administrative_id=pa)
        return qs


class AntenneViewSet(viewsets.ModelViewSet):
    queryset = Antenne.objects.select_related(
        'province_educationnelle',
        'province_educationnelle__province_administrative',
    ).all()
    serializer_class = AntenneSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom']

    def get_queryset(self):
        qs = super().get_queryset()
        pe = self.request.query_params.get('province_educationnelle')
        pa = self.request.query_params.get('province_administrative')
        # Alias historique
        province = self.request.query_params.get('province')
        if pe:
            qs = qs.filter(province_educationnelle_id=pe)
        if pa:
            qs = qs.filter(province_educationnelle__province_administrative_id=pa)
        if province and not pe:
            qs = qs.filter(province_educationnelle_id=province)
        return qs


class EcoleViewSet(viewsets.ModelViewSet):
    queryset = Ecole.objects.select_related(
        'province_educationnelle',
        'province_educationnelle__province_administrative',
        'antenne',
    ).all()
    serializer_class = EcoleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code', 'numero_agrement', 'directeur', 'adresse']
    ordering_fields = ['nom', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        pe = self.request.query_params.get('province_educationnelle')
        pa = self.request.query_params.get('province_administrative')
        antenne = self.request.query_params.get('antenne')
        province = self.request.query_params.get('province')
        if pe:
            qs = qs.filter(province_educationnelle_id=pe)
        if pa:
            qs = qs.filter(province_educationnelle__province_administrative_id=pa)
        if province and not pe:
            qs = qs.filter(province_educationnelle_id=province)
        if antenne:
            qs = qs.filter(antenne_id=antenne)
        type_ecole = self.request.query_params.get('type_ecole')
        niveau = self.request.query_params.get('niveau')
        active = self.request.query_params.get('active')
        if type_ecole:
            qs = qs.filter(type_ecole=type_ecole)
        if niveau:
            qs = qs.filter(niveau=niveau)
        if active in ('true', '1', 'True'):
            qs = qs.filter(active=True)
        elif active in ('false', '0', 'False'):
            qs = qs.filter(active=False)
        if user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(province_educationnelle_id=user.province_educationnelle_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(antenne_id=user.antenne_id)
        return qs


class PersonnelEcoleViewSet(viewsets.ModelViewSet):
    queryset = PersonnelEcole.objects.select_related('ecole').all()
    serializer_class = PersonnelEcoleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'postnom', 'prenom', 'matricule', 'telephone']
    ordering_fields = ['nom', 'fonction', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        ecole = self.request.query_params.get('ecole')
        fonction = self.request.query_params.get('fonction')
        actif = self.request.query_params.get('actif')
        if ecole:
            qs = qs.filter(ecole_id=ecole)
        if fonction:
            qs = qs.filter(fonction=fonction)
        if actif in ('true', '1', 'True'):
            qs = qs.filter(actif=True)
        elif actif in ('false', '0', 'False'):
            qs = qs.filter(actif=False)
        return qs
