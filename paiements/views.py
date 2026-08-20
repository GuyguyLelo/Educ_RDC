"""Vues API — Paiements."""
import uuid

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import GestionPaiements
from .models import Paiement
from .serializers import PaiementSerializer


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.select_related('eleve', 'agent').all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated, GestionPaiements]
    search_fields = ['reference', 'eleve__matricule', 'eleve__nom']
    ordering_fields = ['date_paiement', 'montant']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.est_national:
            return qs
        if user.role == 'admin_ecole' and user.ecole_id:
            return qs.filter(eleve__ecole_id=user.ecole_id)
        if user.role == 'agent_province_admin' and user.province_administrative_id:
            return qs.filter(
                eleve__ecole__province_educationnelle__province_administrative_id=(
                    user.province_administrative_id
                ),
            )
        if user.role == 'agent_provincial' and user.province_educationnelle_id:
            return qs.filter(
                eleve__ecole__province_educationnelle_id=user.province_educationnelle_id,
            )
        if user.role == 'agent_antenne' and user.antenne_id:
            return qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        eleve = serializer.validated_data.get('eleve')
        if user.role == 'admin_ecole' and user.ecole_id and eleve:
            if eleve.ecole_id != user.ecole_id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Élève hors de votre établissement.')
        reference = serializer.validated_data.get('reference')
        if not reference:
            reference = f'PAY-{uuid.uuid4().hex[:10].upper()}'
        serializer.save(agent=self.request.user, reference=reference)
