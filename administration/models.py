"""
Modèles d'administration — journaux d'activité et accès extérieur.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


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


class AutorisationAccesExterieur(models.Model):
    """Demande / autorisation de connexion depuis l'extérieur de la RDC."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        AUTORISE = 'autorise', 'Autorisé'
        REFUSE = 'refuse', 'Refusé'
        REVOQUE = 'revoque', 'Révoqué'

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='autorisations_acces_exterieur',
        verbose_name='Utilisateur',
    )
    adresse_ip = models.GenericIPAddressField(verbose_name='Adresse IP')
    geo_label = models.CharField(max_length=255, blank=True, verbose_name='Localisation')
    country_code = models.CharField(max_length=8, blank=True, verbose_name='Code pays')
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name='Statut',
    )
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name='Date de demande')
    date_decision = models.DateTimeField(null=True, blank=True, verbose_name='Date de décision')
    date_expiration = models.DateTimeField(null=True, blank=True, verbose_name='Expiration')
    decide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decisions_acces_exterieur',
        verbose_name='Décidé par',
    )
    motif = models.CharField(max_length=255, blank=True, verbose_name='Motif / commentaire')

    class Meta:
        verbose_name = 'Autorisation accès extérieur'
        verbose_name_plural = 'Autorisations accès extérieur'
        ordering = ['-date_demande']
        indexes = [
            models.Index(fields=['statut', 'utilisateur']),
        ]

    def __str__(self):
        return f'{self.utilisateur} — {self.adresse_ip} ({self.get_statut_display()})'

    @property
    def est_valide(self) -> bool:
        if self.statut != self.Statut.AUTORISE:
            return False
        if self.date_expiration and timezone.now() > self.date_expiration:
            return False
        return True
