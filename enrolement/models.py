"""
Modèle Enrôlement — processus d'enregistrement scolaire.
"""
from django.conf import settings
from django.db import models


class Enrolement(models.Model):
    """Dossier d'enrôlement d'un élève."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDE = 'valide', 'Validé'
        REJETE = 'rejete', 'Rejeté'

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='enrolements',
        verbose_name='Élève',
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='enrolements_effectues',
        verbose_name='Agent',
    )
    annee_scolaire = models.CharField(
        max_length=20,
        default='2025-2026',
        verbose_name='Année scolaire',
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name='Statut',
    )
    date_enrolement = models.DateTimeField(auto_now_add=True, verbose_name="Date d'enrôlement")
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name='Date de validation')
    observations = models.TextField(blank=True, verbose_name='Observations')

    class Meta:
        verbose_name = 'Enrôlement'
        verbose_name_plural = 'Enrôlements'
        ordering = ['-date_enrolement']

    def __str__(self):
        return f'Enrôlement {self.eleve.matricule} — {self.get_statut_display()}'
