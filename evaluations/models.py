"""
Module Évaluation — notes et bulletins scolaires (modèle RDC / IGE).

Structure officielle secondaire :
  1ère P · 2ème P · Exam. 1er sem. · Tot.1 · 3ème P · 4ème P · Exam. 2e sem. · Tot.2 · TOTAL · %
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class AnneeScolaire(models.Model):
    """
    Référentiel national d'année scolaire (ex. 2025-2026).

    Une seule année peut être active pour toute la plateforme :
    notes, bulletins, programmes et périodes s'y rattachent.
    """

    class Regime(models.TextChoices):
        SECONDAIRE = 'secondaire', 'Secondaire (4 périodes + 2 examens)'
        PRIMAIRE = 'primaire', 'Primaire (3 trimestres)'

    libelle = models.CharField(max_length=20, unique=True, verbose_name='Libellé')
    date_debut = models.DateField(verbose_name='Début')
    date_fin = models.DateField(verbose_name='Fin')
    regime = models.CharField(
        max_length=20,
        choices=Regime.choices,
        default=Regime.SECONDAIRE,
        verbose_name='Régime d\'évaluation',
    )
    active = models.BooleanField(
        default=False,
        verbose_name='Année active (nationale)',
        help_text='Une seule année active pour toute la plateforme.',
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Année scolaire'
        verbose_name_plural = 'Années scolaires'
        ordering = ['-date_debut']

    def __str__(self):
        return self.libelle

    @classmethod
    def get_active(cls):
        """Retourne l'année scolaire nationale active, ou None."""
        return cls.objects.filter(active=True).order_by('-date_debut').first()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.active:
            AnneeScolaire.objects.exclude(pk=self.pk).filter(active=True).update(active=False)


class PeriodeEvaluation(models.Model):
    """Période de notation rattachée à une année scolaire."""

    class TypePeriode(models.TextChoices):
        TRAVAUX = 'travaux', 'Travaux journaliers'
        EXAMEN = 'examen', 'Examen'
        TRIMESTRE = 'trimestre', 'Trimestre'

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='periodes',
        verbose_name='Année scolaire',
    )
    code = models.CharField(max_length=20, verbose_name='Code')
    libelle = models.CharField(max_length=80, verbose_name='Libellé')
    type_periode = models.CharField(
        max_length=20,
        choices=TypePeriode.choices,
        default=TypePeriode.TRAVAUX,
        verbose_name='Type',
    )
    semestre = models.PositiveSmallIntegerField(default=1, verbose_name='Semestre')
    ordre = models.PositiveSmallIntegerField(default=1, verbose_name='Ordre')
    facteur_maximum = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1'),
        verbose_name='Facteur max. (× max matière)',
        help_text='1 pour une période TJ, 2 pour un examen semestriel typique.',
    )

    class Meta:
        verbose_name = 'Période d\'évaluation'
        verbose_name_plural = 'Périodes d\'évaluation'
        ordering = ['annee', 'ordre']
        constraints = [
            models.UniqueConstraint(fields=['annee', 'code'], name='uniq_periode_code_annee'),
        ]

    def __str__(self):
        return f'{self.libelle} ({self.annee.libelle})'


class VerrouillagePeriode(models.Model):
    """Période verrouillée pour une classe (plus de saisie possible)."""

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='verrouillages_periodes',
        verbose_name='Année scolaire',
    )
    classe = models.ForeignKey(
        'ecoles.Classe',
        on_delete=models.CASCADE,
        related_name='verrouillages_periodes',
        verbose_name='Classe',
    )
    periode = models.ForeignKey(
        PeriodeEvaluation,
        on_delete=models.CASCADE,
        related_name='verrouillages',
        verbose_name='Période',
    )
    verrouille_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='periodes_verrouillees',
        verbose_name='Verrouillé par',
    )
    date_verrouillage = models.DateTimeField(auto_now_add=True, verbose_name='Date de verrouillage')

    class Meta:
        verbose_name = 'Verrouillage de période'
        verbose_name_plural = 'Verrouillages de périodes'
        constraints = [
            models.UniqueConstraint(
                fields=['annee', 'classe', 'periode'],
                name='uniq_verrou_periode_classe',
            ),
        ]

    def __str__(self):
        return f'{self.classe} — {self.periode.libelle} (verrouillée)'


