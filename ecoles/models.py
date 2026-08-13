"""
Hiérarchie territoriale éducative (héritage multi-table) :

StructureOrganisationnelle (modèle unique de base)
├── ProvinceAdministrative
├── ProvinceEducationnelle  → liée à ProvinceAdministrative
└── Antenne                 → liée à ProvinceEducationnelle
"""
from django.conf import settings
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


class Arrete(models.Model):
    """Document du référentiel national (arrêté, agrément, autorisation…)."""

    class TypeDocument(models.TextChoices):
        ARRETE = 'arrete', 'Arrêté'
        AGREMENT = 'agrement', "Décision d'agrément"
        AUTORISATION = 'autorisation', "Autorisation d'ouverture"
        MODIFICATION = 'modification', 'Modification de statut'
        CONVENTION = 'convention', 'Convention'
        AUTRE = 'autre', 'Autre'

    # Alias de compatibilité
    TypeArrete = TypeDocument

    numero = models.CharField(
        max_length=80,
        unique=True,
        verbose_name='N° référence',
        help_text='Référence unique (ex. AGR/EPSP/2024/001)',
    )
    objet = models.CharField(max_length=255, verbose_name='Objet')
    type_arrete = models.CharField(
        max_length=30,
        choices=TypeDocument.choices,
        default=TypeDocument.ARRETE,
        verbose_name='Type de document',
    )
    date_arrete = models.DateField(verbose_name='Date du document')
    signataire = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nom du signataire',
    )
    autorite = models.CharField(
        max_length=150,
        blank=True,
        default='EPSP',
        verbose_name='Autorité émettrice',
    )
    description = models.TextField(blank=True, verbose_name='Description / observations')
    fichier = models.FileField(
        upload_to='referentiel/arretes/',
        blank=True,
        null=True,
        verbose_name='Fichier (PDF)',
    )
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Document référentiel'
        verbose_name_plural = 'Documents référentiels'
        ordering = ['-date_arrete', 'numero']

    def __str__(self):
        return f'{self.numero} — {self.objet}'


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
        max_length=80,
        blank=True,
        verbose_name="N° d'agrément",
    )
    arrete = models.ForeignKey(
        Arrete,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecoles',
        verbose_name="Arrêté d'agrément",
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
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Latitude GPS',
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Longitude GPS',
    )
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

    @property
    def photo_principale(self):
        principale = self.photos.filter(est_principale=True).first()
        if principale:
            return principale
        return self.photos.first()

    @property
    def has_gps(self):
        return self.latitude is not None and self.longitude is not None


class SectionScolaire(models.Model):
    """Section d'enseignement (ex. Technique, Scientifique, Pédagogique)."""

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name='École',
    )
    nom = models.CharField(max_length=120, verbose_name='Nom')
    code = models.CharField(max_length=30, blank=True, verbose_name='Code')
    active = models.BooleanField(default=True, verbose_name='Active')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Section scolaire'
        verbose_name_plural = 'Sections scolaires'
        ordering = ['nom']
        constraints = [
            models.UniqueConstraint(fields=['ecole', 'nom'], name='uniq_section_nom_ecole'),
        ]

    def __str__(self):
        return f'{self.nom} ({self.ecole.code})'


class OptionScolaire(models.Model):
    """Option rattachée à une section (ex. Coupe et Couture)."""

    section = models.ForeignKey(
        SectionScolaire,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Section',
    )
    nom = models.CharField(max_length=150, verbose_name='Nom')
    code = models.CharField(max_length=30, blank=True, verbose_name='Code')
    active = models.BooleanField(default=True, verbose_name='Active')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Option scolaire'
        verbose_name_plural = 'Options scolaires'
        ordering = ['section__nom', 'nom']
        constraints = [
            models.UniqueConstraint(fields=['section', 'nom'], name='uniq_option_nom_section'),
        ]

    def __str__(self):
        return f'{self.nom} — {self.section.nom}'

    @property
    def ecole(self):
        return self.section.ecole


