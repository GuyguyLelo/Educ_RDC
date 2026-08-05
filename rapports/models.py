"""
Modèle Rapport — historique des exports / rapports générés.
"""
from django.conf import settings
from django.db import models


class Rapport(models.Model):
    """Rapport administratif généré."""

    class TypeRapport(models.TextChoices):
        ELEVES = 'eleves', 'Rapport élèves'
        ECOLES = 'ecoles', 'Rapport écoles'
        CARTES = 'cartes', 'Rapport cartes'
        GLOBAL = 'global', 'Rapport global'

    titre = models.CharField(max_length=200, verbose_name='Titre')
    type_rapport = models.CharField(
        max_length=20,
        choices=TypeRapport.choices,
        default=TypeRapport.GLOBAL,
        verbose_name='Type',
    )
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rapports_generes',
        verbose_name='Généré par',
    )
    fichier = models.FileField(
        upload_to='rapports/',
        blank=True,
        null=True,
        verbose_name='Fichier',
    )
    date_generation = models.DateTimeField(auto_now_add=True, verbose_name='Date de génération')
    parametres = models.JSONField(default=dict, blank=True, verbose_name='Paramètres')

    class Meta:
        verbose_name = 'Rapport'
        verbose_name_plural = 'Rapports'
        ordering = ['-date_generation']

    def __str__(self):
        return f'{self.titre} ({self.date_generation:%d/%m/%Y})'
