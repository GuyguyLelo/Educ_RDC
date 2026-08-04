from django.contrib import admin
from .models import Carte


@admin.register(Carte)
class CarteAdmin(admin.ModelAdmin):
    list_display = ('numero_carte', 'eleve', 'date_emission', 'date_expiration', 'statut')
    list_filter = ('statut',)
    search_fields = ('numero_carte', 'eleve__matricule', 'eleve__nom')
