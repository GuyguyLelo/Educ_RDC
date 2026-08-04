"""Vues API et authentification — Utilisateurs."""
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Utilisateur
from .serializers import UtilisateurSerializer, UtilisateurCreateSerializer
from .permissions import EstAdmin


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT enrichi avec infos utilisateur."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UtilisateurSerializer(self.user).data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.select_related(
        'province_administrative',
        'province_educationnelle',
        'antenne',
    ).all()
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'telephone']
    ordering_fields = ['username', 'date_creation', 'role']

    def get_serializer_class(self):
        if self.action == 'create':
            return UtilisateurCreateSerializer
        return UtilisateurSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [EstAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        q = self.request.query_params.get('q')
        actif = self.request.query_params.get('actif')
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def moi(self, request):
        return Response(UtilisateurSerializer(request.user).data)
