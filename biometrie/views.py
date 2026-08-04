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
    queryset = Biometrie.objects.select_related('eleve').all()
    serializer_class = BiometrieSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['eleve__matricule', 'eleve__nom']

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
