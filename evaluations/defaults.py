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
    ('Religion', 'REL', '10', 1),
    ('Ed. civ. & morale', 'ECM', '10', 2),
    ('Education à la Vie', 'EV', '10', 3),
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
    ('Coupe', 'COUPE', '40', 20),
    ('Cours ménagers', 'CMEN', '40', 21),
    ('Couture industrielle', 'CIND', '40', 22),
    ('Exercices techniques', 'EXTECH', '40', 23),
    ('Français', 'FR', '40', 24),
    ('Couture artisanale', 'CART', '50', 30),
]

# Humanités générales (hors métier technique) — fallback secondaire
MATIERES_HUMANITES = [
    ('Religion', 'REL', '10', 1),
    ('Ed. civ. & morale', 'ECM', '10', 2),
    ('Education à la Vie', 'EV', '10', 3),
    ('Français', 'FR', '40', 10),
    ('Anglais', 'ANG', '20', 11),
    ('Mathématiques', 'MATH', '20', 12),
    ('Histoire', 'HIST', '20', 13),
    ('Géographie', 'GEO', '20', 14),
    ('Sciences', 'SCI', '20', 15),
    ('Informatique', 'INFO', '20', 16),
    ('Education phys. & sportive', 'EPS', '20', 17),
]

# Section Littéraire · Latin-Philosophie (1ère–4ème humanités)
MATIERES_LATIN_PHILO = [
    ('Religion', 'REL', '10', 1),
    ('Ed. civ. & morale', 'ECM', '10', 2),
    ('Education à la Vie', 'EV', '10', 3),
    ('Français', 'FR', '40', 10),
    ('Latin', 'LAT', '40', 11),
    ('Philosophie', 'PHILO', '20', 12),
    ('Anglais', 'ANG', '20', 13),
    ('Histoire', 'HIST', '20', 14),
    ('Géographie', 'GEO', '20', 15),
    ('Mathématiques', 'MATH', '20', 16),
    ('Sciences', 'SCI', '20', 17),
    ('Informatique', 'INFO', '20', 18),
    ('Education phys. & sportive', 'EPS', '20', 19),
]

MATIERES_LATIN_GREC = [
    ('Religion', 'REL', '10', 1),
    ('Ed. civ. & morale', 'ECM', '10', 2),
    ('Education à la Vie', 'EV', '10', 3),
    ('Français', 'FR', '40', 10),
    ('Latin', 'LAT', '40', 11),
    ('Grec', 'GREC', '40', 12),
    ('Anglais', 'ANG', '20', 13),
    ('Histoire', 'HIST', '20', 14),
    ('Géographie', 'GEO', '20', 15),
    ('Mathématiques', 'MATH', '20', 16),
    ('Sciences', 'SCI', '20', 17),
    ('Informatique', 'INFO', '20', 18),
    ('Education phys. & sportive', 'EPS', '20', 19),
]

_CATALOGUE_PAR_CODE_OPTION = {
    'COUPE': MATIERES_SECONDAIRE,
    'LP': MATIERES_LATIN_PHILO,
    'LG': MATIERES_LATIN_GREC,
}

_CATALOGUE_PAR_NOM_OPTION = {
    'coupe et couture': MATIERES_SECONDAIRE,
    'latin-philosophie': MATIERES_LATIN_PHILO,
    'latin philosophie': MATIERES_LATIN_PHILO,
    'latin-grec': MATIERES_LATIN_GREC,
    'latin grec': MATIERES_LATIN_GREC,
}

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


def matieres_catalogue(regime: str, option=None):
    """Catalogue de branches selon le régime et l'option (pas Coupe par défaut)."""
    if regime == AnneeScolaire.Regime.PRIMAIRE:
        return MATIERES_PRIMAIRE
    if option is not None:
        code = (getattr(option, 'code', None) or '').strip().upper().replace(' ', '-')
        if code and code in _CATALOGUE_PAR_CODE_OPTION:
            return _CATALOGUE_PAR_CODE_OPTION[code]
        nom = (getattr(option, 'nom', None) or '').strip().lower()
        nom = nom.replace('—', '-').replace('–', '-').replace('_', '-')
        if nom in _CATALOGUE_PAR_NOM_OPTION:
            return _CATALOGUE_PAR_NOM_OPTION[nom]
        if 'latin' in nom and 'philo' in nom:
            return MATIERES_LATIN_PHILO
        if 'latin' in nom and 'grec' in nom:
            return MATIERES_LATIN_GREC
        if 'coupe' in nom and 'couture' in nom:
            return MATIERES_SECONDAIRE
    return MATIERES_HUMANITES


