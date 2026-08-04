from django.contrib import admin
from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
    PersonnelEcole,
)
from .forms import (
    ProvinceAdministrativeForm,
    ProvinceEducationnelleForm,
    AntenneForm,
)


@admin.register(StructureOrganisationnelle)
class StructureOrganisationnelleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'actif', 'date_creation')
    search_fields = ('nom', 'code')
    list_filter = ('actif',)


@admin.register(ProvinceAdministrative)
class ProvinceAdministrativeAdmin(admin.ModelAdmin):
    form = ProvinceAdministrativeForm
    list_display = ('nom', 'code', 'actif', 'date_creation')
    search_fields = ('nom', 'code')


@admin.register(ProvinceEducationnelle)
class ProvinceEducationnelleAdmin(admin.ModelAdmin):
    form = ProvinceEducationnelleForm
    list_display = ('nom', 'code', 'province_administrative', 'actif')
    list_filter = ('province_administrative', 'actif')
    search_fields = ('nom', 'code')


@admin.register(Antenne)
class AntenneAdmin(admin.ModelAdmin):
    form = AntenneForm
    list_display = ('nom', 'code', 'province_educationnelle', 'telephone', 'actif')
    list_filter = ('province_educationnelle__province_administrative', 'actif')
    search_fields = ('nom', 'code')


@admin.register(Ecole)
class EcoleAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'code', 'numero_agrement', 'type_ecole', 'niveau',
        'effectif_mat', 'effectif_prim', 'effectif_sec',
        'province_educationnelle', 'antenne', 'active',
    )
    list_filter = ('type_ecole', 'niveau', 'province_educationnelle', 'active')
    search_fields = ('nom', 'code', 'numero_agrement', 'directeur')


@admin.register(PersonnelEcole)
class PersonnelEcoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'postnom', 'prenom', 'fonction', 'ecole', 'telephone', 'actif')
    list_filter = ('fonction', 'sexe', 'actif', 'ecole__antenne')
    search_fields = ('nom', 'postnom', 'prenom', 'matricule', 'telephone')
