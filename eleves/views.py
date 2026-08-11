"""Vues API — Élèves."""
import hashlib
import uuid

from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utilisateurs.permissions import LecturePourTousEcritureAdmin
from biometrie.models import Biometrie
from cartes.models import Carte
from .models import Eleve
from .import_utils import importer_eleves, reponse_modele_xlsx
from .pdf_fiche import generer_pdf_fiche_eleve
from .serializers import EleveSerializer, EleveDetailSerializer
from .services import assurer_qr_eleve, generer_prochain_matricule, generer_qr_eleve


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
        'classe',
        'classe__option',
        'classe__section',
    ).all()
    serializer_class = EleveSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = [
        'matricule', 'numero_identification', 'numero_permanent', 'numero_impot',
        'nom', 'postnom', 'prenom', 'classe__nom',
        'nom_pere', 'nom_mere', 'nom_tuteur',
        'telephone_pere', 'telephone_mere', 'telephone_tuteur',
    ]
    ordering_fields = ['nom', 'date_inscription', 'matricule']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EleveDetailSerializer
        return EleveSerializer

    def get_queryset(self):
        qs = Eleve.objects.select_related(
            'ecole',
            'ecole__province_educationnelle',
            'ecole__province_educationnelle__province_administrative',
            'ecole__antenne',
            'classe',
            'classe__option',
            'classe__section',
        )
        # Détail : charger biométrie + cartes ; liste : allégé
        if getattr(self, 'action', None) == 'retrieve':
            qs = qs.select_related('biometrie').prefetch_related(
                Prefetch('cartes', queryset=Carte.objects.order_by('-date_emission')),
            )
        qs = qs.all()
        user = self.request.user
        ecole = self.request.query_params.get('ecole')
        classe = self.request.query_params.get('classe')
        q = self.request.query_params.get('q')

        # Périmètre par rôle (appliqué avant les filtres UI)
        if getattr(user, 'est_enseignant', False):
            # Un enseignant ne voit que les élèves de sa classe titulaire
            if not user.classe_id:
                return qs.none()
            qs = qs.filter(classe_id=user.classe_id)
            if user.ecole_id:
                qs = qs.filter(ecole_id=user.ecole_id)
        elif user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(ecole__province_educationnelle_id=user.province_educationnelle_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(ecole__antenne_id=user.antenne_id)
        elif getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(ecole_id=user.ecole_id)
        elif user.ecole_id and not (
            getattr(user, 'est_admin', False) or getattr(user, 'est_national', False)
        ):
            # Sécurité : tout compte rattaché à une école reste borné
            qs = qs.filter(ecole_id=user.ecole_id)

        # Filtre école UI — un utilisateur école ne peut pas élargir hors de son établissement
        ecole_figee = (
            getattr(user, 'est_utilisateur_ecole', False)
            or (
                bool(user.ecole_id)
                and not (getattr(user, 'est_admin', False) or getattr(user, 'est_national', False))
            )
        )
        if ecole_figee and user.ecole_id:
            qs = qs.filter(ecole_id=user.ecole_id)
        elif ecole and not getattr(user, 'est_enseignant', False):
            qs = qs.filter(ecole_id=ecole)

        if classe and not getattr(user, 'est_enseignant', False):
            qs = qs.filter(classe_id=classe)
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(matricule__icontains=q)
                | Q(numero_identification__icontains=q)
                | Q(numero_permanent__icontains=q)
                | Q(numero_impot__icontains=q)
                | Q(nom__icontains=q)
                | Q(postnom__icontains=q)
                | Q(prenom__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        from django.db import transaction
        with transaction.atomic():
            # Matricule toujours attribué côté serveur (AAAA-0001)
            serializer.validated_data['matricule'] = generer_prochain_matricule()
            eleve = serializer.save()
            synchroniser_biometrie_photo(eleve)
            assurer_qr_eleve(eleve)

    @action(detail=False, methods=['get'], url_path='prochain-matricule')
    def prochain_matricule(self, request):
        """Retourne le prochain matricule (AAAA-0001)."""
        from .services import annee_pour_matricule, ordre_depuis_matricule
        matricule = generer_prochain_matricule()
        return Response({
            'matricule': matricule,
            'annee': annee_pour_matricule(),
            'ordre': ordre_depuis_matricule(matricule),
        })

    def perform_update(self, serializer):
        eleve = serializer.save()
        synchroniser_biometrie_photo(eleve)
        assurer_qr_eleve(eleve)

    def retrieve(self, request, *args, **kwargs):
        eleve = self.get_object()
        assurer_qr_eleve(eleve)
        serializer = self.get_serializer(eleve)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """Télécharge la fiche élève en PDF."""
        eleve = self.get_object()
        assurer_qr_eleve(eleve)
        pdf = generer_pdf_fiche_eleve(eleve)
        filename = f'fiche_eleve_{eleve.matricule}.pdf'.replace('/', '-')
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path='regenerer-qr')
    def regenerer_qr(self, request, pk=None):
        """Régénère le QR code unique de l'élève."""
        eleve = self.get_object()
        assurer_qr_eleve(eleve)
        generer_qr_eleve(eleve, force=True)
        eleve.refresh_from_db()
        return Response(EleveDetailSerializer(eleve, context={'request': request}).data)

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
        detail=True,
        methods=['post'],
        url_path='photo-parent',
        parser_classes=[MultiPartParser, FormParser],
    )
    def photo_parent(self, request, pk=None):
        """Upload / remplacement de la photo du père, de la mère ou du tuteur."""
        eleve = self.get_object()
        role = (request.data.get('role') or '').strip().lower()
        field_map = {
            'pere': 'photo_pere',
            'mere': 'photo_mere',
            'tuteur': 'photo_tuteur',
        }
        field = field_map.get(role)
        if not field:
            return Response(
                {'detail': 'Rôle invalide. Utilisez pere, mere ou tuteur.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fichier = request.FILES.get('photo') or request.FILES.get(field)
        if not fichier:
            return Response(
                {'detail': 'Fichier photo requis (champ "photo").'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        setattr(eleve, field, fichier)
        eleve.save(update_fields=[field, 'date_modification'])
        return Response(
            EleveDetailSerializer(eleve, context={'request': request}).data
        )

    @action(detail=False, methods=['get'], url_path='modele-import')
    def modele_import(self, request):
        """Télécharge le modèle Excel d'import des élèves."""
        return reponse_modele_xlsx()

    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_fichier(self, request):
        """Importe des élèves depuis un Excel (.xlsx) ou CSV."""
        fichier = request.FILES.get('fichier') or request.FILES.get('file')
        if not fichier:
            return Response(
                {'detail': 'Fichier Excel ou CSV requis (champ « fichier »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = (fichier.name or '').lower()
        if name and not name.endswith(('.xlsx', '.xlsm', '.csv', '.txt', '.tsv')):
            return Response(
                {'detail': 'Format non supporté. Utilisez un fichier .xlsx ou .csv.'},
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
                filename=fichier.name or '',
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
