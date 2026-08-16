"""
Matrice des permissions réellement implémentées dans Educ_RDC.

Source de vérité pour l'affichage admin (page Gestion de permissions).
Les niveaux reflètent le comportement UI + API actuel, pas une ambition future.
"""

# write | read | partial | denied | na
NIVEAUX = {
    'write': {'label': 'Écriture', 'badge': 'badge-success', 'court': 'Écriture'},
    'read': {'label': 'Lecture seule', 'badge': 'badge-info', 'court': 'Lecture'},
    'partial': {'label': 'Partiel', 'badge': 'badge-warning', 'court': 'Partiel'},
    'denied': {'label': 'Interdit', 'badge': 'badge-danger', 'court': 'Interdit'},
    'na': {'label': 'Non applicable', 'badge': 'badge-neutral', 'court': 'N/A'},
}

ROLES = [
    {
        'code': 'admin',
        'label': 'Administrateur',
        'scope': 'National (tous les territoires)',
        'resume': (
            'Accès complet à la plateforme hors module Évaluation (réservé à l’école) : '
            'référentiels, écoles, élèves, utilisateurs et monitoring.'
        ),
    },
    {
        'code': 'agent_national',
        'label': 'Agent National',
        'scope': 'National (tous les territoires)',
        'resume': (
            'Même périmètre métier que l’administrateur (écoles, élèves, '
            'référentiels), sans évaluations, comptes ni monitoring.'
        ),
    },
    {
        'code': 'agent_province_admin',
        'label': 'Agent Province administrative',
        'scope': 'Province administrative rattachée',
        'resume': (
            'Chef hiérarchique des agents PE : mêmes droits de consultation '
            'territoriale, avec une vue d’ensemble des provinces éducationnelles.'
        ),
    },
    {
        'code': 'agent_provincial',
        'label': 'Agent Province éducationnelle',
        'scope': 'Province éducationnelle rattachée',
        'resume': (
            'Consultation des écoles et élèves de sa PE. Pas d’écriture, '
            'pas d’évaluation, pas de gestion documentaire ni utilisateurs.'
        ),
    },
    {
        'code': 'agent_antenne',
        'label': 'Agent Antenne',
        'scope': 'Antenne rattachée',
        'resume': (
            'Mêmes restrictions que l’agent PE, limitées à son antenne. '
            'Dashboard et rapports centrés sur les écoles de l’antenne.'
        ),
    },
    {
        'code': 'admin_ecole',
        'label': 'Administratif école',
        'scope': 'École rattachée',
        'resume': (
            'Gère sa fiche école, ses élèves, le programme d’évaluation et les comptes '
            'admin_ecole / enseignant de son établissement (sans saisie des notes).'
        ),
    },
    {
        'code': 'enseignant',
        'label': 'Enseignant',
        'scope': 'Classe titulaire',
        'resume': (
            'Consulte les élèves de sa classe, met à jour leur photo, '
            'saisit les notes et exporte listes / bulletins de classe.'
        ),
    },
]

