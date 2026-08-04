from django.contrib import admin
from .models import JournalActivite


@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'action', 'adresse_ip', 'date_action')
    list_filter = ('action',)
    search_fields = ('utilisateur__username', 'action', 'details')
    readonly_fields = ('utilisateur', 'action', 'details', 'adresse_ip', 'date_action')
