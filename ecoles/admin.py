from django.contrib import admin
from .models import Province, Antenne, Ecole


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'date_creation')
    search_fields = ('nom', 'code')


@admin.register(Antenne)
class AntenneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'province', 'telephone')
    list_filter = ('province',)
    search_fields = ('nom', 'code')


@admin.register(Ecole)
class EcoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'type_ecole', 'niveau', 'province', 'antenne', 'active')
    list_filter = ('type_ecole', 'niveau', 'province', 'active')
    search_fields = ('nom', 'code', 'directeur')
