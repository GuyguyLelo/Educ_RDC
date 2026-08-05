"""Serializers utilisateurs."""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur


def _valider_rattachement_scolaire(attrs, instance=None):
    role = attrs.get('role', getattr(instance, 'role', None))
    ecole = attrs.get('ecole', getattr(instance, 'ecole', None))
    classe = attrs.get('classe', getattr(instance, 'classe', None) if instance else None)
    if role in Utilisateur.ROLES_ECOLE and not ecole:
        raise serializers.ValidationError({
            'ecole': "L'école est obligatoire pour un administratif ou un enseignant.",
        })
    if role == Utilisateur.Role.ENSEIGNANT:
        if not classe:
            raise serializers.ValidationError({
                'classe': "Sélectionnez la classe dont l'enseignant est titulaire.",
            })
        if ecole and classe.ecole_id != ecole.id:
            raise serializers.ValidationError({
                'classe': "La classe doit appartenir à l'école sélectionnée.",
            })
    return attrs


class UtilisateurSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True, allow_null=True, default=None,
    )
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True, allow_null=True, default=None,
    )
    antenne_nom = serializers.CharField(
        source='antenne.nom', read_only=True, allow_null=True, default=None,
    )
    ecole_nom = serializers.CharField(
        source='ecole.nom', read_only=True, allow_null=True, default=None,
    )
    ecole_code = serializers.CharField(
        source='ecole.code', read_only=True, allow_null=True, default=None,
    )
    classe_nom = serializers.CharField(
        source='classe.nom', read_only=True, allow_null=True, default=None,
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'telephone',
            'province_administrative', 'province_administrative_nom',
            'province_educationnelle', 'province_educationnelle_nom',
            'antenne', 'antenne_nom',
            'ecole', 'ecole_nom', 'ecole_code',
            'classe', 'classe_nom',
            'is_active', 'date_creation', 'password',
        ]
        read_only_fields = ['date_creation', 'classe_nom']

    def validate(self, attrs):
        return _valider_rattachement_scolaire(attrs, self.instance)

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'telephone',
            'province_administrative', 'province_educationnelle', 'antenne',
            'ecole', 'classe', 'is_active',
        ]

    def validate(self, attrs):
        return _valider_rattachement_scolaire(attrs)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user
