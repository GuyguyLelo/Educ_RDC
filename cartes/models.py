"""
Modèle Carte scolaire avec QR code.
"""
import uuid
from django.db import models
from django.utils import timezone


class Carte(models.Model):
    """Carte scolaire d'un élève."""

    class Statut(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIREE = 'expiree', 'Expirée'
        ANNULEE = 'annulee', 'Annulée'

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='cartes',
        verbose_name='Élève',
    )
    enrolement = models.OneToOneField(
        'enrolement.Enrolement',
        on_delete=models.PROTECT,
        related_name='carte',
        verbose_name='Enrôlement',
        null=True,
        blank=True,
    )
    numero_carte = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='Numéro de carte',
    )
    date_emission = models.DateTimeField(auto_now_add=True, verbose_name="Date d'émission")
    date_expiration = models.DateField(verbose_name="Date d'expiration")
    qr_code = models.ImageField(
        upload_to='cartes/qr/',
        blank=True,
        null=True,
        verbose_name='QR Code',
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ACTIVE,
        verbose_name='Statut',
    )

    class Meta:
        verbose_name = 'Carte scolaire'
        verbose_name_plural = 'Cartes scolaires'
        ordering = ['-date_emission']

    def __str__(self):
        return f'Carte {self.numero_carte} — {self.eleve.nom_complet}'

    def save(self, *args, **kwargs):
        if not self.numero_carte:
            self.numero_carte = f'RDC-{uuid.uuid4().hex[:12].upper()}'
        if not self.date_expiration:
            self.date_expiration = timezone.now().date().replace(year=timezone.now().year + 3)
        super().save(*args, **kwargs)
