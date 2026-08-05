"""Vues API — Structures hiérarchiques et écoles."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utilisateurs.permissions import LecturePourTousEcritureAdmin, GestionClassesEcole
from .models import (
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
    Classe,
    PhotoEcole,
    PersonnelEcole,
)
from .import_personnel import importer_personnel, reponse_modele_xlsx
from .import_classes import importer_classes, reponse_modele_xlsx as reponse_modele_classes
from administration.import_modeles import reponse_modele as reponse_modele_catalogue
from .serializers import (
    ProvinceAdministrativeSerializer,
    ProvinceEducationnelleSerializer,
    AntenneSerializer,
    EcoleSerializer,
    ClasseSerializer,
    PhotoEcoleSerializer,
    PersonnelEcoleSerializer,
)


class ProvinceAdministrativeViewSet(viewsets.ModelViewSet):
    queryset = ProvinceAdministrative.objects.all()
    serializer_class = ProvinceAdministrativeSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom', 'code']


class ProvinceEducationnelleViewSet(viewsets.ModelViewSet):
    queryset = ProvinceEducationnelle.objects.select_related('province_administrative').all()
    serializer_class = ProvinceEducationnelleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        pa = self.request.query_params.get('province_administrative')
        if pa:
            qs = qs.filter(province_administrative_id=pa)
        return qs


class AntenneViewSet(viewsets.ModelViewSet):
    queryset = Antenne.objects.select_related(
        'province_educationnelle',
        'province_educationnelle__province_administrative',
    ).all()
    serializer_class = AntenneSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    search_fields = ['nom', 'code']
    ordering_fields = ['nom']

    def get_queryset(self):
        qs = super().get_queryset()
        pe = self.request.query_params.get('province_educationnelle')
        pa = self.request.query_params.get('province_administrative')
        # Alias historique
        province = self.request.query_params.get('province')
        if pe:
            qs = qs.filter(province_educationnelle_id=pe)
        if pa:
            qs = qs.filter(province_educationnelle__province_administrative_id=pa)
        if province and not pe:
            qs = qs.filter(province_educationnelle_id=province)
        return qs


class EcoleViewSet(viewsets.ModelViewSet):
    queryset = Ecole.objects.select_related(
        'province_educationnelle',
        'province_educationnelle__province_administrative',
        'antenne',
    ).prefetch_related('photos').all()
    serializer_class = EcoleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['nom', 'code', 'numero_agrement', 'directeur', 'adresse', 'email']
    ordering_fields = ['nom', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        pe = self.request.query_params.get('province_educationnelle')
        pa = self.request.query_params.get('province_administrative')
        antenne = self.request.query_params.get('antenne')
        province = self.request.query_params.get('province')
        if pe:
            qs = qs.filter(province_educationnelle_id=pe)
        if pa:
            qs = qs.filter(province_educationnelle__province_administrative_id=pa)
        if province and not pe:
            qs = qs.filter(province_educationnelle_id=province)
        if antenne:
            qs = qs.filter(antenne_id=antenne)
        type_ecole = self.request.query_params.get('type_ecole')
        niveau = self.request.query_params.get('niveau')
        active = self.request.query_params.get('active')
        if type_ecole:
            qs = qs.filter(type_ecole=type_ecole)
        if niveau:
            qs = qs.filter(niveau=niveau)
        if active in ('true', '1', 'True'):
            qs = qs.filter(active=True)
        elif active in ('false', '0', 'False'):
            qs = qs.filter(active=False)
        if user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(province_educationnelle_id=user.province_educationnelle_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(antenne_id=user.antenne_id)
        elif getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(id=user.ecole_id)
        return qs

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def photos(self, request, pk=None):
        """Liste ou ajout de photos pour une école."""
        ecole = self.get_object()
        if request.method == 'GET':
            ser = PhotoEcoleSerializer(
                ecole.photos.all(), many=True, context={'request': request},
            )
            return Response(ser.data)

        images = []
        for key in ('image', 'images', 'photo', 'photos'):
            images.extend(request.FILES.getlist(key))
        # Dédupliquer par identité d'objet fichier
        seen = set()
        unique_images = []
        for img in images:
            marker = id(img)
            if marker in seen:
                continue
            seen.add(marker)
            if img and getattr(img, 'size', 0):
                unique_images.append(img)
        images = unique_images

        if not images:
            return Response(
                {'detail': 'Fichier image requis (champ « image »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for image in images:
            content_type = (getattr(image, 'content_type', '') or '').lower()
            if content_type and not content_type.startswith('image/'):
                return Response(
                    {'detail': f'« {image.name} » n\'est pas une image valide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        legende = (request.data.get('legende') or '').strip()
        est_principale = str(request.data.get('est_principale', '0')).lower() in (
            '1', 'true', 'oui', 'yes', 'on',
        )
        had_photos = ecole.photos.exists()
        created = []
        try:
            for index, image in enumerate(images):
                # Première image principale si demandé, ou si aucune photo n'existait
                make_main = (est_principale and index == 0) or (not had_photos and index == 0)
                photo = PhotoEcole.objects.create(
                    ecole=ecole,
                    image=image,
                    legende=legende if len(images) == 1 else (
                        f'{legende} ({index + 1})' if legende else ''
                    ),
                    est_principale=make_main,
                )
                created.append(photo)
                if make_main:
                    had_photos = True
        except Exception as exc:
            return Response(
                {'detail': f'Impossible d\'enregistrer la photo : {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PhotoEcoleSerializer(
            created, many=True, context={'request': request},
        )
        return Response(
            {
                'detail': (
                    f'{len(created)} photo{"s" if len(created) > 1 else ""} ajoutée'
                    f'{"s" if len(created) > 1 else ""}.'
                ),
                'count': len(created),
                'photos': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'photos/(?P<photo_id>[^/.]+)',
    )
    def supprimer_photo(self, request, pk=None, photo_id=None):
        """Supprime une photo d'école."""
        ecole = self.get_object()
        photo = ecole.photos.filter(pk=photo_id).first()
        if not photo:
            return Response({'detail': 'Photo introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        was_main = photo.est_principale
        photo.image.delete(save=False)
        photo.delete()
        if was_main:
            next_photo = ecole.photos.first()
            if next_photo:
                next_photo.est_principale = True
                next_photo.save(update_fields=['est_principale'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='modele-import')
    def modele_import(self, request):
        """Télécharge le modèle Excel d'import des écoles."""
        return reponse_modele_catalogue('ecoles')


class ClasseViewSet(viewsets.ModelViewSet):
    """Classes scolaires — créées par l'administratif de l'école."""

    queryset = Classe.objects.select_related('ecole').all()
    serializer_class = ClasseSerializer
    permission_classes = [IsAuthenticated, GestionClassesEcole]
    search_fields = ['nom', 'code', 'ecole__nom', 'ecole__code']
    ordering_fields = ['nom', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        ecole = self.request.query_params.get('ecole')
        actif = self.request.query_params.get('actif') or self.request.query_params.get('active')
        if ecole:
            qs = qs.filter(ecole_id=ecole)
        if actif in ('true', '1', 'True'):
            qs = qs.filter(active=True)
        elif actif in ('false', '0', 'False'):
            qs = qs.filter(active=False)
        if getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(ecole_id=user.ecole_id)
        elif user.role == 'agent_antenne' and user.antenne_id:
            qs = qs.filter(ecole__antenne_id=user.antenne_id)
        elif user.role == 'agent_provincial' and user.province_educationnelle_id:
            qs = qs.filter(ecole__province_educationnelle_id=user.province_educationnelle_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        ecole = serializer.validated_data.get('ecole')
        if user.role == 'admin_ecole' and user.ecole_id:
            if ecole and ecole.id != user.ecole_id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous ne pouvez créer des classes que pour votre école.")
            serializer.save(ecole_id=user.ecole_id)
        else:
            serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == 'admin_ecole' and user.ecole_id:
            instance = self.get_object()
            if instance.ecole_id != user.ecole_id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous ne pouvez modifier que les classes de votre école.")
            serializer.save(ecole_id=user.ecole_id)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='modele-import')
    def modele_import(self, request):
        """Télécharge le modèle Excel d'import des classes."""
        return reponse_modele_classes()

    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_fichier(self, request):
        """Importe des classes depuis Excel (.xlsx) ou CSV."""
        fichier = request.FILES.get('fichier') or request.FILES.get('file')
        if not fichier:
            return Response(
                {'detail': 'Fichier Excel requis (champ « fichier »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (fichier.name or '').lower()
        if name and not name.endswith(('.xlsx', '.xlsm', '.csv', '.txt')):
            return Response(
                {'detail': 'Format non supporté. Utilisez un fichier .xlsx ou .csv.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ecole_raw = request.data.get('ecole') or request.data.get('ecole_id')
        ecole_id = None
        if ecole_raw not in (None, ''):
            try:
                ecole_id = int(ecole_raw)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'Identifiant école invalide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user = request.user
        if user.role == 'admin_ecole' and user.ecole_id:
            ecole_id = user.ecole_id

        update_existing = str(request.data.get('update_existing', '1')).lower() not in (
            '0', 'false', 'non', 'no',
        )
        try:
            result = importer_classes(
                fichier.read(),
                ecole_id=ecole_id,
                ecole_code=request.data.get('ecole_code') or None,
                filename=fichier.name or '',
                update_existing=update_existing,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': (
                f"Import classes terminé : {result['created']} créée(s), "
                f"{result['updated']} mise(s) à jour, "
                f"{result['skipped']} ignorée(s), "
                f"{result['errors_count']} erreur(s) "
                f"sur {result['total']} ligne(s)."
            ),
            **result,
        })


class PersonnelEcoleViewSet(viewsets.ModelViewSet):
    queryset = PersonnelEcole.objects.select_related('ecole').all()
    serializer_class = PersonnelEcoleSerializer
    permission_classes = [IsAuthenticated, LecturePourTousEcritureAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['nom', 'postnom', 'prenom', 'matricule', 'telephone']
    ordering_fields = ['nom', 'fonction', 'date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        ecole = self.request.query_params.get('ecole')
        fonction = self.request.query_params.get('fonction')
        actif = self.request.query_params.get('actif')
        if ecole:
            qs = qs.filter(ecole_id=ecole)
        if fonction:
            qs = qs.filter(fonction=fonction)
        if actif in ('true', '1', 'True'):
            qs = qs.filter(actif=True)
        elif actif in ('false', '0', 'False'):
            qs = qs.filter(actif=False)
        if getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
            qs = qs.filter(ecole_id=user.ecole_id)
        return qs

    @action(detail=False, methods=['get'], url_path='modele-import')
    def modele_import(self, request):
        """Télécharge le modèle Excel d'import du personnel."""
        return reponse_modele_xlsx()

    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_fichier(self, request):
        """Importe le personnel depuis un fichier Excel (.xlsx) ou CSV."""
        fichier = request.FILES.get('fichier') or request.FILES.get('file')
        if not fichier:
            return Response(
                {'detail': 'Fichier Excel requis (champ « fichier »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = (fichier.name or '').lower()
        if name and not name.endswith(('.xlsx', '.xlsm', '.csv', '.txt')):
            return Response(
                {'detail': 'Format non supporté. Utilisez un fichier .xlsx ou .csv.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ecole_raw = request.data.get('ecole') or request.data.get('ecole_id')
        if ecole_raw in (None, ''):
            return Response(
                {'detail': 'École requise (champ « ecole »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            result = importer_personnel(
                fichier.read(),
                ecole_id=ecole_id,
                filename=fichier.name or '',
                update_existing=update_existing,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': (
                f"Import terminé pour « {result['ecole_nom']} » : "
                f"{result['created']} créé(s), "
                f"{result['updated']} mis à jour, "
                f"{result['skipped']} ignoré(s), "
                f"{result['errors_count']} erreur(s) "
                f"sur {result['total']} ligne(s)."
            ),
            **result,
        })
