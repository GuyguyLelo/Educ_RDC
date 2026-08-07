"""Serializers — module Évaluation."""
from rest_framework import serializers

from .models import (
    AnneeScolaire,
    BulletinDecision,
    Matiere,
    Note,
    PeriodeEvaluation,
    ProgrammeClasse,
)


class AnneeScolaireSerializer(serializers.ModelSerializer):
    regime_display = serializers.CharField(source='get_regime_display', read_only=True)

    class Meta:
        model = AnneeScolaire
        fields = [
            'id', 'libelle', 'date_debut', 'date_fin', 'regime', 'regime_display',
            'active', 'date_creation',
        ]


class PeriodeEvaluationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_periode_display', read_only=True)

    class Meta:
        model = PeriodeEvaluation
        fields = [
            'id', 'annee', 'code', 'libelle', 'type_periode', 'type_display',
            'semestre', 'ordre', 'facteur_maximum',
        ]


class MatiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matiere
        fields = [
            'id', 'ecole', 'nom', 'code', 'maximum', 'ordre', 'active', 'date_creation',
        ]
        read_only_fields = ['date_creation']


class ProgrammeClasseSerializer(serializers.ModelSerializer):
    matiere_nom = serializers.CharField(source='matiere.nom', read_only=True)
    maximum_effectif = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True,
    )
    classe_nom = serializers.CharField(source='classe.nom', read_only=True)

    class Meta:
        model = ProgrammeClasse
        fields = [
            'id', 'annee', 'classe', 'classe_nom', 'matiere', 'matiere_nom',
            'maximum', 'maximum_effectif', 'ordre',
        ]


class NoteSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)
    matiere_nom = serializers.CharField(source='programme.matiere.nom', read_only=True)
    periode_code = serializers.CharField(source='periode.code', read_only=True)

    class Meta:
        model = Note
        fields = [
            'id', 'eleve', 'eleve_nom', 'programme', 'matiere_nom',
            'periode', 'periode_code', 'valeur', 'saisi_par', 'date_saisie',
        ]
        read_only_fields = ['saisi_par', 'date_saisie']


class NoteBulkItemSerializer(serializers.Serializer):
    eleve = serializers.IntegerField()
    periode = serializers.IntegerField()
    valeur = serializers.DecimalField(
        max_digits=6, decimal_places=2, allow_null=True, required=False,
    )


class NoteBulkSerializer(serializers.Serializer):
    programme = serializers.IntegerField()
    notes = NoteBulkItemSerializer(many=True)


class BulletinDecisionSerializer(serializers.ModelSerializer):
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)

    class Meta:
        model = BulletinDecision
        fields = [
            'id', 'eleve', 'eleve_nom', 'annee', 'decision', 'decision_display',
            'conduite', 'appreciation', 'place', 'effectif',
            'total_obtenu', 'total_max', 'pourcentage', 'date_decision',
        ]