def matieres_queryset_pour_classe(qs, classe, *, mode='programme'):
    """
    Filtre les matières pertinentes pour une classe.

    mode='strict'    : uniquement les matières rattachées à cette classe
    mode='programme' : cette classe + catalogue option/section (classe non précisée)
    mode='liste'     : identique à programme (jamais les matières d’une autre classe)
    """
    from django.db.models import Q

    if not classe:
        return qs.none()
    if mode == 'strict':
        return qs.filter(classe_id=classe.id)
    q = Q(classe_id=classe.id)
    if classe.option_id:
        q |= Q(option_id=classe.option_id, classe__isnull=True)
    elif classe.section_id:
        q |= Q(section_id=classe.section_id, option__isnull=True, classe__isnull=True)
    return qs.filter(q).distinct()


def assurer_section_option_classe(ecole_id: int, regime: str, classe_id: int | None = None):
    """
    Garantit une section/option (et classe cible) pour rattacher le catalogue.
    N'installe que l'option minimale utile — jamais tout le référentiel RDC.
    Retourne (section, option, classe).
    """
    from ecoles.models import Classe, OptionScolaire, SectionScolaire
    from ecoles.programme_rdc import assurer_option_referentiel

    classe = None
    if classe_id:
        classe = Classe.objects.select_related('section', 'option').filter(
            pk=classe_id, ecole_id=ecole_id,
        ).first()
        if classe and classe.section_id and classe.option_id:
            return classe.section, classe.option, classe

    # Une seule option du référentiel (celle déjà offerte par l'école, sinon défaut)
    if regime == AnneeScolaire.Regime.PRIMAIRE:
        opt_code, sec_nom, opt_nom = 'TC-PRIM', 'Enseignement primaire', 'Tronc commun'
        niveau = 'primaire'
    else:
        opt_code, sec_nom, opt_nom = 'COUPE', 'Technique — Cycle court', 'Coupe et Couture'
        niveau = 'secondaire'

    # Préférer une option déjà organisée par l'école
    option = (
        OptionScolaire.objects.select_related('section')
        .filter(section__ecole_id=ecole_id, active=True)
        .order_by('section__nom', 'nom')
        .first()
    )
    section = option.section if option else None

    if not option:
        section, option = assurer_option_referentiel(ecole_id, opt_code, niveau=niveau)

    if not section:
        section = SectionScolaire.objects.filter(ecole_id=ecole_id, nom=sec_nom).first()
    if not option and section:
        option = OptionScolaire.objects.filter(section=section, nom=opt_nom).first()

    if classe and section and option:
        classe.section = section
        classe.option = option
        classe.save(update_fields=['section', 'option'])
        return section, option, classe

    if option and not classe:
        classe = Classe.objects.filter(ecole_id=ecole_id, option=option).order_by('nom').first()

    return section, option, classe


