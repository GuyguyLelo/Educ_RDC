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
from .import_utils import importer_eleves
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
        'ecole',
        'ecole__province_educationnelle',
        'ecole__province_educationnelle__province_administrative',
        'ecole__antenne',
        'biometrie',
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
        if user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(ecole__province_educationnelle_id=user.province_educationnelle_id)
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

    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_fichier(self, request):
        """Importe des élèves depuis un CSV (champ fichier)."""
        fichier = request.FILES.get('fichier') or request.FILES.get('file')
        if not fichier:
            return Response(
                {'detail': 'Fichier CSV requis (champ « fichier »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = (fichier.name or '').lower()
        if name and not name.endswith(('.csv', '.txt', '.tsv')):
            return Response(
                {'detail': 'Format non supporté. Utilisez un fichier .csv ou .txt.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ecole_raw = request.data.get('ecole') or request.data.get('ecole_id')
        ecole_code = (request.data.get('ecole_code') or '').strip() or None
        ecole_id = None
        if ecole_raw not in (None, ''):
            try:
                ecole_id = int(ecole_raw)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'Identifiant école invalide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        update_existing = str(request.data.get('update_existing', '1')).lower() not in (
            '0', 'false', 'non', 'no',
        )

        try:
            result = importer_eleves(
                fichier.read(),
                ecole_id=ecole_id,
                ecole_code=ecole_code,
                update_existing=update_existing,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': (
                f"Import terminé : {result['created']} créé(s), "
                f"{result['updated']} mis à jour, "
                f"{result['skipped']} ignoré(s), "
                f"{result['errors_count']} erreur(s) "
                f"sur {result['total']} ligne(s)."
            ),
            **result,
        })
