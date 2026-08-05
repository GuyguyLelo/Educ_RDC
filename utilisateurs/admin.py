from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'role', 'ecole', 'classe',
        'province_administrative', 'province_educationnelle', 'antenne', 'is_active',
    )
    list_filter = (
        'role', 'is_active', 'ecole',
        'province_administrative', 'province_educationnelle',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'classe')
    fieldsets = UserAdmin.fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone', 'ecole', 'classe',
                'province_administrative', 'province_educationnelle', 'antenne',
            ),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone', 'ecole', 'classe',
                'province_administrative', 'province_educationnelle', 'antenne',
            ),
        }),
    )
