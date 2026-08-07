"""Périodes et matières types selon le régime RDC."""
from decimal import Decimal

from .models import AnneeScolaire, PeriodeEvaluation


PERIODES_SECONDAIRE = [
    # code, libelle, type, semestre, ordre, facteur_max
    ('p1', '1ère Période', PeriodeEvaluation.TypePeriode.TRAVAUX, 1, 1, '1'),
    ('p2', '2ème Période', PeriodeEvaluation.TypePeriode.TRAVAUX, 1, 2, '1'),
    ('exam1', 'Examen 1er Semestre', PeriodeEvaluation.TypePeriode.EXAMEN, 1, 3, '2'),
    ('p3', '3ème Période', PeriodeEvaluation.TypePeriode.TRAVAUX, 2, 4, '1'),
    ('p4', '4ème Période', PeriodeEvaluation.TypePeriode.TRAVAUX, 2, 5, '1'),
    ('exam2', 'Examen 2ème Semestre', PeriodeEvaluation.TypePeriode.EXAMEN, 2, 6, '2'),
]

PERIODES_PRIMAIRE = [
    ('t1', '1er Trimestre', PeriodeEvaluation.TypePeriode.TRIMESTRE, 1, 1, '1'),
    ('t2', '2ème Trimestre', PeriodeEvaluation.TypePeriode.TRIMESTRE, 1, 2, '1'),
    ('t3', '3ème Trimestre', PeriodeEvaluation.TypePeriode.TRIMESTRE, 1, 3, '1'),
]

# Branches extraites du bulletin officiel IGE/EPSP./172
# (modèle : 1ère Année Coupe et Couture / Cycle court)
# Tuple : (nom, code, maximum TJ, ordre)
MATIERES_SECONDAIRE = [
    # MAXIMA 10 → Exam 20 · Tot 40 · T.G. 80
    ('Religion', 'REL', '10', 1),
    ('Ed. civ. & morale', 'ECM', '10', 2),
    ('Education à la Vie', 'EV', '10', 3),
    # MAXIMA 20 → Exam 40 · Tot 80 · T.G. 160
    ('Arithm. géométrie', 'MATH', '20', 10),
    ('Education familiale', 'EFAM', '20', 11),
    ('Education plastique', 'EPL', '20', 12),
    ('Education phys. & sportive', 'EPS', '20', 13),
    ('Ess. moul. / Drapage', 'EMD', '20', 14),
    ('Histoire et géogr.', 'HG', '20', 15),
    ('Informatique', 'INFO', '20', 16),
    ('Organisation du travail', 'ORG', '20', 17),
    ('Techno. des textiles', 'TTEX', '20', 18),
    ('Techno. du métier', 'TMET', '20', 19),
    # MAXIMA 40 → Exam 80 · Tot 160 · T.G. 320
    ('Coupe', 'COUPE', '40', 20),
    ('Cours ménagers', 'CMEN', '40', 21),
    ('Couture industrielle', 'CIND', '40', 22),
    ('Exercices techniques', 'EXTECH', '40', 23),
    ('Français', 'FR', '40', 24),
    # MAXIMA 50 → Exam 100 · Tot 200 · T.G. 400
    ('Couture artisanale', 'CART', '50', 30),
]

MATIERES_PRIMAIRE = [
    ('Langue congolaise', 'LC', '10', 1),
    ('Français', 'FR', '20', 2),
    ('Mathématiques', 'MATH', '20', 3),
    ('Éducation scientifique', 'ES', '10', 4),
    ('Éducation à la vie', 'EV', '10', 5),
    ('Arts plastiques', 'ART', '10', 6),
    ('Éducation physique', 'EP', '10', 7),
    ('Religion / Morale', 'REL', '10', 8),
]


# Anciens libellés → nom officiel (migration douce lors du chargement catalogue)
ALIAS_MATIERES = {
    'Éducation civique & morale': 'Ed. civ. & morale',
    'Éducation à la Vie': 'Education à la Vie',
    'Éducation à la vie': 'Education à la Vie',
    'Arithmétique / Géométrie': 'Arithm. géométrie',
    'Éducation physique & sportive': 'Education phys. & sportive',
    'Histoire et géographie': 'Histoire et géogr.',
}


def creer_periodes_pour_annee(annee: AnneeScolaire) -> int:
    """Crée les périodes standard si absentes. Retourne le nombre créé."""
    specs = (
        PERIODES_PRIMAIRE
        if annee.regime == AnneeScolaire.Regime.PRIMAIRE
        else PERIODES_SECONDAIRE
    )
    created = 0
    for code, libelle, typ, semestre, ordre, facteur in specs:
        _, was_created = PeriodeEvaluation.objects.get_or_create(
            annee=annee,
            code=code,
            defaults={
                'libelle': libelle,
                'type_periode': typ,
                'semestre': semestre,
                'ordre': ordre,
                'facteur_maximum': Decimal(facteur),
            },
        )
        if was_created:
            created += 1
    return created


def matieres_catalogue(regime: str):
    if regime == AnneeScolaire.Regime.PRIMAIRE:
        return MATIERES_PRIMAIRE
    return MATIERES_SECONDAIRE


def synchroniser_matieres_ecole(ecole_id: int, regime: str = AnneeScolaire.Regime.SECONDAIRE) -> dict:
    """
    Intègre le catalogue bulletin officiel dans la base pour une école.
    Crée les matières manquantes et met à jour code / maximum / ordre.
    """
    from .models import Matiere

    # Renommer les alias éventuels avant sync
    for ancien, nouveau in ALIAS_MATIERES.items():
        qs_ancien = Matiere.objects.filter(ecole_id=ecole_id, nom=ancien)
        if not qs_ancien.exists():
            continue
        if Matiere.objects.filter(ecole_id=ecole_id, nom=nouveau).exists():
            qs_ancien.update(active=False)
        else:
            qs_ancien.update(nom=nouveau)

    created = 0
    updated = 0
    for nom, code, maximum, ordre in matieres_catalogue(regime):
        obj, was_created = Matiere.objects.get_or_create(
            ecole_id=ecole_id,
            nom=nom,
            defaults={
                'code': code,
                'maximum': Decimal(maximum),
                'ordre': ordre,
                'active': True,
            },
        )
        if was_created:
            created += 1
            continue
        changed = False
        if obj.code != code:
            obj.code = code
            changed = True
        if obj.maximum != Decimal(maximum):
            obj.maximum = Decimal(maximum)
            changed = True
        if obj.ordre != ordre:
            obj.ordre = ordre
            changed = True
        if not obj.active:
            obj.active = True
            changed = True
        if changed:
            obj.save(update_fields=['code', 'maximum', 'ordre', 'active'])
            updated += 1
    return {'created': created, 'updated': updated, 'total': created + updated}
