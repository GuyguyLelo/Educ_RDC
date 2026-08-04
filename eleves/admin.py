from django.contrib import admin
from .models import Eleve


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'nom', 'postnom', 'prenom', 'sexe', 'ecole', 'classe', 'actif', 'photo')
    list_filter = ('sexe', 'actif', 'ecole__province')
    search_fields = ('matricule', 'nom', 'postnom', 'prenom')
    readonly_fields = ('date_inscription', 'date_modification')