def synchroniser_matieres_ecole(
    ecole_id: int,
    regime: str = AnneeScolaire.Regime.SECONDAIRE,
    classe_id: int | None = None,
    section_id: int | None = None,
    option_id: int | None = None,
) -> dict:
    """
    Intègre le catalogue bulletin officiel pour une section / option / classe.
    """
    from ecoles.models import Classe, OptionScolaire, SectionScolaire
    from .models import Matiere

    section = option = classe = None
    if classe_id:
        classe = Classe.objects.select_related('section', 'option').filter(
            pk=classe_id, ecole_id=ecole_id,
        ).first()
        if classe:
            section = classe.section
            option = classe.option
    if option_id and not option:
        option = OptionScolaire.objects.select_related('section').filter(
            pk=option_id, section__ecole_id=ecole_id,
        ).first()
        if option:
            section = option.section
    if section_id and not section:
        section = SectionScolaire.objects.filter(pk=section_id, ecole_id=ecole_id).first()

    if not section or not option:
        section, option, classe = assurer_section_option_classe(ecole_id, regime, classe_id)

    # Alias uniquement dans le même scope
    for ancien, nouveau in ALIAS_MATIERES.items():
        qs_ancien = Matiere.objects.filter(
            ecole_id=ecole_id, nom=ancien,
            section=section, option=option, classe=classe,
        )
        if not qs_ancien.exists():
            continue
        if Matiere.objects.filter(
            ecole_id=ecole_id, nom=nouveau,
            section=section, option=option, classe=classe,
        ).exists():
            qs_ancien.update(active=False)
        else:
            qs_ancien.update(nom=nouveau)

    created = 0
    updated = 0
    for nom, code, maximum, ordre in matieres_catalogue(regime, option=option):
        obj, was_created = Matiere.objects.get_or_create(
            ecole_id=ecole_id,
            nom=nom,
            section=section,
            option=option,
            classe=classe,
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
        for field, value in (
            ('code', code),
            ('maximum', Decimal(maximum)),
            ('ordre', ordre),
            ('active', True),
        ):
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed = True
        if changed:
            obj.save()
            updated += 1
    return {
        'created': created,
        'updated': updated,
        'total': created + updated,
        'section_id': section.id if section else None,
        'option_id': option.id if option else None,
        'classe_id': classe.id if classe else None,
    }


def _regime_pour_classe(classe, annee_id=None):
    if annee_id:
        annee = AnneeScolaire.objects.filter(pk=annee_id).first()
        if annee and annee.regime:
            return annee.regime
    from ecoles.models import Ecole
    ecole = getattr(classe, 'ecole', None)
    if ecole and getattr(ecole, 'niveau', None) == Ecole.Niveau.PRIMAIRE:
        return AnneeScolaire.Regime.PRIMAIRE
    return AnneeScolaire.Regime.SECONDAIRE


def assurer_programme_classe(annee_id, classe) -> dict:
    """
    Garantit un programme de notes pour la classe / année :
    rattache les matières existantes, sinon copie le catalogue d'option,
    sinon installe le catalogue officiel de cette option sur la classe.
    """
    from .models import Matiere, ProgrammeClasse

    if not annee_id or not classe:
        return {'created': 0, 'matieres': 0}

    ecole_id = classe.ecole_id
    regime = _regime_pour_classe(classe, annee_id)

    matieres = Matiere.objects.filter(
        ecole_id=ecole_id, active=True, classe_id=classe.id,
    )
    if not matieres.exists():
        sources = matieres_queryset_pour_classe(
            Matiere.objects.filter(ecole_id=ecole_id, active=True),
            classe,
            mode='programme',
        )
        ids = []
        for src in sources.order_by('ordre', 'nom'):
            obj, _ = Matiere.objects.get_or_create(
                ecole_id=ecole_id,
                nom=src.nom,
                section_id=classe.section_id,
                option_id=classe.option_id,
                classe=classe,
                defaults={
                    'code': src.code,
                    'maximum': src.maximum,
                    'ordre': src.ordre,
                    'active': True,
                },
            )
            ids.append(obj.id)
        matieres = Matiere.objects.filter(pk__in=ids) if ids else matieres

    if not matieres.exists():
        synchroniser_matieres_ecole(ecole_id, regime, classe_id=classe.id)
        matieres = Matiere.objects.filter(
            ecole_id=ecole_id, active=True, classe_id=classe.id,
        )

    created = 0
    for m in matieres.order_by('ordre', 'nom'):
        _, was = ProgrammeClasse.objects.get_or_create(
            annee_id=annee_id,
            classe=classe,
            matiere=m,
            defaults={'ordre': m.ordre, 'maximum': m.maximum},
        )
        if was:
            created += 1
    return {'created': created, 'matieres': matieres.count()}
