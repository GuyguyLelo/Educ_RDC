from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, CredentialBiometrique


@admin.register(CredentialBiometrique)
class CredentialBiometriqueAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'nom_appareil', 'date_creation', 'date_dernier_usage')
    search_fields = ('utilisateur__username', 'nom_appareil')
    readonly_fields = ('credential_id', 'sign_count', 'date_creation', 'date_dernier_usage')


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'role', 'ecole', 'classe',
        'province_administrative', 'province_educationnelle', 'antenne',
        'is_active', 'connexion_biometrique',
    )
    list_filter = (
        'role', 'is_active', 'connexion_biometrique', 'ecole',
        'province_administrative', 'province_educationnelle',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'classe')
    fieldsets = UserAdmin.fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone', 'ecole', 'classe',
                'province_administrative', 'province_educationnelle', 'antenne',
                'connexion_biometrique',
            ),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone', 'ecole', 'classe',
                'province_administrative', 'province_educationnelle', 'antenne',
                'connexion_biometrique',
            ),
        }),
    )
