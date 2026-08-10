from django.contrib import admin
from .models import (
    AnneeScolaire,
    BulletinDecision,
    Matiere,
    Note,
    PeriodeEvaluation,
    ProgrammeClasse,
    VerrouillagePeriode,
)


@admin.register(AnneeScolaire)
class AnneeScolaireAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'date_debut', 'date_fin', 'regime', 'active')
    list_filter = ('regime', 'active')


@admin.register(PeriodeEvaluation)
class PeriodeEvaluationAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'code', 'annee', 'type_periode', 'semestre', 'ordre')
    list_filter = ('annee', 'type_periode')


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ('nom', 'section', 'option', 'classe', 'ecole', 'maximum', 'ordre', 'active')
    list_filter = ('ecole', 'section', 'active')
    search_fields = ('nom', 'code')


@admin.register(ProgrammeClasse)
class ProgrammeClasseAdmin(admin.ModelAdmin):
    list_display = ('classe', 'matiere', 'annee', 'maximum', 'ordre')
    list_filter = ('annee', 'classe__ecole')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'programme', 'periode', 'valeur', 'date_saisie')
    list_filter = ('periode__annee',)


@admin.register(BulletinDecision)
class BulletinDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'eleve', 'annee', 'decision', 'pourcentage', 'place', 'effectif',
    )
    list_filter = ('annee', 'decision')


@admin.register(VerrouillagePeriode)
class VerrouillagePeriodeAdmin(admin.ModelAdmin):
    list_display = ('classe', 'periode', 'annee', 'verrouille_par', 'date_verrouillage')
    list_filter = ('annee',)
