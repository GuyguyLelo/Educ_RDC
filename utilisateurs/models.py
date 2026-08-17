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
        AGENT_PROVINCE_ADMIN = 'agent_province_admin', 'Agent Province administrative'
        AGENT_PROVINCIAL = 'agent_provincial', 'Agent Province éducationnelle'
        AGENT_ANTENNE = 'agent_antenne', 'Agent Antenne'
        ADMIN_ECOLE = 'admin_ecole', 'Administratif école'
        ENSEIGNANT = 'enseignant', 'Enseignant'

    ROLES_ECOLE = (Role.ADMIN_ECOLE, Role.ENSEIGNANT)

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.AGENT_ANTENNE,
        verbose_name='Rôle',
    )
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    province_administrative = models.ForeignKey(
        'ecoles.ProvinceAdministrative',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='Province administrative',
    )
    province_educationnelle = models.ForeignKey(
        'ecoles.ProvinceEducationnelle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='Province éducationnelle',
    )
    antenne = models.ForeignKey(
        'ecoles.Antenne',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name='Antenne',
    )
    ecole = models.ForeignKey(
        'ecoles.Ecole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs',
        verbose_name='École',
    )
    classe = models.ForeignKey(
        'ecoles.Classe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enseignants',
        verbose_name='Classe (titulaire)',
        help_text="Classe dont l'enseignant est titulaire — limite l'accès aux élèves de cette classe.",
    )
    photo = models.ImageField(
        upload_to='utilisateurs/photos/',
        blank=True,
        null=True,
        verbose_name='Photo de profil',
    )
    connexion_biometrique = models.BooleanField(
        default=False,
        verbose_name='Connexion biométrique autorisée',
        help_text='Permet à l’utilisateur d’enregistrer et d’utiliser l’empreinte / Face ID / Windows Hello.',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    def save(self, *args, **kwargs):
        # Synchroniser le rattachement territorial depuis l'école
        if self.ecole_id and self.role in self.ROLES_ECOLE:
            ecole = self.ecole
            if ecole is not None:
                self.antenne_id = ecole.antenne_id
                self.province_educationnelle_id = ecole.province_educationnelle_id
                pe = ecole.province_educationnelle
                if pe is not None:
                    self.province_administrative_id = pe.province_administrative_id
        elif self.role not in self.ROLES_ECOLE:
            # Les agents ministériels ne sont pas rattachés à une école
            self.ecole = None

        # Agent antenne : rattacher PE / PA depuis l’antenne
        if self.role == self.Role.AGENT_ANTENNE and self.antenne_id:
            antenne = self.antenne
            if antenne is not None:
                self.province_educationnelle_id = antenne.province_educationnelle_id
                pe = antenne.province_educationnelle
                if pe is not None:
                    self.province_administrative_id = pe.province_administrative_id
        elif self.role == self.Role.AGENT_PROVINCIAL and self.province_educationnelle_id:
            pe = self.province_educationnelle
            if pe is not None:
                self.province_administrative_id = pe.province_administrative_id
                self.antenne = None

        # Agent PA : chef des PE — rattachement PA uniquement
        if self.role == self.Role.AGENT_PROVINCE_ADMIN:
            self.province_educationnelle = None
            self.antenne = None

        if self.role != self.Role.ENSEIGNANT:
            self.classe = None
        elif self.classe_id and self.ecole_id and self.classe.ecole_id != self.ecole_id:
            # La classe doit appartenir à l'école de l'enseignant
            self.classe = None
        super().save(*args, **kwargs)

    @property
    def province(self):
        """Compatibilité : province éducationnelle prioritaire."""
        return self.province_educationnelle

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
            self.Role.AGENT_PROVINCE_ADMIN,
            self.Role.AGENT_PROVINCIAL,
        ) or self.is_superuser

    @property
    def est_utilisateur_ecole(self):
        return self.role in self.ROLES_ECOLE

    @property
    def est_enseignant(self):
        return self.role == self.Role.ENSEIGNANT

    @property
    def classe_nom(self):
        return self.classe.nom if self.classe_id else ''

    @property
    def est_admin_ecole(self):
        return self.role == self.Role.ADMIN_ECOLE or self.est_admin

    @property
    def est_agent_territorial(self):
        """Agents PA / PE / antenne — consultation territoriale restreinte (sans écriture)."""
        return self.role in (
            self.Role.AGENT_PROVINCE_ADMIN,
            self.Role.AGENT_PROVINCIAL,
            self.Role.AGENT_ANTENNE,
        )


class CredentialBiometrique(models.Model):
    """Clé publique WebAuthn (empreinte / visage) pour connexion plateforme."""

    utilisateur = models.ForeignKey(
        'Utilisateur',
        on_delete=models.CASCADE,
        related_name='credentials_biometriques',
        verbose_name='Utilisateur',
    )
    credential_id = models.CharField(
        max_length=512,
        unique=True,
        verbose_name='ID credential (base64url)',
    )
    public_key = models.BinaryField(verbose_name='Clé publique')
    sign_count = models.PositiveIntegerField(default=0, verbose_name='Compteur de signatures')
    transports = models.JSONField(default=list, blank=True, verbose_name='Transports')
    nom_appareil = models.CharField(
        max_length=120,
        blank=True,
        default='Appareil biométrique',
        verbose_name='Nom de l’appareil',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date d’enregistrement')
    date_dernier_usage = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Dernière utilisation',
    )

    class Meta:
        verbose_name = 'Identifiant biométrique'
        verbose_name_plural = 'Identifiants biométriques'
        ordering = ['-date_creation']

    def __str__(self):
        return f'{self.utilisateur} — {self.nom_appareil}'
