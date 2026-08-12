"""Vues API et rapports — statistiques dashboard + export PDF."""
import io

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ecoles.models import Antenne, Ecole, PersonnelEcole, ProvinceEducationnelle
from eleves.models import Eleve
from cartes.models import Carte
from biometrie.models import Biometrie
from .models import Rapport


def _scoped_querysets(user):
    """Retourne les querysets et le contexte territorial selon le rôle."""
    ecoles_qs = Ecole.objects.filter(active=True)
    eleves_qs = Eleve.objects.filter(actif=True)
    cartes_qs = Carte.objects.filter(statut=Carte.Statut.ACTIVE)
    biometrie_qs = Biometrie.objects.filter(validee=True)
    personnel_qs = PersonnelEcole.objects.filter(actif=True)

    scope = 'national'
    scope_label = "Vue d'ensemble nationale"
    ecole_id = None
    ecole_nom = None
    classe = None

    if getattr(user, 'est_enseignant', False):
        scope = 'classe'
        ecole = user.ecole if user.ecole_id else None
        ecole_id = user.ecole_id
        ecole_nom = ecole.nom if ecole else None
        classe = user.classe_nom or ''
        scope_label = (
            f'Classe {classe}' + (f' — {ecole.nom}' if ecole else '')
            if classe else 'Classe titulaire non définie'
        )
        if ecole_id:
            ecoles_qs = ecoles_qs.filter(pk=ecole_id)
            personnel_qs = personnel_qs.filter(ecole_id=ecole_id)
        else:
            ecoles_qs = ecoles_qs.none()
            personnel_qs = personnel_qs.none()
        if user.classe_id:
            eleves_qs = eleves_qs.filter(classe_id=user.classe_id)
            if ecole_id:
                eleves_qs = eleves_qs.filter(ecole_id=ecole_id)
        else:
            eleves_qs = eleves_qs.none()
        cartes_qs = cartes_qs.filter(eleve_id__in=eleves_qs.values('id'))
        biometrie_qs = biometrie_qs.filter(eleve_id__in=eleves_qs.values('id'))
    elif getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
        scope = 'ecole'
        ecole = user.ecole
        ecole_id = ecole.id
        ecole_nom = ecole.nom
        scope_label = f'École — {ecole.nom}'
        ecoles_qs = ecoles_qs.filter(pk=ecole_id)
        eleves_qs = eleves_qs.filter(ecole_id=ecole_id)
        cartes_qs = cartes_qs.filter(eleve__ecole_id=ecole_id)
        biometrie_qs = biometrie_qs.filter(eleve__ecole_id=ecole_id)
        personnel_qs = personnel_qs.filter(ecole_id=ecole_id)
    elif user.role == 'agent_antenne' and user.antenne_id:
        scope = 'antenne'
        antenne = user.antenne
        scope_label = f'Antenne — {antenne.nom}'
        ecoles_qs = ecoles_qs.filter(antenne_id=user.antenne_id)
        eleves_qs = eleves_qs.filter(ecole__antenne_id=user.antenne_id)
        cartes_qs = cartes_qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        biometrie_qs = biometrie_qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        personnel_qs = personnel_qs.filter(ecole__antenne_id=user.antenne_id)
    elif user.role == 'agent_provincial' and user.province_educationnelle_id:
        scope = 'province'
        pe = user.province_educationnelle
        scope_label = f'Province éducationnelle — {pe.nom}'
        pe_id = user.province_educationnelle_id
        ecoles_qs = ecoles_qs.filter(province_educationnelle_id=pe_id)
        eleves_qs = eleves_qs.filter(ecole__province_educationnelle_id=pe_id)
        cartes_qs = cartes_qs.filter(eleve__ecole__province_educationnelle_id=pe_id)
        biometrie_qs = biometrie_qs.filter(eleve__ecole__province_educationnelle_id=pe_id)
        personnel_qs = personnel_qs.filter(ecole__province_educationnelle_id=pe_id)
    elif user.role == 'agent_national':
        scope = 'national'
        scope_label = "Vue d'ensemble nationale — agent national"
    else:
        scope = 'national'
        scope_label = "Vue d'ensemble nationale"

    return {
        'scope': scope,
        'scope_label': scope_label,
        'ecole_id': ecole_id,
        'ecole_nom': ecole_nom,
        'classe': classe,
        'ecoles_qs': ecoles_qs,
        'eleves_qs': eleves_qs,
        'cartes_qs': cartes_qs,
        'biometrie_qs': biometrie_qs,
        'personnel_qs': personnel_qs,
    }


