"""
Modèle Élève — identification scolaire.
"""
import uuid

from django.db import models


def _default_code_unique_eleve():
    return f'ELV-{uuid.uuid4().hex[:16].upper()}'


class Eleve(models.Model):
    """Élève inscrit dans une école."""

    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'

    matricule = models.CharField(max_length=30, unique=True, verbose_name='Matricule')
    code_unique = models.CharField(
        max_length=40,
        unique=True,
        default=_default_code_unique_eleve,
        editable=False,
        verbose_name='Code unique QR',
        help_text='Identifiant stable encodé dans le QR code de l’élève.',
    )
    qr_code = models.ImageField(
        upload_to='eleves/qr/',
        blank=True,
        null=True,
        verbose_name='QR Code',
    )
    numero_identification = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Numéro Identification',
    )
    numero_permanent = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Numéro Permanent',
    )
    nom = models.CharField(max_length=100, verbose_name='Nom')
    postnom = models.CharField(max_length=100, blank=True, verbose_name='Postnom')
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    date_naissance = models.DateField(verbose_name='Date de naissance')
    lieu_naissance = models.CharField(max_length=150, blank=True, verbose_name='Lieu de naissance')
    sexe = models.CharField(max_length=1, choices=Sexe.choices, verbose_name='Sexe')
    ecole = models.ForeignKey(
        'ecoles.Ecole',
        on_delete=models.PROTECT,
        related_name='eleves',
        verbose_name='École',
    )
    classe = models.ForeignKey(
        'ecoles.Classe',
        on_delete=models.PROTECT,
        related_name='eleves',
        verbose_name='Classe',
        null=True,
        blank=True,
    )
    adresse = models.CharField(max_length=255, blank=True, verbose_name='Adresse')

    # ——— Père ———
    nom_pere = models.CharField(max_length=100, blank=True, verbose_name='Nom du père')
    postnom_pere = models.CharField(max_length=100, blank=True, verbose_name='Postnom du père')
    prenom_pere = models.CharField(max_length=100, blank=True, verbose_name='Prénom du père')
    telephone_pere = models.CharField(max_length=20, blank=True, verbose_name='Téléphone père')
    email_pere = models.EmailField(blank=True, verbose_name='E-mail père')
    profession_pere = models.CharField(max_length=120, blank=True, verbose_name='Profession père')
    photo_pere = models.ImageField(
        upload_to='eleves/parents/',
        blank=True,
        null=True,
        verbose_name='Photo du père',
    )

    # ——— Mère ———
    nom_mere = models.CharField(max_length=100, blank=True, verbose_name='Nom de la mère')
    postnom_mere = models.CharField(max_length=100, blank=True, verbose_name='Postnom de la mère')
    prenom_mere = models.CharField(max_length=100, blank=True, verbose_name='Prénom de la mère')
    telephone_mere = models.CharField(max_length=20, blank=True, verbose_name='Téléphone mère')
    email_mere = models.EmailField(blank=True, verbose_name='E-mail mère')
    profession_mere = models.CharField(max_length=120, blank=True, verbose_name='Profession mère')
    photo_mere = models.ImageField(
        upload_to='eleves/parents/',
        blank=True,
        null=True,
        verbose_name='Photo de la mère',
    )

    # ——— Tuteur / responsable légal ———
    class LienTuteur(models.TextChoices):
        PERE = 'pere', 'Père'
        MERE = 'mere', 'Mère'
        TUTEUR = 'tuteur', 'Tuteur légal'
        ONCLE_TANTE = 'oncle_tante', 'Oncle / Tante'
        GRAND_PARENT = 'grand_parent', 'Grand-parent'
        AUTRE = 'autre', 'Autre'

    nom_tuteur = models.CharField(max_length=150, blank=True, verbose_name='Nom du tuteur')
    telephone_tuteur = models.CharField(max_length=20, blank=True, verbose_name='Téléphone tuteur')
    email_tuteur = models.EmailField(blank=True, verbose_name='E-mail tuteur')
    lien_tuteur = models.CharField(
        max_length=20,
        choices=LienTuteur.choices,
        blank=True,
        verbose_name='Lien de parenté (tuteur)',
    )
    photo_tuteur = models.ImageField(
        upload_to='eleves/parents/',
        blank=True,
        null=True,
        verbose_name='Photo du tuteur',
    )

    photo = models.ImageField(
        upload_to='eleves/photos/',
        blank=True,
        null=True,
        verbose_name='Photo',
    )
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_inscription = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Élève'
        verbose_name_plural = 'Élèves'
        ordering = ['nom', 'postnom', 'prenom']

    def __str__(self):
        return f'{self.nom} {self.postnom} {self.prenom} ({self.matricule})'

    def save(self, *args, **kwargs):
        if self.numero_identification is not None:
            self.numero_identification = self.numero_identification.strip() or None
        if self.numero_permanent is not None:
            self.numero_permanent = self.numero_permanent.strip() or None
        if not self.code_unique:
            self.code_unique = f'ELV-{uuid.uuid4().hex[:16].upper()}'
        super().save(*args, **kwargs)

    @staticmethod
    def _joindre_nom(*parties):
        return ' '.join(p for p in parties if p).strip()

    @property
    def nom_complet(self):
        return self._joindre_nom(self.nom, self.postnom, self.prenom)

    @property
    def nom_complet_pere(self):
        return self._joindre_nom(self.nom_pere, self.postnom_pere, self.prenom_pere)

    @property
    def nom_complet_mere(self):
        return self._joindre_nom(self.nom_mere, self.postnom_mere, self.prenom_mere)

    def get_photo(self):
        """Retourne la photo élève, sinon celle de la biométrie."""
        if self.photo:
            return self.photo
        bio = getattr(self, 'biometrie', None)
        if bio and bio.photo:
            return bio.photo
        return None
