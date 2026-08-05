from django.contrib import admin
from .models import Eleve


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = (
        'matricule', 'numero_identification', 'numero_permanent',
        'nom', 'postnom', 'prenom', 'sexe', 'ecole', 'classe', 'actif', 'photo',
    )
    list_filter = ('sexe', 'actif', 'ecole__province_educationnelle', 'lien_tuteur')
    search_fields = (
        'matricule', 'numero_identification', 'numero_permanent',
        'nom', 'postnom', 'prenom',
        'nom_pere', 'nom_mere', 'nom_tuteur',
        'telephone_pere', 'telephone_mere', 'telephone_tuteur',
    )
    readonly_fields = ('date_inscription', 'date_modification')
    fieldsets = (
        ('Identité', {
            'fields': (
                'matricule', 'numero_identification', 'numero_permanent',
                'nom', 'postnom', 'prenom', 'date_naissance', 'lieu_naissance',
                'sexe', 'photo', 'actif',
            ),
        }),
        ('Scolarité', {
            'fields': ('ecole', 'classe', 'adresse'),
        }),
        ('Père', {
            'fields': (
                'nom_pere', 'postnom_pere', 'prenom_pere',
                'telephone_pere', 'email_pere', 'profession_pere', 'photo_pere',
            ),
        }),
        ('Mère', {
            'fields': (
                'nom_mere', 'postnom_mere', 'prenom_mere',
                'telephone_mere', 'email_mere', 'profession_mere', 'photo_mere',
            ),
        }),
        ('Tuteur / responsable', {
            'fields': (
                'lien_tuteur', 'nom_tuteur', 'telephone_tuteur',
                'email_tuteur', 'photo_tuteur',
            ),
        }),
        ('Suivi', {
            'fields': ('date_inscription', 'date_modification'),
        }),
    )