# Lignes de la matrice : capacité → niveau par rôle
CAPACITES = [
    {
        'id': 'dashboard',
        'domaine': 'Navigation',
        'libelle': 'Tableau de bord',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'write',
            'agent_provincial': 'write',
            'agent_antenne': 'write',
            'admin_ecole': 'write',
            'enseignant': 'write',
        },
        'notes': {
            'agent_province_admin': 'KPI provinces éduc. / écoles / élèves de la PA',
            'agent_provincial': 'KPI antennes / écoles / élèves de la PE',
            'agent_antenne': 'KPI écoles / élèves de l’antenne',
            'admin_ecole': 'Effectifs et personnel de l’école',
            'enseignant': 'Effectif de la classe (garçons / filles)',
        },
    },
    {
        'id': 'menu_ecoles',
        'domaine': 'Navigation',
        'libelle': 'Menu Écoles / Mon école',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'denied',
        },
        'notes': {
            'admin_ecole': 'Redirigé vers « Mon école »',
            'enseignant': 'Menu masqué',
        },
    },
    {
        'id': 'menu_eleves',
        'domaine': 'Navigation',
        'libelle': 'Menu Élèves',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'read',
        },
    },
    {
        'id': 'menu_evaluations',
        'domaine': 'Navigation',
        'libelle': 'Menu Évaluation',
        'niveaux': {
            'admin': 'denied',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'write',
            'enseignant': 'write',
        },
        'notes': {
            'admin': 'Module réservé à l’école',
            'agent_national': 'Module réservé à l’école',
            'agent_province_admin': 'Redirection dashboard',
            'agent_provincial': 'Redirection dashboard',
            'agent_antenne': 'Redirection dashboard',
        },
    },
    {
        'id': 'menu_docs',
        'domaine': 'Navigation',
        'libelle': 'Gestion documentaire',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
    },
    {
        'id': 'menu_rapports',
        'domaine': 'Navigation',
        'libelle': 'Menu Rapports',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'partial',
        },
        'notes': {
            'agent_province_admin': 'Sans cartes / biométries ; KPI provinces éduc.',
            'agent_provincial': 'Sans cartes / biométries ; KPI antennes',
            'agent_antenne': 'Sans cartes / biométries',
            'enseignant': 'Exports PDF liste élèves / cours de classe',
        },
    },
    {
        'id': 'menu_utilisateurs',
        'domaine': 'Navigation',
        'libelle': 'Gestion utilisateurs',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'partial',
            'enseignant': 'denied',
        },
        'notes': {
            'admin_ecole': 'Comptes école via fiche école (API), pas la page nationale',
        },
    },
    {
        'id': 'menu_monitoring',
        'domaine': 'Navigation',
        'libelle': 'Utilisateurs connectés / monitoring',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
    },
    {
        'id': 'menu_parametres',
        'domaine': 'Navigation',
        'libelle': 'Paramètres (territoire, structure, années)',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
    },
    {
        'id': 'ecole_creer',
        'domaine': 'Écoles',
        'libelle': 'Créer / modifier / supprimer une école',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'partial',
            'enseignant': 'denied',
        },
        'notes': {
            'admin_ecole': 'Modification de sa propre école uniquement',
        },
    },
    {
        'id': 'ecole_photos_docs',
        'domaine': 'Écoles',
        'libelle': 'Photos et documents d’école',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'na',
        },
    },
    {
        'id': 'ecole_personnel',
        'domaine': 'Écoles',
        'libelle': 'Personnel (CRUD / import)',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'na',
        },
    },
    {
        'id': 'eleve_consulter',
        'domaine': 'Élèves',
        'libelle': 'Consulter les élèves',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'write',
            'enseignant': 'read',
        },
        'notes': {
            'enseignant': 'Uniquement sa classe titulaire',
        },
    },
    {
        'id': 'eleve_ecrire',
        'domaine': 'Élèves',
        'libelle': 'Créer / modifier / supprimer / import Excel',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'write',
            'enseignant': 'denied',
        },
    },
    {
        'id': 'eleve_photo',
        'domaine': 'Élèves',
        'libelle': 'Photo de l’élève',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'write',
            'enseignant': 'write',
        },
        'notes': {
            'enseignant': 'Élèves de sa classe uniquement',
        },
    },
    {
        'id': 'eleve_qr',
        'domaine': 'Élèves',
        'libelle': 'QR unique (immuable)',
        'niveaux': {
            'admin': 'read',
            'agent_national': 'read',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
        'notes': {
            'admin': 'Généré une fois à la création — pas de régénération (documents imprimés)',
            'agent_national': 'Généré une fois à la création — pas de régénération',
        },
    },
    {
        'id': 'eleve_cartes',
        'domaine': 'Élèves',
        'libelle': 'Cartes et biométries (fiche)',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'write',
            'agent_province_admin': 'read',
            'agent_provincial': 'read',
            'agent_antenne': 'read',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
        'notes': {
            'admin_ecole': 'Blocs masqués sur la fiche',
            'enseignant': 'Blocs masqués ; API cartes vide',
        },
    },
    {
        'id': 'eval_config',
        'domaine': 'Évaluations',
        'libelle': 'Configurer matières / déverrouiller période',
        'niveaux': {
            'admin': 'partial',
            'agent_national': 'partial',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'partial',
            'enseignant': 'denied',
        },
        'notes': {
            'admin': 'Catalogue matières via Structure scolaire',
            'agent_national': 'Catalogue matières via Structure scolaire',
            'admin_ecole': 'Programme / clôture / déverrouillage / classement — sans saisie ni création de matières',
        },
    },
    {
        'id': 'eval_notes',
        'domaine': 'Évaluations',
        'libelle': 'Saisie des notes',
        'niveaux': {
            'admin': 'denied',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'write',
        },
        'notes': {
            'admin_ecole': 'Consultation / programme — sans saisie',
            'enseignant': 'Sa classe — clôture = tous les cours de la période',
        },
    },
    {
        'id': 'eval_bulletins',
        'domaine': 'Évaluations',
        'libelle': 'Bulletins / classements',
        'niveaux': {
            'admin': 'denied',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'write',
            'enseignant': 'write',
        },
    },
    {
        'id': 'users_global',
        'domaine': 'Comptes',
        'libelle': 'CRUD utilisateurs agents / admin',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
    },
    {
        'id': 'users_ecole',
        'domaine': 'Comptes',
        'libelle': 'Comptes admin école / enseignant',
        'niveaux': {
            'admin': 'write',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'write',
            'enseignant': 'denied',
        },
        'notes': {
            'admin_ecole': 'Uniquement pour son école',
        },
    },
    {
        'id': 'permissions_page',
        'domaine': 'Comptes',
        'libelle': 'Page Gestion de permissions',
        'niveaux': {
            'admin': 'read',
            'agent_national': 'denied',
            'agent_province_admin': 'denied',
            'agent_provincial': 'denied',
            'agent_antenne': 'denied',
            'admin_ecole': 'denied',
            'enseignant': 'denied',
        },
        'notes': {
            'admin': 'Consultation de la matrice implémentée',
        },
    },
]


