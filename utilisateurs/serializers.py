"""Serializers utilisateurs."""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'telephone',
            'province_administrative', 'province_educationnelle', 'antenne',
            'is_active', 'date_creation',
        ]
        read_only_fields = ['date_creation']


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'telephone',
            'province_administrative', 'province_educationnelle', 'antenne',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user
