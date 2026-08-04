from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'role',
        'province_administrative', 'province_educationnelle', 'antenne', 'is_active',
    )
    list_filter = ('role', 'is_active', 'province_administrative', 'province_educationnelle')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone',
                'province_administrative', 'province_educationnelle', 'antenne',
            ),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Educ_RDC', {
            'fields': (
                'role', 'telephone',
                'province_administrative', 'province_educationnelle', 'antenne',
            ),
        }),
    )
