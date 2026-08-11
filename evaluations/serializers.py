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
    nb_periodes = serializers.SerializerMethodField()

    class Meta:
        model = AnneeScolaire
        fields = [
            'id', 'libelle', 'date_debut', 'date_fin', 'regime', 'regime_display',
            'active', 'nb_periodes', 'date_creation',
        ]
        read_only_fields = ['nb_periodes', 'regime_display', 'date_creation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from rest_framework.validators import UniqueValidator
        field = self.fields['libelle']
        field.validators = [
            v for v in field.validators
            if not isinstance(v, UniqueValidator)
        ]
        field.validators.append(
            UniqueValidator(
                queryset=AnneeScolaire.objects.all(),
                message="Ce libellé d'année existe déjà. Choisissez un autre (ex. 2026-2027).",
            )
        )

    def get_nb_periodes(self, obj):
        annotated = getattr(obj, 'nb_periodes', None)
        if isinstance(annotated, int):
            return annotated
        return obj.periodes.count()

    def validate(self, attrs):
        debut = attrs.get('date_debut', getattr(self.instance, 'date_debut', None))
        fin = attrs.get('date_fin', getattr(self.instance, 'date_fin', None))
        if debut and fin and fin < debut:
            raise serializers.ValidationError({
                'date_fin': 'La date de fin doit être postérieure ou égale au début.',
            })
        return attrs


class PeriodeEvaluationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_periode_display', read_only=True)

    class Meta:
        model = PeriodeEvaluation
        fields = [
            'id', 'annee', 'code', 'libelle', 'type_periode', 'type_display',
            'semestre', 'ordre', 'facteur_maximum',
        ]


class MatiereSerializer(serializers.ModelSerializer):
    section_nom = serializers.SerializerMethodField()
    option_nom = serializers.SerializerMethodField()
    classe_nom = serializers.SerializerMethodField()

    class Meta:
        model = Matiere
        fields = [
            'id', 'ecole',
            'section', 'section_nom', 'option', 'option_nom', 'classe', 'classe_nom',
            'nom', 'code', 'maximum', 'ordre', 'active', 'date_creation',
        ]
        read_only_fields = ['date_creation']

    def get_section_nom(self, obj):
        return obj.section.nom if obj.section_id else ''

    def get_option_nom(self, obj):
        return obj.option.nom if obj.option_id else ''

    def get_classe_nom(self, obj):
        return obj.classe.nom if obj.classe_id else ''


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
