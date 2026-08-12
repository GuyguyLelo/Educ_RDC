"""Vues API — Cartes scolaires."""
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from .models import Carte
from .serializers import CarteSerializer
from .services import generer_qr_code, generer_pdf_carte


class CarteViewSet(viewsets.ModelViewSet):
    queryset = Carte.objects.select_related('eleve', 'eleve__ecole').all()
    serializer_class = CarteSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['numero_carte', 'eleve__matricule', 'eleve__nom']
    ordering_fields = ['date_emission', 'numero_carte']

    def get_queryset(self):
        qs = super().get_queryset()
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        user = self.request.user
        # Enseignant : pas d'accès aux cartes scolaires
        if getattr(user, 'est_enseignant', False):
            return qs.none()
        if getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(eleve__ecole_id=user.ecole_id)
        elif user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(eleve__ecole__province_educationnelle_id=user.province_educationnelle_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        return qs

    def perform_create(self, serializer):
        carte = serializer.save()
        if not carte.qr_code:
            generer_qr_code(carte)
            carte.save(update_fields=['qr_code'])

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Export PDF de la carte scolaire."""
        carte = self.get_object()
        pdf_bytes = generer_pdf_carte(carte)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="carte_{carte.numero_carte}.pdf"'
        return response

    @action(detail=True, methods=['post'])
    def regenerer_qr(self, request, pk=None):
        carte = self.get_object()
        generer_qr_code(carte)
        carte.save(update_fields=['qr_code'])
        return Response(CarteSerializer(carte, context={'request': request}).data)
