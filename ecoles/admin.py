from django.contrib import admin
from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Arrete,
    Ecole,
    SectionScolaire,
    OptionScolaire,
    Classe,
    PhotoEcole,
    DocumentEcole,
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


@admin.register(Arrete)
class ArreteAdmin(admin.ModelAdmin):
    list_display = ('numero', 'objet', 'type_arrete', 'date_arrete', 'signataire', 'autorite', 'actif')
    list_filter = ('type_arrete', 'actif')
    search_fields = ('numero', 'objet', 'autorite', 'signataire')
    date_hierarchy = 'date_arrete'


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
    raw_id_fields = ('arrete',)


@admin.register(SectionScolaire)
class SectionScolaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'ecole', 'active')
    list_filter = ('active', 'ecole')
    search_fields = ('nom', 'code', 'ecole__nom')


@admin.register(OptionScolaire)
class OptionScolaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'section', 'active')
    list_filter = ('active', 'section__ecole')
    search_fields = ('nom', 'code', 'section__nom')


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'section', 'option', 'ecole', 'active', 'date_creation')
    list_filter = ('active', 'section', 'ecole__antenne')
    search_fields = ('nom', 'code', 'ecole__nom', 'ecole__code')


@admin.register(PhotoEcole)
class PhotoEcoleAdmin(admin.ModelAdmin):
    list_display = ('ecole', 'legende', 'est_principale', 'date_ajout')
    list_filter = ('est_principale', 'ecole__antenne')
    search_fields = ('ecole__nom', 'legende')


@admin.register(DocumentEcole)
class DocumentEcoleAdmin(admin.ModelAdmin):
    list_display = ('ecole', 'type_document', 'titre', 'date_document', 'date_ajout')
    list_filter = ('type_document', 'ecole__antenne')
    search_fields = ('ecole__nom', 'titre', 'fichier')


@admin.register(PersonnelEcole)
class PersonnelEcoleAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'postnom', 'prenom', 'fonction', 'ecole',
        'matricule', 'reference_acte_engagement', 'telephone', 'actif',
    )
    list_filter = ('fonction', 'sexe', 'actif', 'ecole__antenne')
    search_fields = (
        'nom', 'postnom', 'prenom', 'matricule',
        'reference_acte_engagement', 'telephone',
    )
