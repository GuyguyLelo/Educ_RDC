"""Serializers cartes scolaires."""
from rest_framework import serializers
from .models import Carte


class CarteSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)
    eleve_matricule = serializers.CharField(source='eleve.matricule', read_only=True)
    ecole_nom = serializers.CharField(source='eleve.ecole.nom', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Carte
        fields = [
            'id', 'eleve', 'eleve_nom', 'eleve_matricule', 'ecole_nom',
            'enrolement', 'numero_carte', 'date_emission', 'date_expiration',
            'qr_code', 'qr_code_url', 'statut', 'statut_display',
        ]
        read_only_fields = ['numero_carte', 'date_emission', 'qr_code']

    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        if obj.qr_code and request:
            return request.build_absolute_uri(obj.qr_code.url)
        if obj.qr_code:
            return obj.qr_code.url
        return None
