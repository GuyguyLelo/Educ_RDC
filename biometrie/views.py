"""Vues API — Biométrie."""
import hashlib
import uuid

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from .models import Biometrie
from .serializers import BiometrieSerializer


class BiometrieViewSet(viewsets.ModelViewSet):
    queryset = Biometrie.objects.select_related('eleve', 'eleve__ecole').all()
    serializer_class = BiometrieSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['eleve__matricule', 'eleve__nom']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'est_enseignant', False):
            if not user.classe_id:
                return qs.none()
            qs = qs.filter(eleve__classe_id=user.classe_id)
            if user.ecole_id:
                qs = qs.filter(eleve__ecole_id=user.ecole_id)
        elif getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(eleve__ecole_id=user.ecole_id)
        elif user.role == 'agent_province_admin' and user.province_administrative_id:
            qs = qs.filter(
                eleve__ecole__province_educationnelle__province_administrative_id=(
                    user.province_administrative_id
                ),
            )
        elif user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(eleve__ecole__province_educationnelle_id=user.province_educationnelle_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        return qs

    def perform_create(self, serializer):
        # Simulation d'empreinte si non fournie
        empreinte = serializer.validated_data.get('empreinte_hash')
        if not empreinte:
            empreinte = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        serializer.save(empreinte_hash=empreinte)

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        bio = self.get_object()
        bio.validee = True
        bio.save(update_fields=['validee'])
        return Response(BiometrieSerializer(bio, context={'request': request}).data)
