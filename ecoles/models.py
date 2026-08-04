"""
Modèles géographiques et scolaires : Province, Antenne, École.
"""
from django.db import models


class Province(models.Model):
    """Province de la RDC."""

    nom = models.CharField(max_length=100, unique=True, verbose_name='Nom')
    code = models.CharField(max_length=10, unique=True, verbose_name='Code')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Province'
        verbose_name_plural = 'Provinces'
        ordering = ['nom']

    def __str__(self):
        return f'{self.nom} ({self.code})'


class Antenne(models.Model):
    """Antenne provinciale / sous-division."""

    nom = models.CharField(max_length=150, verbose_name='Nom')
    code = models.CharField(max_length=20, unique=True, verbose_name='Code')
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='antennes',
        verbose_name='Province',
    )
    adresse = models.CharField(max_length=255, blank=True, verbose_name='Adresse')
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Antenne'
        verbose_name_plural = 'Antennes'
        ordering = ['province__nom', 'nom']

    def __str__(self):
        return f'{self.nom} — {self.province.nom}'


class Ecole(models.Model):
    """Établissement scolaire identifié."""

    class TypeEcole(models.TextChoices):
        PUBLIQUE = 'publique', 'Publique'
        PRIVEE = 'privee', 'Privée'
        CONVENTIONNEE = 'conventionnee', 'Conventionnée'

    class Niveau(models.TextChoices):
        MATERNELLE = 'maternelle', 'Maternelle'
        PRIMAIRE = 'primaire', 'Primaire'
        SECONDAIRE = 'secondaire', 'Secondaire'
        MIXTE = 'mixte', 'Mixte'

    nom = models.CharField(max_length=200, verbose_name="Nom de l'école")
    code = models.CharField(max_length=30, unique=True, verbose_name='Code école')
    type_ecole = models.CharField(
        max_length=20,
        choices=TypeEcole.choices,
        default=TypeEcole.PUBLIQUE,
        verbose_name="Type d'école",
    )
    niveau = models.CharField(
        max_length=20,
        choices=Niveau.choices,
        default=Niveau.PRIMAIRE,
        verbose_name='Niveau',
    )
    adresse = models.CharField(max_length=255, verbose_name='Adresse')
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    email = models.EmailField(blank=True, verbose_name='Email')
    directeur = models.CharField(max_length=150, blank=True, verbose_name='Directeur')
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='ecoles',
        verbose_name='Province',
    )
    antenne = models.ForeignKey(
        Antenne,
        on_delete=models.PROTECT,
        related_name='ecoles',
        verbose_name='Antenne',
    )
    active = models.BooleanField(default=True, verbose_name='Active')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'École'
        verbose_name_plural = 'Écoles'
        ordering = ['nom']

    def __str__(self):
        return f'{self.nom} ({self.code})'

    @property
    def nombre_eleves(self):
        return self.eleves.filter(actif=True).count()