def _chart_for_scope(scope, eleves_qs, ecoles_qs, user):
    """Série pour le graphique principal selon le périmètre."""
    if scope == 'classe':
        rows = list(
            eleves_qs.values('sexe')
            .annotate(valeur=Count('id'))
            .order_by('sexe')
        )
        labels = {'M': 'Garçons', 'F': 'Filles'}
        return {
            'title': f"Effectif — classe {getattr(user, 'classe_nom', '') or ''}".strip(),
            'subtitle': 'Répartition par sexe',
            'series': [
                {'nom': labels.get(r['sexe'], r['sexe'] or '—'), 'valeur': r['valeur']}
                for r in rows
            ],
            'valeur_key': 'eleves',
        }

    if scope == 'ecole':
        rows = list(
            eleves_qs.values('classe__nom')
            .annotate(valeur=Count('id'))
            .order_by('classe__nom')[:15]
        )
        return {
            'title': 'Répartition par classe',
            'subtitle': 'Élèves actifs',
            'series': [{'nom': r['classe__nom'] or '—', 'valeur': r['valeur']} for r in rows],
            'valeur_key': 'eleves',
        }

    if scope == 'antenne':
        rows = list(
            ecoles_qs.annotate(
                valeur=Count('eleves', filter=Q(eleves__actif=True)),
            )
            .order_by('-valeur')
            .values('nom', 'valeur')[:10]
        )
        return {
            'title': 'Écoles de l\'antenne',
            'subtitle': 'Élèves actifs par établissement',
            'series': [{'nom': r['nom'], 'valeur': r['valeur']} for r in rows],
            'valeur_key': 'eleves',
        }

    if scope == 'province':
        pe_id = user.province_educationnelle_id
        rows = list(
            Antenne.objects.filter(province_educationnelle_id=pe_id)
            .annotate(
                valeur=Count('ecoles__eleves', filter=Q(ecoles__eleves__actif=True)),
                nb_ecoles=Count('ecoles', filter=Q(ecoles__active=True)),
            )
            .order_by('-valeur')
            .values('nom', 'valeur', 'nb_ecoles')[:10]
        )
        return {
            'title': 'Répartition par antenne',
            'subtitle': 'Élèves actifs',
            'series': [
                {'nom': r['nom'], 'valeur': r['valeur'], 'nb_ecoles': r['nb_ecoles']}
                for r in rows
            ],
            'valeur_key': 'eleves',
        }

    # national
    rows = list(
        ProvinceEducationnelle.objects.annotate(
            nb_ecoles=Count('ecoles', filter=Q(ecoles__active=True)),
            valeur=Count('ecoles__eleves', filter=Q(ecoles__eleves__actif=True)),
        )
        .order_by('-valeur')
        .values('nom', 'nb_ecoles', 'valeur')[:10]
    )
    return {
        'title': 'Répartition par province',
        'subtitle': 'Élèves actifs',
        'series': [
            {'nom': r['nom'], 'valeur': r['valeur'], 'nb_ecoles': r['nb_ecoles']}
            for r in rows
        ],
        'valeur_key': 'eleves',
    }


