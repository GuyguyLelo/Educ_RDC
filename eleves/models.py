"""
Modèle Élève — identification scolaire.
"""
from django.db import models


class Eleve(models.Model):
    """Élève inscrit dans une école."""

    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'

    matricule = models.CharField(max_length=30, unique=True, verbose_name='Matricule')
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
    classe = models.CharField(max_length=50, verbose_name='Classe')
    adresse = models.CharField(max_length=255, blank=True, verbose_name='Adresse')
    nom_tuteur = models.CharField(max_length=150, blank=True, verbose_name='Nom du tuteur')
    telephone_tuteur = models.CharField(max_length=20, blank=True, verbose_name='Téléphone tuteur')
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

    @property
    def nom_complet(self):
        parties = [self.nom, self.postnom, self.prenom]
        return ' '.join(p for p in parties if p).strip()

    def get_photo(self):
        """Retourne la photo élève, sinon celle de la biométrie."""
        if self.photo:
            return self.photo
        bio = getattr(self, 'biometrie', None)
        if bio and bio.photo:
            return bio.photo
        return None