def _grouper_details_par_role():
    """Construit, pour chaque rôle, la liste détaillée groupée par domaine."""
    details = {r['code']: {} for r in ROLES}
    for capa in CAPACITES:
        domaine = capa['domaine']
        notes = capa.get('notes') or {}
        for role in ROLES:
            code = role['code']
            niveau = capa['niveaux'].get(code, 'na')
            details[code].setdefault(domaine, []).append({
                'libelle': capa['libelle'],
                'niveau': niveau,
                'niveau_meta': NIVEAUX[niveau],
                'note': notes.get(code, ''),
            })
    resultat = []
    for role in ROLES:
        domaines = []
        for domaine, items in details[role['code']].items():
            domaines.append({'domaine': domaine, 'items': items})
        resultat.append({**role, 'domaines': domaines})
    return resultat


def get_contexte_permissions():
    """Contexte prêt pour le template gestion_permissions."""
    lignes = []
    domaine_courant = None
    for capa in CAPACITES:
        show_domaine = capa['domaine'] != domaine_courant
        domaine_courant = capa['domaine']
        cellules = []
        notes = capa.get('notes') or {}
        for role in ROLES:
            code = role['code']
            niveau = capa['niveaux'].get(code, 'na')
            cellules.append({
                'role': code,
                'niveau': niveau,
                'niveau_meta': NIVEAUX[niveau],
                'note': notes.get(code, ''),
            })
        lignes.append({
            'id': capa['id'],
            'domaine': capa['domaine'],
            'show_domaine': show_domaine,
            'libelle': capa['libelle'],
            'cellules': cellules,
        })
    return {
        'niveaux_legende': list(NIVEAUX.values()),
        'roles_permissions': ROLES,
        'lignes_matrice': lignes,
        'roles_details': _grouper_details_par_role(),
    }