def _workflow_for_role(role):
    workflows = {
        'admin': [
            'Pilotage national et administration des comptes',
            'Structurer provinces, antennes et écoles',
            'Suivre l\'identification et la production des cartes',
            'Exploiter les rapports consolidés',
        ],
        'agent_national': [
            'Suivre le déploiement national',
            'Contrôler les effectifs et les écoles',
            'Superviser la production des cartes',
            'Exporter les rapports nationaux',
        ],
        'agent_provincial': [
            'Piloter les antennes de la province',
            'Valider les écoles du territoire',
            'Suivre les élèves et biométries',
            'Suivre la production des cartes',
        ],
        'agent_antenne': [
            'Gérer les écoles de l\'antenne',
            'Enregistrer les élèves',
            'Capturer les biométries',
            'Générer les cartes scolaires',
        ],
        'admin_ecole': [
            'Mettre à jour la fiche de l\'école',
            'Gérer les élèves et le personnel',
            'Créer les comptes enseignants',
            'Suivre cartes et biométries',
        ],
        'enseignant': [
            'Consulter les élèves de sa classe',
            'Vérifier les fiches élèves',
            'Suivre l\'état des biométries de la classe',
            'Mettre à jour la photo des élèves',
        ],
    }
    return workflows.get(role, workflows['agent_antenne'])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistiques_dashboard(request):
    """Statistiques dynamiques pour le dashboard, personnalisées par rôle."""
    user = request.user
    ctx = _scoped_querysets(user)
    eleves_qs = ctx['eleves_qs']
    ecoles_qs = ctx['ecoles_qs']
    cartes_qs = ctx['cartes_qs']
    biometrie_qs = ctx['biometrie_qs']
    personnel_qs = ctx['personnel_qs']
    scope = ctx['scope']

    chart = _chart_for_scope(scope, eleves_qs, ecoles_qs, user)

    # Compatibilité anciens clients (rapports)
    par_province = [
        {
            'nom': s['nom'],
            'nb_eleves': s['valeur'],
            'nb_ecoles': s.get('nb_ecoles', 0),
        }
        for s in chart['series']
    ]

    nb_eleves = eleves_qs.count()
    nb_ecoles = ecoles_qs.count()
    nb_cartes = cartes_qs.count()
    nb_biometries = biometrie_qs.count()
    nb_personnel = personnel_qs.count()
    nb_garcons = eleves_qs.filter(sexe=Eleve.Sexe.MASCULIN).count()
    nb_filles = eleves_qs.filter(sexe=Eleve.Sexe.FEMININ).count()

    cards = [
        {
            'key': 'eleves',
            'label': 'Élèves inscrits',
            'value': nb_eleves,
            'hint': f'{nb_garcons} garçons · {nb_filles} filles',
        },
    ]

    if scope == 'classe':
        cards = [
            {
                'key': 'eleves',
                'label': 'Effectif élèves',
                'value': nb_eleves,
                'hint': ctx['classe'] or 'Classe',
            },
            {
                'key': 'garcons',
                'label': 'Effectif garçons',
                'value': nb_garcons,
                'hint': 'Sexe masculin',
            },
            {
                'key': 'filles',
                'label': 'Effectif filles',
                'value': nb_filles,
                'hint': 'Sexe féminin',
            },
        ]
    elif scope == 'ecole':
        cards.extend([
            {
                'key': 'personnel',
                'label': 'Personnel',
                'value': nb_personnel,
                'hint': 'Agents et enseignants identifiés',
            },
            {
                'key': 'cartes',
                'label': 'Cartes produites',
                'value': nb_cartes,
                'hint': 'Cartes scolaires actives',
                'accent': True,
            },
            {
                'key': 'biometries',
                'label': 'Biométries',
                'value': nb_biometries,
                'hint': 'Captures validées',
            },
        ])
    else:
        cards.extend([
            {
                'key': 'ecoles',
                'label': 'Écoles',
                'value': nb_ecoles,
                'hint': 'Établissements identifiés',
            },
            {
                'key': 'cartes',
                'label': 'Cartes produites',
                'value': nb_cartes,
                'hint': 'Cartes scolaires actives',
                'accent': True,
            },
            {
                'key': 'biometries',
                'label': 'Biométries',
                'value': nb_biometries,
                'hint': 'Captures validées',
            },
        ])

    actions = []
    if scope in ('ecole', 'classe') and ctx['ecole_id']:
        actions = [
            {'label': 'Élèves de ma classe' if scope == 'classe' else 'Fiche de l\'école',
             'url': '/eleves/' if scope == 'classe' else f"/ecoles/{ctx['ecole_id']}/",
             'style': 'primary'},
        ]
        if scope == 'ecole':
            actions.insert(1, {'label': 'Élèves', 'url': '/eleves/', 'style': 'ghost'})
        else:
            actions.append({'label': 'Rapports', 'url': '/rapports/', 'style': 'ghost'})
    elif scope == 'antenne':
        actions = [
            {'label': 'Écoles', 'url': '/ecoles/', 'style': 'primary'},
            {'label': 'Élèves', 'url': '/eleves/', 'style': 'ghost'},
            {'label': 'Rapports', 'url': '/rapports/', 'style': 'ghost'},
        ]
    elif scope == 'province':
        actions = [
            {'label': 'Écoles de la province', 'url': '/ecoles/', 'style': 'primary'},
            {'label': 'Élèves', 'url': '/eleves/', 'style': 'ghost'},
            {'label': 'Rapports', 'url': '/rapports/', 'style': 'ghost'},
        ]
    else:
        actions = [
            {'label': 'Écoles', 'url': '/ecoles/', 'style': 'primary'},
            {'label': 'Élèves', 'url': '/eleves/', 'style': 'ghost'},
            {'label': 'Rapports', 'url': '/rapports/', 'style': 'ghost'},
        ]
        if user.role == 'admin' or user.is_superuser:
            actions.append({'label': 'Utilisateurs', 'url': '/utilisateurs/', 'style': 'ghost'})

    return Response({
        'role': user.role,
        'role_display': user.get_role_display(),
        'scope': scope,
        'scope_label': ctx['scope_label'],
        'ecole_id': ctx['ecole_id'],
        'ecole_nom': ctx['ecole_nom'],
        'classe': ctx.get('classe'),
        'nb_eleves': nb_eleves,
        'nb_ecoles': nb_ecoles,
        'nb_cartes': 0 if getattr(user, 'est_enseignant', False) else nb_cartes,
        'biometries_validees': nb_biometries,
        'nb_personnel': nb_personnel,
        'nb_garcons': nb_garcons,
        'nb_filles': nb_filles,
        'cards': cards,
        'chart': chart,
        'pie_chart': {
            'title': 'Répartition par sexe',
            'subtitle': (
                f"Classe {ctx.get('classe') or ''}".strip()
                if scope == 'classe'
                else 'Effectif du périmètre'
            ),
            'series': [
                {'nom': 'Garçons', 'valeur': nb_garcons, 'couleur': '#007FFF'},
                {'nom': 'Filles', 'valeur': nb_filles, 'couleur': '#CE1126'},
            ],
        },
        'par_province': par_province,
        'actions': actions,
        'workflow': [] if scope == 'classe' else _workflow_for_role(user.role),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_rapport_pdf(request):
    """Export PDF d'un rapport adapté au périmètre de l'utilisateur."""
    user = request.user
    ctx = _scoped_querysets(user)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largeur, hauteur = A4

    c.setFillColorRGB(0, 0.5, 1)
    c.rect(0, hauteur - 50, largeur, 50, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(largeur / 2, hauteur - 32, 'Educ_RDC — Rapport')

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 11)
    y = hauteur - 80
    c.drawString(50, y, f'Périmètre : {ctx["scope_label"]}')
    y -= 18
    c.drawString(50, y, f'Rôle : {user.get_role_display()}')
    y -= 28

    stats = [
        f'Écoles actives : {ctx["ecoles_qs"].count()}',
        f'Élèves actifs : {ctx["eleves_qs"].count()}',
    ]
    if not getattr(user, 'est_enseignant', False):
        stats.append(f'Cartes actives : {ctx["cartes_qs"].count()}')
    stats.append(f'Biométries validées : {ctx["biometrie_qs"].count()}')
    if ctx['scope'] == 'ecole':
        stats.append(f'Personnel actif : {ctx["personnel_qs"].count()}')

    for ligne in stats:
        c.drawString(50, y, ligne)
        y -= 24

    c.setFillColorRGB(0.808, 0.067, 0.149)
    c.rect(0, 30, largeur, 20, fill=1, stroke=0)
    c.showPage()
    c.save()
    buffer.seek(0)

    Rapport.objects.create(
        titre=f'Rapport {ctx["scope_label"]}',
        type_rapport=Rapport.TypeRapport.GLOBAL,
        genere_par=request.user,
    )

    return HttpResponse(
        buffer.read(),
        content_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="rapport_educ_rdc.pdf"'},
    )
