"""
Modèles d'administration — journaux d'activité.
"""
from django.conf import settings
from django.db import models


class JournalActivite(models.Model):
    """Journal des actions importantes sur la plateforme."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activites',
        verbose_name='Utilisateur',
    )
    action = models.CharField(max_length=100, verbose_name='Action')
    details = models.TextField(blank=True, verbose_name='Détails')
    adresse_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Adresse IP')
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date de l'action")

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journaux d'activité"
        ordering = ['-date_action']

    def __str__(self):
        user = self.utilisateur.username if self.utilisateur else 'Système'
        return f'{user} — {self.action} ({self.date_action:%d/%m/%Y %H:%M})'
