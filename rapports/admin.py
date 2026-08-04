from django.contrib import admin
from .models import Rapport


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_rapport', 'genere_par', 'date_generation')
    list_filter = ('type_rapport',)
