"""Vues API — Paiements."""
import uuid

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from .models import Paiement
from .serializers import PaiementSerializer


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.select_related('eleve', 'agent').all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['reference', 'eleve__matricule', 'eleve__nom']
    ordering_fields = ['date_paiement', 'montant']

    def perform_create(self, serializer):
        reference = serializer.validated_data.get('reference')
        if not reference:
            reference = f'PAY-{uuid.uuid4().hex[:10].upper()}'
        serializer.save(agent=self.request.user, reference=reference)
