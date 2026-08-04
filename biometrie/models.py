"""
Modèle Biométrie — photo et empreinte simulée.
"""
from django.db import models


class Biometrie(models.Model):
    """Données biométriques d'un élève (photo + empreinte simulée)."""

    eleve = models.OneToOneField(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='biometrie',
        verbose_name='Élève',
    )
    photo = models.ImageField(
        upload_to='biometrie/photos/',
        blank=True,
        null=True,
        verbose_name='Photo',
    )
    # Empreinte simulée (hash fictif pour démonstration)
    empreinte_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name='Hash empreinte (simulé)',
    )
    date_capture = models.DateTimeField(auto_now_add=True, verbose_name='Date de capture')
    validee = models.BooleanField(default=False, verbose_name='Validée')
    observations = models.TextField(blank=True, verbose_name='Observations')

    class Meta:
        verbose_name = 'Biométrie'
        verbose_name_plural = 'Biométries'

    def __str__(self):
        statut = 'validée' if self.validee else 'en attente'
        return f'Biométrie de {self.eleve.nom_complet} ({statut})'
