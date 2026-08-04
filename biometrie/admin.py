from django.contrib import admin
from .models import Biometrie


@admin.register(Biometrie)
class BiometrieAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'validee', 'date_capture')
    list_filter = ('validee',)
    search_fields = ('eleve__matricule', 'eleve__nom')