class Matiere(models.Model):
    """Branche liée à une section, une option et une classe de l'école."""

    ecole = models.ForeignKey(
        'ecoles.Ecole',
        on_delete=models.CASCADE,
        related_name='matieres',
        verbose_name='École',
    )
    section = models.ForeignKey(
        'ecoles.SectionScolaire',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='matieres',
        verbose_name='Section',
    )
    option = models.ForeignKey(
        'ecoles.OptionScolaire',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='matieres',
        verbose_name='Option',
    )
    classe = models.ForeignKey(
        'ecoles.Classe',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='matieres_catalogue',
        verbose_name='Classe',
    )
    nom = models.CharField(max_length=120, verbose_name='Nom')
    code = models.CharField(max_length=20, blank=True, verbose_name='Code')
    maximum = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('10'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Maximum (1 période TJ)',
    )
    ordre = models.PositiveSmallIntegerField(default=1, verbose_name='Ordre')
    active = models.BooleanField(default=True, verbose_name='Active')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Matière'
        verbose_name_plural = 'Matières'
        ordering = ['ordre', 'nom']
        constraints = [
            models.UniqueConstraint(
                fields=['ecole', 'nom', 'section', 'option', 'classe'],
                name='uniq_matiere_scope_ecole',
            ),
        ]

    def __str__(self):
        return f'{self.nom} (/{self.maximum})'

    def save(self, *args, **kwargs):
        # Cohérence section ← option ← classe
        if self.classe_id:
            if self.classe.option_id:
                self.option_id = self.classe.option_id
            if self.classe.section_id:
                self.section_id = self.classe.section_id
        elif self.option_id and not self.section_id:
            self.section_id = self.option.section_id
        super().save(*args, **kwargs)


class ProgrammeClasse(models.Model):
    """Matières enseignées dans une classe pour une année."""

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='programmes',
        verbose_name='Année scolaire',
    )
    classe = models.ForeignKey(
        'ecoles.Classe',
        on_delete=models.CASCADE,
        related_name='programmes',
        verbose_name='Classe',
    )
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.CASCADE,
        related_name='programmes',
        verbose_name='Matière',
    )
    maximum = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Maximum (override)',
    )
    ordre = models.PositiveSmallIntegerField(default=1, verbose_name='Ordre')

    class Meta:
        verbose_name = 'Programme de classe'
        verbose_name_plural = 'Programmes de classe'
        ordering = ['ordre', 'matiere__nom']
        constraints = [
            models.UniqueConstraint(
                fields=['annee', 'classe', 'matiere'],
                name='uniq_programme_classe_matiere',
            ),
        ]

    def __str__(self):
        return f'{self.classe.nom} — {self.matiere.nom}'

    @property
    def maximum_effectif(self):
        return self.maximum if self.maximum is not None else self.matiere.maximum


class Note(models.Model):
    """Note d'un élève pour une matière et une période."""

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='Élève',
    )
    programme = models.ForeignKey(
        ProgrammeClasse,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='Programme',
    )
    periode = models.ForeignKey(
        PeriodeEvaluation,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='Période',
    )
    valeur = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Note',
    )
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_saisies',
        verbose_name='Saisi par',
    )
    date_saisie = models.DateTimeField(auto_now=True, verbose_name='Date de saisie')

    class Meta:
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'
        ordering = ['eleve__nom', 'programme__ordre']
        constraints = [
            models.UniqueConstraint(
                fields=['eleve', 'programme', 'periode'],
                name='uniq_note_eleve_programme_periode',
            ),
        ]

    def __str__(self):
        return f'{self.eleve} — {self.programme.matiere.nom} — {self.periode.code}: {self.valeur}'


class BulletinDecision(models.Model):
    """Décision de fin d'année / mentions du bulletin (modèle RDC)."""

    class Decision(models.TextChoices):
        PASSE = 'passe', 'Passe'
        DOUBLE = 'double', 'Double'
        APPLICATION = 'application', 'Application'
        EN_ATTENTE = 'en_attente', 'En attente'

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='bulletins',
        verbose_name='Élève',
    )
    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='bulletins',
        verbose_name='Année scolaire',
    )
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        default=Decision.EN_ATTENTE,
        verbose_name='Décision',
    )
    conduite = models.CharField(max_length=80, blank=True, verbose_name='Conduite')
    appreciation = models.TextField(blank=True, verbose_name='Appréciation')
    place = models.PositiveIntegerField(null=True, blank=True, verbose_name='Place')
    effectif = models.PositiveIntegerField(null=True, blank=True, verbose_name='Effectif classe')
    total_obtenu = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Total obtenu',
    )
    total_max = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Total maximal',
    )
    pourcentage = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Pourcentage',
    )
    date_decision = models.DateField(null=True, blank=True, verbose_name='Date de décision')
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Décision de bulletin'
        verbose_name_plural = 'Décisions de bulletin'
        constraints = [
            models.UniqueConstraint(fields=['eleve', 'annee'], name='uniq_bulletin_eleve_annee'),
        ]

    def __str__(self):
        return f'Bulletin {self.eleve} — {self.annee.libelle}'
