"""Serializers paiements."""
from rest_framework import serializers
from .models import Paiement


class PaiementSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)
    type_display = serializers.CharField(source='get_type_paiement_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Paiement
        fields = [
            'id', 'eleve', 'eleve_nom', 'agent', 'montant',
            'type_paiement', 'type_display', 'reference',
            'statut', 'statut_display', 'date_paiement', 'observations',
        ]
        read_only_fields = ['agent', 'date_paiement']
