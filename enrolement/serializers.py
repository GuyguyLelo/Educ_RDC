"""Serializers enrôlement."""
from rest_framework import serializers
from .models import Enrolement


class EnrolementSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)
    eleve_matricule = serializers.CharField(source='eleve.matricule', read_only=True)
    agent_nom = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Enrolement
        fields = [
            'id', 'eleve', 'eleve_nom', 'eleve_matricule', 'agent', 'agent_nom',
            'annee_scolaire', 'statut', 'statut_display',
            'date_enrolement', 'date_validation', 'observations',
        ]
        read_only_fields = ['agent', 'date_enrolement', 'date_validation']

    def get_agent_nom(self, obj):
        if obj.agent:
            return obj.agent.get_full_name() or obj.agent.username
        return None
