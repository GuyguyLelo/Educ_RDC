"""
Modèle utilisateur personnalisé avec rôles hiérarchiques.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Utilisateur de la plateforme Educ_RDC."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        AGENT_NATIONAL = 'agent_national', 'Agent National'
        AGENT_PROVINCIAL = 'agent_provincial', 'Agent Provincial'
        AGENT_ANTENNE = 'agent_antenne', 'Agent Antenne'

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.AGENT_ANTENNE,
        verbose_name='Rôle',
    )
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    province = models.ForeignKey(
        'ecoles.Province',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='Province',
    )
    antenne = models.ForeignKey(
        'ecoles.Antenne',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='Antenne',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def est_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def est_national(self):
        return self.role in (self.Role.ADMIN, self.Role.AGENT_NATIONAL) or self.is_superuser

    @property
    def est_provincial(self):
        return self.role in (
            self.Role.ADMIN,
            self.Role.AGENT_NATIONAL,
            self.Role.AGENT_PROVINCIAL,
        ) or self.is_superuser
