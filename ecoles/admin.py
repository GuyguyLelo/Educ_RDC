from django.contrib import admin
from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Ecole,
    Classe,
    PhotoEcole,
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
        'email', 'latitude', 'longitude',
        'effectif_mat', 'effectif_prim', 'effectif_sec',
        'province_educationnelle', 'antenne', 'active',
    )
    list_filter = ('type_ecole', 'niveau', 'province_educationnelle', 'active')
    search_fields = ('nom', 'code', 'numero_agrement', 'directeur', 'email')


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'ecole', 'active', 'date_creation')
    list_filter = ('active', 'ecole__antenne')
    search_fields = ('nom', 'code', 'ecole__nom', 'ecole__code')


@admin.register(PhotoEcole)
class PhotoEcoleAdmin(admin.ModelAdmin):
    list_display = ('ecole', 'legende', 'est_principale', 'date_ajout')
    list_filter = ('est_principale', 'ecole__antenne')
    search_fields = ('ecole__nom', 'legende')


@admin.register(PersonnelEcole)
class PersonnelEcoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'postnom', 'prenom', 'fonction', 'ecole', 'telephone', 'actif')
    list_filter = ('fonction', 'sexe', 'actif', 'ecole__antenne')
    search_fields = ('nom', 'postnom', 'prenom', 'matricule', 'telephone')
