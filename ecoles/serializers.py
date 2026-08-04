"""Serializers écoles / provinces / antennes."""
from rest_framework import serializers
from .models import Province, Antenne, Ecole


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id', 'nom', 'code', 'date_creation']


class AntenneSerializer(serializers.ModelSerializer):
    province_nom = serializers.CharField(source='province.nom', read_only=True)

    class Meta:
        model = Antenne
        fields = [
            'id', 'nom', 'code', 'province', 'province_nom',
            'adresse', 'telephone', 'date_creation',
        ]


class EcoleSerializer(serializers.ModelSerializer):
    province_nom = serializers.CharField(source='province.nom', read_only=True)
    antenne_nom = serializers.CharField(source='antenne.nom', read_only=True)
    type_display = serializers.CharField(source='get_type_ecole_display', read_only=True)
    niveau_display = serializers.CharField(source='get_niveau_display', read_only=True)
    nombre_eleves = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ecole
        fields = [
            'id', 'nom', 'code', 'type_ecole', 'type_display', 'niveau',
            'niveau_display', 'adresse', 'telephone', 'email', 'directeur',
            'province', 'province_nom', 'antenne', 'antenne_nom',
            'active', 'nombre_eleves', 'date_creation',
        ]
