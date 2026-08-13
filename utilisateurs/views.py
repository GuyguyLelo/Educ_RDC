"""Vues API et authentification — Utilisateurs."""
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Utilisateur
from .serializers import (
    ChangerMotDePasseSerializer,
    ProfilSerializer,
    UtilisateurSerializer,
    UtilisateurCreateSerializer,
)
from .permissions import GestionUtilisateurs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT enrichi avec infos utilisateur."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        if user.ecole_id:
            token['ecole_id'] = user.ecole_id
        if user.classe_id:
            token['classe_id'] = user.classe_id
            token['classe'] = user.classe.nom
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        request = self.context.get('request')
        data['user'] = UtilisateurSerializer(
            self.user, context={'request': request},
        ).data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.select_related(
        'province_administrative',
        'province_educationnelle',
        'antenne',
        'ecole',
        'classe',
        'classe__section',
        'classe__option',
    ).all()
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'telephone']
    ordering_fields = ['username', 'date_creation', 'role']

    ROLES_ECOLE = Utilisateur.ROLES_ECOLE

    def get_serializer_class(self):
        if self.action == 'create':
            return UtilisateurCreateSerializer
        return UtilisateurSerializer

    def get_permissions(self):
        if self.action in ('moi', 'changer_mot_de_passe', 'photo'):
            return [IsAuthenticated()]
        return [GestionUtilisateurs()]

    def _est_admin_global(self):
        user = self.request.user
        return bool(user.est_admin or user.is_superuser)

    def _est_admin_ecole(self):
        user = self.request.user
        return (
            not self._est_admin_global()
            and user.role == Utilisateur.Role.ADMIN_ECOLE
            and bool(user.ecole_id)
        )

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        role = self.request.query_params.get('role')
        ecole = self.request.query_params.get('ecole')
        q = self.request.query_params.get('q')
        actif = self.request.query_params.get('actif')

        if self._est_admin_ecole():
            qs = qs.filter(ecole_id=user.ecole_id, role__in=self.ROLES_ECOLE)
        else:
            if ecole:
                qs = qs.filter(ecole_id=ecole)
            elif self.action == 'list':
                # Liste nationale : enseignants gérés depuis la fiche école
                # (ne pas exclure sur retrieve/update/delete — sinon PATCH 404)
                if role != Utilisateur.Role.ENSEIGNANT:
                    qs = qs.exclude(role=Utilisateur.Role.ENSEIGNANT)

        if role:
            qs = qs.filter(role=role)
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(telephone__icontains=q)
            )
        if actif in ('1', 'true', 'True'):
            qs = qs.filter(is_active=True)
        elif actif in ('0', 'false', 'False'):
            qs = qs.filter(is_active=False)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if self._est_admin_ecole():
            # Injection école côté serveur (ignore toute autre école envoyée)
            mutable = data.copy() if hasattr(data, 'copy') else dict(data)
            mutable['ecole'] = request.user.ecole_id
            role = mutable.get('role')
            if role not in self.ROLES_ECOLE:
                raise ValidationError({
                    'role': "Rôle non autorisé. Utilisez administratif école ou enseignant.",
                })
            if role != Utilisateur.Role.ENSEIGNANT:
                mutable['classe'] = None
            serializer = self.get_serializer(data=mutable)
        else:
            serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        if self._est_admin_ecole():
            # Double contrôle objet école
            ecole = serializer.validated_data.get('ecole')
            if not ecole or ecole.id != request.user.ecole_id:
                raise PermissionDenied("Vous ne pouvez créer des comptes que pour votre école.")
        self.perform_create(serializer)
        self._sync_personnel(serializer.instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if self._est_admin_ecole():
            if instance.ecole_id != request.user.ecole_id:
                raise PermissionDenied("Compte hors de votre école.")
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data['ecole'] = request.user.ecole_id
            role = data.get('role', instance.role)
            if role not in self.ROLES_ECOLE:
                raise ValidationError({
                    'role': "Rôle non autorisé pour un compte école.",
                })
            if role != Utilisateur.Role.ENSEIGNANT:
                data['classe'] = None
            serializer = self.get_serializer(instance, data=data, partial=partial)
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self._sync_personnel(serializer.instance)
        return Response(serializer.data)

    def _sync_personnel(self, user):
        """Alimente la fiche Personnel pour les enseignants créés/modifiés."""
        try:
            from ecoles.services_personnel import synchroniser_personnel_depuis_utilisateur
            synchroniser_personnel_depuis_utilisateur(user)
        except Exception:
            # Ne bloque pas la création du compte si la synchro échoue
            pass

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            raise ValidationError({'detail': 'Vous ne pouvez pas supprimer votre propre compte.'})
        if self._est_admin_ecole() and instance.ecole_id != request.user.ecole_id:
            raise PermissionDenied("Compte hors de votre école.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def moi(self, request):
        """Profil de l'utilisateur connecté (lecture / mise à jour limitée)."""
        user = request.user
        if request.method == 'GET':
            return Response(
                UtilisateurSerializer(user, context={'request': request}).data
            )
        serializer = ProfilSerializer(
            user, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UtilisateurSerializer(user, context={'request': request}).data
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='changer-mot-de-passe',
        permission_classes=[IsAuthenticated],
    )
    def changer_mot_de_passe(self, request):
        serializer = ChangerMotDePasseSerializer(
            data=request.data, context={'user': request.user},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['nouveau_mot_de_passe'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe mis à jour.'})

    @action(
        detail=False,
        methods=['post'],
        url_path='photo',
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def photo(self, request):
        """Upload / remplacement de la photo de profil."""
        fichier = request.FILES.get('photo')
        if not fichier:
            return Response(
                {'detail': 'Fichier photo requis (champ « photo »).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        if user.photo:
            user.photo.delete(save=False)
        user.photo = fichier
        user.save(update_fields=['photo'])
        return Response(
            UtilisateurSerializer(user, context={'request': request}).data
        )
