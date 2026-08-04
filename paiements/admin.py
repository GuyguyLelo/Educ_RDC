from django.contrib import admin
from .models import Paiement


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'eleve', 'montant', 'type_paiement', 'statut', 'date_paiement')
    list_filter = ('type_paiement', 'statut')
    search_fields = ('reference', 'eleve__matricule')
