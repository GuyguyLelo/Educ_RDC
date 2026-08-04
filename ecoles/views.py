"""Vues API — Écoles, Provinces, Antennes."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from .models import Province, Antenne, Ecole
from .serializers import ProvinceSerializer, AntenneSerializer, EcoleSerializer


class ProvinceViewSet(viewsets.ModelViewSet):
    queryset = Province.objects.all()
    serializer_class = ProvinceSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom', 'code']


class AntenneViewSet(viewsets.ModelViewSet):
    queryset = Antenne.objects.select_related('province').all()
    serializer_class = AntenneSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    filterset_fields = ['province']
    ordering_fields = ['nom']

    def get_queryset(self):
        qs = super().get_queryset()
        province = self.request.query_params.get('province')
        if province:
            qs = qs.filter(province_id=province)
        return qs


class EcoleViewSet(viewsets.ModelViewSet):
    queryset = Ecole.objects.select_related('province', 'antenne').all()
    serializer_class = EcoleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code', 'directeur', 'adresse']
    ordering_fields = ['nom', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        province = self.request.query_params.get('province')
        antenne = self.request.query_params.get('antenne')
        if province:
            qs = qs.filter(province_id=province)
        if antenne:
            qs = qs.filter(antenne_id=antenne)
        # Filtrage par rôle
        if user.role == 'agent_provincial' and user.province_id:
            qs = qs.filter(province_id=user.province_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(antenne_id=user.antenne_id)
        return qs
