"""
Référentiel des sections, options et classes conforme au programme EPSP / MEPST RDC
(Ministère de l'Éducation nationale — structure officielle des niveaux).

Sources (préscolaire) :
- MINEDU-NC : enseignement préscolaire en 3 années (1ère, 2ème, 3ème)
- Structures de préscolarisation : école maternelle, espace communautaire
  d'éveil (ECE), classe pré-primaire ; crèche pour la petite enfance (< 3 ans)

Chaque école n'organise qu'un sous-ensemble : le chargement est sélectif
(options choisies), jamais l'intégralité du catalogue par défaut.
"""
from __future__ import annotations

from .models import Classe, OptionScolaire, SectionScolaire


# ---------------------------------------------------------------------------
# CRÈCHE (petite enfance, typiquement 0–3 ans)
# ---------------------------------------------------------------------------
PROGRAMME_CRECHE = {
    'sections': [
        {
            'nom': 'Crèche',
            'code': 'CRECHE',
            'options': [
                {
                    'nom': 'Tronc commun crèche',
                    'code': 'TC-CRECHE',
                    'classes': [
                        ('Petite crèche (0–1 an)', 'PC'),
                        ('Moyenne crèche (1–2 ans)', 'MC'),
                        ('Grande crèche (2–3 ans)', 'GC'),
                    ],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# MATERNELLE / PRÉSCOLAIRE (3–5 ans — 3 années)
# ---------------------------------------------------------------------------
CLASSES_MATERNELLE_3 = [
    ('1ère année maternelle (G1)', '1M'),
    ('2ème année maternelle (G2)', '2M'),
    ('3ème année maternelle (G3)', '3M'),
]

PROGRAMME_MATERNELLE = {
    'sections': [
        {
            'nom': 'Enseignement maternel',
            'code': 'MAT',
            'options': [
                {
                    'nom': 'École maternelle',
                    'code': 'TC-MAT',
                    'classes': CLASSES_MATERNELLE_3,
                },
                {
                    'nom': 'Espace communautaire d\'éveil (ECE)',
                    'code': 'ECE',
                    'classes': CLASSES_MATERNELLE_3,
                },
                {
                    'nom': 'Classe pré-primaire',
                    'code': 'PREPRIM',
                    'classes': [
                        ('Classe pré-primaire', 'PREP'),
                    ],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# PRIMAIRE
# ---------------------------------------------------------------------------
PROGRAMME_PRIMAIRE = {
    'sections': [
        {
            'nom': 'Enseignement primaire',
            'code': 'PRIM',
            'options': [
                {
                    'nom': 'Tronc commun',
                    'code': 'TC-PRIM',
                    'classes': [
                        ('1ère année primaire', '1P'),
                        ('2ème année primaire', '2P'),
                        ('3ème année primaire', '3P'),
                        ('4ème année primaire', '4P'),
                        ('5ème année primaire', '5P'),
                        ('6ème année primaire', '6P'),
                    ],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# SECONDAIRE
# ---------------------------------------------------------------------------
CLASSES_CTEB = [
    ('7ème CTÉB', '7E'),
    ('8ème CTÉB', '8E'),
]

CLASSES_HUMANITES_4 = [
    ('1ère humanités', '1H'),
    ('2ème humanités', '2H'),
    ('3ème humanités', '3H'),
    ('4ème humanités', '4H'),
]

CLASSES_CYCLE_COURT_3 = [
    ('1ère cycle court', '1CC'),
    ('2ème cycle court', '2CC'),
    ('3ème cycle court', '3CC'),
]

CLASSES_CYCLE_LONG_4 = [
    ('1ère cycle long', '1CL'),
    ('2ème cycle long', '2CL'),
    ('3ème cycle long', '3CL'),
    ('4ème cycle long', '4CL'),
]


PROGRAMME_SECONDAIRE = {
    'sections': [
        {
            'nom': 'Secondaire général (CTÉB)',
            'code': 'CTEB',
            'options': [
                {
                    'nom': 'Tronc commun CTÉB',
                    'code': 'TC-CTEB',
                    'classes': CLASSES_CTEB,
                },
            ],
        },
        {
            'nom': 'Scientifique',
            'code': 'SC',
            'options': [
                {
                    'nom': 'Mathématique-Physique',
                    'code': 'MP',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Chimie-Biologie',
                    'code': 'CB',
                    'classes': CLASSES_HUMANITES_4,
                },
            ],
        },
        {
            'nom': 'Littéraire',
            'code': 'LIT',
            'options': [
                {
                    'nom': 'Latin-Philosophie',
                    'code': 'LP',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Latin-Grec',
                    'code': 'LG',
                    'classes': CLASSES_HUMANITES_4,
                },
            ],
        },
        {
            'nom': 'Pédagogique',
            'code': 'PED',
            'options': [
                {
                    'nom': 'Pédagogie générale',
                    'code': 'PG',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Normale',
                    'code': 'NORM',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Éducation physique',
                    'code': 'EP',
                    'classes': CLASSES_HUMANITES_4,
                },
            ],
        },
        {
            'nom': 'Commerciale et Gestion',
            'code': 'CG',
            'options': [
                {
                    'nom': 'Commerciale et Gestion',
                    'code': 'CG-OPT',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Secrétariat',
                    'code': 'SECR',
                    'classes': CLASSES_HUMANITES_4,
                },
            ],
        },
        {
            'nom': 'Technique — Cycle court',
            'code': 'TECH-CC',
            'options': [
                {'nom': 'Coupe et Couture', 'code': 'COUPE', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Électricité', 'code': 'ELEC', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Électronique', 'code': 'ELN', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Mécanique générale', 'code': 'MECA', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Mécanique automobile', 'code': 'AUTO', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Construction', 'code': 'CONST', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Menuiserie', 'code': 'MEN', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Agriculture', 'code': 'AGRI', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Hôtellerie et Tourisme', 'code': 'HOT', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Informatique', 'code': 'INFO', 'classes': CLASSES_CYCLE_COURT_3},
                {'nom': 'Coupe et Couture industrielle', 'code': 'COUPE-I', 'classes': CLASSES_CYCLE_COURT_3},
            ],
        },
        {
            'nom': 'Technique — Cycle long',
            'code': 'TECH-CL',
            'options': [
                {'nom': 'Électricité', 'code': 'ELEC-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Électronique', 'code': 'ELN-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Mécanique générale', 'code': 'MECA-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Mécanique automobile', 'code': 'AUTO-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Construction', 'code': 'CONST-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Agriculture', 'code': 'AGRI-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Industrie d\'habillement', 'code': 'IHAB', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Informatique', 'code': 'INFO-L', 'classes': CLASSES_CYCLE_LONG_4},
                {'nom': 'Chimie industrielle', 'code': 'CHIM-I', 'classes': CLASSES_CYCLE_LONG_4},
            ],
        },
        {
            'nom': 'Arts et Métiers',
            'code': 'ARTS',
            'options': [
                {
                    'nom': 'Arts plastiques',
                    'code': 'AP',
                    'classes': CLASSES_HUMANITES_4,
                },
                {
                    'nom': 'Musique',
                    'code': 'MUS',
                    'classes': CLASSES_HUMANITES_4,
                },
            ],
        },
    ],
}


def _blocs_pour_niveau(niveau: str) -> list[dict]:
    """
    Filtre le catalogue EPSP par niveau d'enseignement.
    - creche / crèche
    - maternelle
    - prescolaire = crèche + maternelle
    - primaire | secondaire | tous
    """
    niveau = (niveau or 'tous').lower().replace('è', 'e').replace('é', 'e').replace('ê', 'e')
    blocs = []
    if niveau in ('creche', 'prescolaire', 'tous', 'all'):
        blocs.append(PROGRAMME_CRECHE)
    if niveau in ('maternelle', 'prescolaire', 'tous', 'all'):
        blocs.append(PROGRAMME_MATERNELLE)
    if niveau in ('primaire', 'tous', 'all'):
        blocs.append(PROGRAMME_PRIMAIRE)
    if niveau in ('secondaire', 'tous', 'all'):
        blocs.append(PROGRAMME_SECONDAIRE)
    return blocs


def iter_options_referentiel(niveau: str = 'tous'):
    """Itère (section_spec, option_spec) du référentiel EPSP."""
    for bloc in _blocs_pour_niveau(niveau):
        for sec in bloc['sections']:
            for opt in sec['options']:
                yield sec, opt


def catalogue_referentiel_rdc(niveau: str = 'tous', ecole_id: int | None = None) -> dict:
    """
    Arbre du référentiel pour UI de sélection.
    Si ecole_id fourni, marque déjà_present / active pour chaque option.
    """
    present = {}
    if ecole_id:
        for opt in OptionScolaire.objects.filter(
            section__ecole_id=ecole_id,
        ).select_related('section'):
            key = (opt.section.code or opt.section.nom, opt.code or opt.nom)
            present[key] = {
                'id': opt.id,
                'active': opt.active,
                'section_id': opt.section_id,
            }
            # aussi index par code option seul
            if opt.code:
                present[opt.code] = present[key]

    sections_out = []
    for bloc in _blocs_pour_niveau(niveau):
        for sec in bloc['sections']:
            options_out = []
            for opt in sec['options']:
                key = (sec.get('code') or sec['nom'], opt.get('code') or opt['nom'])
                info = present.get(opt.get('code')) or present.get(key) or {}
                options_out.append({
                    'nom': opt['nom'],
                    'code': opt.get('code', ''),
                    'nb_classes': len(opt.get('classes') or []),
                    'deja_present': bool(info),
                    'active': info.get('active', False) if info else False,
                    'option_id': info.get('id'),
                })
            sections_out.append({
                'nom': sec['nom'],
                'code': sec.get('code', ''),
                'options': options_out,
            })
    return {'niveau': niveau, 'sections': sections_out}


def _filtrer_programme(
    programme: dict,
    option_codes: set[str] | None,
    section_codes: set[str] | None,
) -> dict:
    """Ne garde que les sections/options demandées."""
    if not option_codes and not section_codes:
        return programme

    sections = []
    for sec in programme['sections']:
        sec_code = (sec.get('code') or '').upper()
        if section_codes and sec_code in section_codes:
            sections.append(sec)
            continue
        if option_codes:
            opts = [
                o for o in sec['options']
                if (o.get('code') or '').upper() in option_codes
            ]
            if opts:
                sections.append({**sec, 'options': opts})
    return {'sections': sections}


def _charger_bloc(ecole_id: int, programme: dict) -> dict:
    sections_c = options_c = classes_c = 0
    sections_u = options_u = classes_u = 0

    for sec_spec in programme['sections']:
        section, created = SectionScolaire.objects.get_or_create(
            ecole_id=ecole_id,
            nom=sec_spec['nom'],
            defaults={'code': sec_spec.get('code', ''), 'active': True},
        )
        if created:
            sections_c += 1
        else:
            changed = False
            if sec_spec.get('code') and section.code != sec_spec['code']:
                section.code = sec_spec['code']
                changed = True
            if not section.active:
                section.active = True
                changed = True
            if changed:
                section.save()
                sections_u += 1

        for opt_spec in sec_spec['options']:
            option, created = OptionScolaire.objects.get_or_create(
                section=section,
                nom=opt_spec['nom'],
                defaults={'code': opt_spec.get('code', ''), 'active': True},
            )
            if created:
                options_c += 1
            else:
                changed = False
                if opt_spec.get('code') and option.code != opt_spec['code']:
                    option.code = opt_spec['code']
                    changed = True
                if not option.active:
                    option.active = True
                    changed = True
                if changed:
                    option.save()
                    options_u += 1

            for nom_classe, code_classe in opt_spec.get('classes', []):
                code_opt = (opt_spec.get('code') or '')
                # Tronc commun / structures unitaires : nom de classe court
                if code_opt.startswith(('TC-PRIM', 'TC-CRECHE', 'TC-MAT', 'ECE', 'PREPRIM')):
                    nom_complet = nom_classe
                    code_complet = code_classe
                else:
                    nom_complet = f'{nom_classe} — {opt_spec["nom"]}'
                    code_opt_short = code_opt[:12]
                    code_complet = f'{code_classe}-{code_opt_short}' if code_opt_short else code_classe
                if len(nom_complet) > 100:
                    nom_complet = nom_complet[:100]
                classe, created = Classe.objects.get_or_create(
                    ecole_id=ecole_id,
                    nom=nom_complet,
                    defaults={
                        'code': code_complet[:30],
                        'section': section,
                        'option': option,
                        'active': True,
                    },
                )
                if created:
                    classes_c += 1
                else:
                    changed = False
                    if classe.section_id != section.id:
                        classe.section = section
                        changed = True
                    if classe.option_id != option.id:
                        classe.option = option
                        changed = True
                    if code_complet and classe.code != code_complet[:30]:
                        classe.code = code_complet[:30]
                        changed = True
                    if not classe.active:
                        classe.active = True
                        changed = True
                    if changed:
                        classe.save()
                        classes_u += 1

    return {
        'sections_created': sections_c,
        'sections_updated': sections_u,
        'options_created': options_c,
        'options_updated': options_u,
        'classes_created': classes_c,
        'classes_updated': classes_u,
    }


def charger_programme_rdc(
    ecole_id: int,
    niveau: str = 'tous',
    *,
    option_codes: list[str] | None = None,
    section_codes: list[str] | None = None,
    tout: bool = False,
) -> dict:
    """
    Charge sections / options / classes pour une école.

    Par défaut exige option_codes ou section_codes (sélection école).
    tout=True charge l'intégralité du niveau (réservé CLI / migration).
    """
    niveau = (niveau or 'tous').lower().replace('è', 'e').replace('é', 'e').replace('ê', 'e')
    opt_set = {c.strip().upper() for c in (option_codes or []) if c and str(c).strip()}
    sec_set = {c.strip().upper() for c in (section_codes or []) if c and str(c).strip()}

    if not tout and not opt_set and not sec_set:
        raise ValueError(
            'Sélectionnez au moins une option (ou section) organisée par l\'école.'
        )

    result = {
        'sections_created': 0,
        'sections_updated': 0,
        'options_created': 0,
        'options_updated': 0,
        'classes_created': 0,
        'classes_updated': 0,
        'niveau': niveau,
        'option_codes': sorted(opt_set),
        'section_codes': sorted(sec_set),
    }

    for bloc in _blocs_pour_niveau(niveau):
        filtered = bloc if tout else _filtrer_programme(bloc, opt_set or None, sec_set or None)
        if not filtered['sections']:
            continue
        stats = _charger_bloc(ecole_id, filtered)
        for k, v in stats.items():
            result[k] = result.get(k, 0) + v

    result['total_created'] = (
        result['sections_created'] + result['options_created'] + result['classes_created']
    )
    result['total_updated'] = (
        result['sections_updated'] + result['options_updated'] + result['classes_updated']
    )
    return result


def assurer_option_referentiel(
    ecole_id: int,
    option_code: str,
    *,
    niveau: str = 'tous',
) -> tuple[SectionScolaire | None, OptionScolaire | None]:
    """Affecte uniquement une option du référentiel (sans tout le catalogue)."""
    code = (option_code or '').upper()
    if not code:
        return None, None
    charger_programme_rdc(ecole_id, niveau=niveau, option_codes=[code])
    option = OptionScolaire.objects.select_related('section').filter(
        section__ecole_id=ecole_id,
        code__iexact=code,
    ).first()
    if not option:
        return None, None
    return option.section, option


def assurer_structure_selon_niveau(ecole) -> dict:
    """
    Pour une école crèche / maternelle : garantit les options préscolaires EPSP
    (TC-CRECHE, TC-MAT, ECE, PREPRIM) si elles manquent encore.
    N'écrase pas les structures déjà présentes (primaire, etc.).
    """
    from .models import Ecole

    niveau = getattr(ecole, 'niveau', None)
    if niveau == Ecole.Niveau.CRECHE:
        codes = ['TC-CRECHE']
        niv_catalogue = 'creche'
    elif niveau == Ecole.Niveau.MATERNELLE:
        codes = ['TC-CRECHE', 'TC-MAT', 'ECE', 'PREPRIM']
        niv_catalogue = 'prescolaire'
    else:
        return {
            'skipped': True,
            'reason': 'niveau_non_prescolaire',
            'niveau': niveau,
            'option_codes': [],
        }

    existing = {
        (c or '').upper()
        for c in OptionScolaire.objects.filter(
            section__ecole_id=ecole.id,
            code__in=codes,
            active=True,
        ).values_list('code', flat=True)
    }
    missing = [c for c in codes if c not in existing]
    if not missing:
        return {
            'skipped': True,
            'reason': 'deja_present',
            'niveau': niveau,
            'option_codes': codes,
        }

    result = charger_programme_rdc(
        ecole.id,
        niveau=niv_catalogue,
        option_codes=missing,
        tout=False,
    )
    result['skipped'] = False
    result['niveau'] = niveau
    result['option_codes_ajoutees'] = missing
    return result


def affecter_structure_ecole(
    ecole_id: int,
    option_codes: list[str],
    *,
    niveau: str = 'tous',
) -> dict:
    """Affecte des options du référentiel EPSP à une école (sections + classes)."""
    return charger_programme_rdc(
        ecole_id,
        niveau=niveau,
        option_codes=option_codes,
        tout=False,
    )


def retirer_structure_ecole(ecole_id: int, option_codes: list[str]) -> dict:
    """
    Retire (désactive) des options affectées à l'école et leurs classes.
    Ne supprime pas les enregistrements (préserve les liens élèves / notes).
    """
    codes = {c.strip().upper() for c in (option_codes or []) if c and str(c).strip()}
    if not codes:
        raise ValueError('Sélectionnez au moins une option à retirer.')

    options = OptionScolaire.objects.filter(
        section__ecole_id=ecole_id,
        code__in=codes,
    ).select_related('section')
    opt_ids = list(options.values_list('id', flat=True))
    sections_ids = list(options.values_list('section_id', flat=True))

    classes_n = Classe.objects.filter(ecole_id=ecole_id, option_id__in=opt_ids).update(active=False)
    options_n = options.update(active=False)

    # Désactiver les sections sans plus aucune option active
    sections_n = 0
    for sid in set(sections_ids):
        if not OptionScolaire.objects.filter(section_id=sid, active=True).exists():
            updated = SectionScolaire.objects.filter(pk=sid, active=True).update(active=False)
            sections_n += updated

    return {
        'options_retirees': options_n,
        'classes_retirees': classes_n,
        'sections_retirees': sections_n,
        'option_codes': sorted(codes),
    }
