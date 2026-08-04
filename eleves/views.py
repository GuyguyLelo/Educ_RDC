"""Vues API — Élèves."""
import hashlib
import uuid

from django.db.models import Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from biometrie.models import Biometrie
from enrolement.models import Enrolement
from cartes.models import Carte
from .models import Eleve
from .serializers import EleveSerializer, EleveDetailSerializer


def synchroniser_biometrie_photo(eleve):
    """Synchronise la photo de l'élève vers le dossier biométrie."""
    if not eleve.photo:
        return
    bio, _ = Biometrie.objects.get_or_create(
        eleve=eleve,
        defaults={'empreinte_hash': hashlib.sha256(uuid.uuid4().bytes).hexdigest()},
    )
    if not bio.photo or bio.photo.name != eleve.photo.name:
        bio.photo = eleve.photo
        bio.save(update_fields=['photo'])


class EleveViewSet(viewsets.ModelViewSet):
    queryset = Eleve.objects.select_related(
        'ecole', 'ecole__province', 'ecole__antenne', 'biometrie',
    ).prefetch_related(
        Prefetch('enrolements', queryset=Enrolement.objects.order_by('-date_enrolement')),
        Prefetch('cartes', queryset=Carte.objects.order_by('-date_emission')),
    ).all()
    serializer_class = EleveSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['matricule', 'nom', 'postnom', 'prenom', 'classe']
    ordering_fields = ['nom', 'date_inscription', 'matricule']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EleveDetailSerializer
        return EleveSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        ecole = self.request.query_params.get('ecole')
        q = self.request.query_params.get('q')
        if ecole:
            qs = qs.filter(ecole_id=ecole)
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(matricule__icontains=q)
                | Q(nom__icontains=q)
                | Q(postnom__icontains=q)
                | Q(prenom__icontains=q)
            )
        if user.role == 'agent_provincial' and user.province_id:
            qs = qs.filter(ecole__province_id=user.province_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(ecole__antenne_id=user.antenne_id)
        return qs

    def perform_create(self, serializer):
        eleve = serializer.save()
        synchroniser_biometrie_photo(eleve)

    def perform_update(self, serializer):
        eleve = serializer.save()
        synchroniser_biometrie_photo(eleve)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def photo(self, request, pk=None):
        """Upload / remplacement de la photo d'un élève."""
        eleve = self.get_object()
        fichier = request.FILES.get('photo')
        if not fichier:
            return Response(
                {'detail': 'Fichier photo requis (champ "photo").'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        eleve.photo = fichier
        eleve.save(update_fields=['photo', 'date_modification'])
        synchroniser_biometrie_photo(eleve)
        return Response(
            EleveDetailSerializer(eleve, context={'request': request}).data
        )
