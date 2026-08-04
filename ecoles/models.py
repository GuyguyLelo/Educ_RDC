"""
Hiérarchie territoriale éducative (héritage multi-table) :

StructureOrganisationnelle (modèle unique de base)
├── ProvinceAdministrative
├── ProvinceEducationnelle  → liée à ProvinceAdministrative
└── Antenne                 → liée à ProvinceEducationnelle
"""
from django.db import models


class StructureOrganisationnelle(models.Model):
    """
    Modèle unique de base pour toutes les structures de référence.
    Les spécialisations héritent de ce modèle (héritage multi-table Django).
    """

    nom = models.CharField(max_length=150, verbose_name='Nom')
    code = models.CharField(max_length=20, unique=True, verbose_name='Code')
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Date de modification')

    class Meta:
        verbose_name = 'Structure organisationnelle'
        verbose_name_plural = 'Structures organisationnelles'
        ordering = ['nom']

    def __str__(self):
        return f'{self.nom} ({self.code})'

    @property
    def type_structure(self):
        """Retourne le type concret via héritage."""
        if hasattr(self, 'provinceadministrative'):
            return 'province_administrative'
        if hasattr(self, 'provinceeducationnelle'):
            return 'province_educationnelle'
        if hasattr(self, 'antenne'):
            return 'antenne'
        return 'structure'


class ProvinceAdministrative(StructureOrganisationnelle):
    """Province administrative de la RDC."""

    class Meta:
        verbose_name = 'Province administrative'
        verbose_name_plural = 'Provinces administratives'
        ordering = ['nom']

    def __str__(self):
        return f'{self.nom} ({self.code})'


class ProvinceEducationnelle(StructureOrganisationnelle):
    """Province éducationnelle rattachée à une province administrative."""

    province_administrative = models.ForeignKey(
        ProvinceAdministrative,
        on_delete=models.CASCADE,
        related_name='provinces_educationnelles',
        verbose_name='Province administrative',
    )

    class Meta:
        verbose_name = 'Province éducationnelle'
        verbose_name_plural = 'Provinces éducationnelles'
        ordering = ['province_administrative__nom', 'nom']

    def __str__(self):
        return f'{self.nom} — {self.province_administrative.nom}'


class Antenne(StructureOrganisationnelle):
    """Antenne rattachée à une province éducationnelle."""

    province_educationnelle = models.ForeignKey(
        ProvinceEducationnelle,
        on_delete=models.CASCADE,
        related_name='antennes',
        verbose_name='Province éducationnelle',
    )
    adresse = models.CharField(max_length=255, blank=True, verbose_name='Adresse')
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')

    class Meta:
        verbose_name = 'Antenne'
        verbose_name_plural = 'Antennes'
        ordering = ['province_educationnelle__nom', 'nom']

    def __str__(self):
        return f'{self.nom} — {self.province_educationnelle.nom}'

    @property
    def province_administrative(self):
        return self.province_educationnelle.province_administrative


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
    numero_agrement = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="N° d'agrément",
    )
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
    effectif_mat = models.PositiveIntegerField(default=0, verbose_name='Effectif MAT')
    effectif_prim = models.PositiveIntegerField(default=0, verbose_name='Effectif PRIM')
    effectif_sec = models.PositiveIntegerField(default=0, verbose_name='Effectif SEC')
    effectifs = models.PositiveIntegerField(default=0, verbose_name='Effectifs')
    province_educationnelle = models.ForeignKey(
        ProvinceEducationnelle,
        on_delete=models.PROTECT,
        related_name='ecoles',
        verbose_name='Province éducationnelle',
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
    def province_administrative(self):
        return self.province_educationnelle.province_administrative

    @property
    def nombre_eleves(self):
        return self.eleves.filter(actif=True).count()

    @property
    def nombre_personnels(self):
        return self.personnels.filter(actif=True).count()


class PersonnelEcole(models.Model):
    """Membre du personnel d'une école (identification)."""

    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'

    class Fonction(models.TextChoices):
        DIRECTEUR = 'directeur', 'Directeur / Directrice'
        DIRECTEUR_ETUDES = 'directeur_etudes', "Directeur des études"
        ENSEIGNANT = 'enseignant', 'Enseignant(e)'
        SECRETAIRE = 'secretaire', 'Secrétaire'
        COMPTABLE = 'comptable', 'Comptable'
        SURVEILLANT = 'surveillant', 'Surveillant(e)'
        PREFET = 'prefet', 'Préfet / Préfète'
        AUTRE = 'autre', 'Autre'

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='personnels',
        verbose_name='École',
    )
    matricule = models.CharField(max_length=40, blank=True, verbose_name='Matricule')
    nom = models.CharField(max_length=100, verbose_name='Nom')
    postnom = models.CharField(max_length=100, blank=True, verbose_name='Postnom')
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    sexe = models.CharField(max_length=1, choices=Sexe.choices, verbose_name='Sexe')
    fonction = models.CharField(
        max_length=30,
        choices=Fonction.choices,
        default=Fonction.ENSEIGNANT,
        verbose_name='Fonction',
    )
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    email = models.EmailField(blank=True, verbose_name='Email')
    date_naissance = models.DateField(null=True, blank=True, verbose_name='Date de naissance')
    date_prise_service = models.DateField(null=True, blank=True, verbose_name='Date de prise de service')
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Personnel de l'école"
        verbose_name_plural = 'Personnels des écoles'
        ordering = ['nom', 'postnom', 'prenom']

    def __str__(self):
        return f'{self.nom_complet} — {self.get_fonction_display()}'

    @property
    def nom_complet(self):
        return ' '.join(p for p in [self.nom, self.postnom, self.prenom] if p).strip()


# Alias de compatibilité (anciennes imports)
Province = ProvinceAdministrative
