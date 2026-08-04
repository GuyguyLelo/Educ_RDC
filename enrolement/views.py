"""Vues API — Enrôlement."""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from cartes.services import creer_carte_depuis_enrolement
from .models import Enrolement
from .serializers import EnrolementSerializer


class EnrolementViewSet(viewsets.ModelViewSet):
    queryset = Enrolement.objects.select_related('eleve', 'agent', 'eleve__ecole').all()
    serializer_class = EnrolementSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['eleve__matricule', 'eleve__nom', 'annee_scolaire']
    ordering_fields = ['date_enrolement', 'statut']

    def get_queryset(self):
        qs = super().get_queryset()
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        user = self.request.user
        if user.role == 'agent_provincial' and user.province_id:
            qs = qs.filter(eleve__ecole__province_id=user.province_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """Valide l'enrôlement et génère automatiquement la carte."""
        enr = self.get_object()
        if enr.statut == Enrolement.Statut.VALIDE:
            return Response({'detail': 'Déjà validé.'}, status=status.HTTP_400_BAD_REQUEST)

        # Vérifier biométrie
        bio = getattr(enr.eleve, 'biometrie', None)
        if not bio or not bio.photo:
            return Response(
                {'detail': 'Biométrie (photo) requise avant validation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enr.statut = Enrolement.Statut.VALIDE
        enr.date_validation = timezone.now()
        enr.save()

        if bio and not bio.validee:
            bio.validee = True
            bio.save(update_fields=['validee'])

        carte = creer_carte_depuis_enrolement(enr)
        return Response({
            'enrolement': EnrolementSerializer(enr).data,
            'carte_id': carte.id,
            'numero_carte': carte.numero_carte,
            'detail': 'Enrôlement validé et carte générée.',
        })

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        enr = self.get_object()
        enr.statut = Enrolement.Statut.REJETE
        enr.observations = request.data.get('observations', enr.observations)
        enr.date_validation = timezone.now()
        enr.save()
        return Response(EnrolementSerializer(enr).data)
