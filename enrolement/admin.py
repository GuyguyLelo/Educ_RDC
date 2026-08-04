from django.contrib import admin
from .models import Enrolement


@admin.register(Enrolement)
class EnrolementAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'annee_scolaire', 'statut', 'agent', 'date_enrolement')
    list_filter = ('statut', 'annee_scolaire')
    search_fields = ('eleve__matricule', 'eleve__nom')
