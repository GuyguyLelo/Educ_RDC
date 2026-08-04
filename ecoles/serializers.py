"""Serializers écoles / structures hiérarchiques."""
from rest_framework import serializers
from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
    PersonnelEcole,
)


class StructureOrganisationnelleSerializer(serializers.ModelSerializer):
    type_structure = serializers.CharField(read_only=True)

    class Meta:
        model = StructureOrganisationnelle
        fields = [
            'id', 'nom', 'code', 'actif', 'type_structure',
            'date_creation', 'date_modification',
        ]


class ProvinceAdministrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProvinceAdministrative
        fields = [
            'id', 'nom', 'code', 'actif',
            'date_creation', 'date_modification',
        ]
        read_only_fields = ['date_creation', 'date_modification']
        extra_kwargs = {
            'code': {'validators': []},
        }

    def validate_code(self, value):
        code = (value or '').strip().upper()
        if not code:
            raise serializers.ValidationError('Le code est obligatoire.')
        qs = StructureOrganisationnelle.objects.filter(code__iexact=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Ce code est déjà utilisé par une autre structure (PA, PE ou antenne).'
            )
        return code

    def create(self, validated_data):
        validated_data['code'] = validated_data['code'].strip().upper()
        return ProvinceAdministrative.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if 'code' in validated_data:
            validated_data['code'] = validated_data['code'].strip().upper()
        return super().update(instance, validated_data)


class ProvinceEducationnelleSerializer(serializers.ModelSerializer):
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )

    class Meta:
        model = ProvinceEducationnelle
        fields = [
            'id', 'nom', 'code', 'actif',
            'province_administrative', 'province_administrative_nom',
            'date_creation', 'date_modification',
        ]


class AntenneSerializer(serializers.ModelSerializer):
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True,
    )
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )
    province_administrative_id = serializers.IntegerField(
        source='province_administrative.id', read_only=True,
    )

    class Meta:
        model = Antenne
        fields = [
            'id', 'nom', 'code', 'actif',
            'province_educationnelle', 'province_educationnelle_nom',
            'province_administrative_id', 'province_administrative_nom',
            'adresse', 'telephone',
            'date_creation', 'date_modification',
        ]


class EcoleSerializer(serializers.ModelSerializer):
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True,
    )
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )
    antenne_nom = serializers.CharField(source='antenne.nom', read_only=True)
    type_display = serializers.CharField(source='get_type_ecole_display', read_only=True)
    niveau_display = serializers.CharField(source='get_niveau_display', read_only=True)
    nombre_eleves = serializers.IntegerField(read_only=True)
    nombre_personnels = serializers.IntegerField(read_only=True)
    # Alias pour compatibilité frontend
    province_nom = serializers.CharField(source='province_educationnelle.nom', read_only=True)
    province = serializers.IntegerField(source='province_educationnelle_id', read_only=True)

    class Meta:
        model = Ecole
        fields = [
            'id', 'nom', 'code', 'numero_agrement', 'type_ecole', 'type_display', 'niveau',
            'niveau_display', 'adresse', 'telephone', 'email', 'directeur',
            'effectif_mat', 'effectif_prim', 'effectif_sec', 'effectifs',
            'province_educationnelle', 'province_educationnelle_nom',
            'province_administrative_nom', 'province', 'province_nom',
            'antenne', 'antenne_nom',
            'active', 'nombre_eleves', 'nombre_personnels', 'date_creation',
        ]


class PersonnelEcoleSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    fonction_display = serializers.CharField(source='get_fonction_display', read_only=True)
    sexe_display = serializers.CharField(source='get_sexe_display', read_only=True)
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    ecole_code = serializers.CharField(source='ecole.code', read_only=True)

    class Meta:
        model = PersonnelEcole
        fields = [
            'id', 'ecole', 'ecole_nom', 'ecole_code',
            'matricule', 'nom', 'postnom', 'prenom', 'nom_complet',
            'sexe', 'sexe_display', 'fonction', 'fonction_display',
            'telephone', 'email', 'date_naissance', 'date_prise_service',
            'actif', 'date_creation',
        ]