class Classe(models.Model):
    """Classe scolaire créée par l'administratif de l'école."""

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name='École',
    )
    section = models.ForeignKey(
        SectionScolaire,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='classes',
        verbose_name='Section',
    )
    option = models.ForeignKey(
        OptionScolaire,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='classes',
        verbose_name='Option',
    )
    nom = models.CharField(max_length=100, verbose_name='Nom de la classe')
    code = models.CharField(max_length=30, blank=True, verbose_name='Code')
    active = models.BooleanField(default=True, verbose_name='Active')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')

    class Meta:
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'
        ordering = ['nom']
        constraints = [
            models.UniqueConstraint(
                fields=['ecole', 'nom'],
                name='uniq_classe_nom_par_ecole',
            ),
        ]

    def __str__(self):
        return f'{self.nom} ({self.ecole.code})'

    def save(self, *args, **kwargs):
        self.nom = (self.nom or '').strip()
        self.code = (self.code or '').strip()
        # Aligner section sur l'option si besoin
        if self.option_id and not self.section_id:
            self.section_id = self.option.section_id
        elif self.option_id and self.section_id and self.option.section_id != self.section_id:
            self.section_id = self.option.section_id
        super().save(*args, **kwargs)


class PhotoEcole(models.Model):
    """Photo associée à une école."""

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='École',
    )
    image = models.ImageField(upload_to='ecoles/photos/', verbose_name='Photo')
    legende = models.CharField(max_length=200, blank=True, verbose_name='Légende')
    est_principale = models.BooleanField(default=False, verbose_name='Photo principale')
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")

    class Meta:
        verbose_name = "Photo d'école"
        verbose_name_plural = "Photos d'écoles"
        ordering = ['-est_principale', '-date_ajout']

    def __str__(self):
        return f'Photo — {self.ecole.nom}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.est_principale:
            PhotoEcole.objects.filter(ecole=self.ecole).exclude(pk=self.pk).update(est_principale=False)


class DocumentEcole(models.Model):
    """Document administratif de création / agrément d'une école."""

    class TypeDocument(models.TextChoices):
        AGREMENT = 'agrement', "Arrêté / décision d'agrément"
        AUTORISATION = 'autorisation', "Autorisation d'ouverture"
        STATUTS = 'statuts', "Statuts de l'établissement"
        PLAN = 'plan', 'Plan de localisation'
        ATTESTATION_EPSP = 'attestation_epsp', 'Attestation EPSP'
        AUTRE = 'autre', 'Autre document'

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='École',
    )
    type_document = models.CharField(
        max_length=30,
        choices=TypeDocument.choices,
        default=TypeDocument.AGREMENT,
        verbose_name='Type de document',
    )
    titre = models.CharField(max_length=200, blank=True, verbose_name='Titre / référence')
    fichier = models.FileField(upload_to='ecoles/documents/', verbose_name='Fichier')
    arrete = models.ForeignKey(
        Arrete,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_ecoles',
        verbose_name='Arrêté (référentiel)',
    )
    date_document = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date du document',
    )
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")

    class Meta:
        verbose_name = "Document d'école"
        verbose_name_plural = "Documents d'écoles"
        ordering = ['type_document', '-date_ajout']

    def __str__(self):
        return f'{self.get_type_document_display()} — {self.ecole.nom}'

    @property
    def nom_fichier(self):
        if not self.fichier:
            return ''
        return self.fichier.name.rsplit('/', 1)[-1]


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
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fiche_personnel',
        verbose_name='Compte plateforme',
        help_text='Compte Educ_RDC lié (ex. enseignant titulaire).',
    )
    matricule = models.CharField(max_length=40, blank=True, verbose_name='Matricule')
    reference_acte_engagement = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Référence de l'acte d'engagement",
        help_text="N° / référence de l'acte d'engagement de l'agent.",
    )
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
    photo = models.ImageField(
        upload_to='personnels/photos/',
        blank=True,
        null=True,
        verbose_name='Photo',
    )
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
