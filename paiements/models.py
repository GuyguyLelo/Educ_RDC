"""
Modèle Paiement — frais scolaires / carte.
"""
from django.conf import settings
from django.db import models


class Paiement(models.Model):
    """Paiement lié à un élève."""

    class TypePaiement(models.TextChoices):
        CARTE = 'carte', 'Frais de carte'
        AUTRE = 'autre', 'Autre'

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDE = 'valide', 'Validé'
        ANNULE = 'annule', 'Annulé'

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name='Élève',
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='paiements_enregistres',
        verbose_name='Agent',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Montant (CDF)')
    type_paiement = models.CharField(
        max_length=20,
        choices=TypePaiement.choices,
        default=TypePaiement.CARTE,
        verbose_name='Type de paiement',
    )
    reference = models.CharField(max_length=50, unique=True, verbose_name='Référence')
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.VALIDE,
        verbose_name='Statut',
    )
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name='Date de paiement')
    observations = models.TextField(blank=True, verbose_name='Observations')

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_paiement']

    def __str__(self):
        return f'{self.reference} — {self.montant} CDF ({self.eleve.matricule})'
