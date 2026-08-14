"""Vues frontend (pages HTML) et journal d'activité."""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from eleves.models import Eleve
from .models import JournalActivite


def journaliser(utilisateur, action, details='', request=None):
    """Enregistre une activité dans le journal."""
    ip = None
    if request:
        ip = request.META.get('REMOTE_ADDR')
    JournalActivite.objects.create(
        utilisateur=utilisateur,
        action=action,
        details=details,
        adresse_ip=ip,
    )


@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def vue_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            from .acces_exterieur import (
                a_autorisation_valide,
                analyser_localisation_requete,
                creer_ou_rafraichir_demande,
            )
            ip, geo, hors = analyser_localisation_requete(request)
            if hors and not a_autorisation_valide(user, ip):
                demande = creer_ou_rafraichir_demande(user, ip, geo)
                journaliser(
                    user,
                    'Connexion hors RDC refusée',
                    f'IP {ip} — {geo.get("label") or "?"} — demande #{demande.pk}',
                    request=request,
                )
                messages.error(
                    request,
                    'Votre connexion provient de l’extérieur de la RDC. '
                    'L’accès doit être autorisé par un administrateur. '
                    'Votre demande a été enregistrée.',
                )
                return render(request, 'login.html')

            login(request, user)
            request.session['_presence_ip'] = ip
            request.session['_presence_geo'] = geo
            request.session.modified = True
            journaliser(
                user,
                'Connexion',
                f'IP {ip}' + (f' — hors RDC autorisé ({geo.get("label")})' if hors else ''),
                request=request,
            )
            messages.success(request, f'Bienvenue, {user.get_full_name() or user.username} !')
            return redirect('dashboard')
        messages.error(request, 'Identifiants incorrects.')
    return render(request, 'login.html')


@login_required
def vue_logout(request):
    journaliser(request.user, 'Déconnexion', request=request)
    logout(request)
    messages.info(request, 'Vous êtes déconnecté.')
    return redirect('login')


@login_required
def vue_dashboard(request):
    return render(request, 'dashboard.html', {'page': 'dashboard'})


@login_required
def vue_ecoles(request):
    user = request.user
    if getattr(user, 'est_enseignant', False):
        messages.warning(request, "Accès réservé aux administratifs de l'école.")
        return redirect('eleves')
    if user.role == 'admin_ecole' and user.ecole_id:
        return redirect('ecole_detail', ecole_id=user.ecole_id)
    return render(request, 'ecoles.html', {'page': 'ecoles'})


@login_required
def vue_ecole_detail(request, ecole_id):
    """Page détail d'une école (identification, effectifs, élèves)."""
    from ecoles.models import Ecole
    user = request.user
    if getattr(user, 'est_enseignant', False):
        messages.warning(request, "Accès réservé aux administratifs de l'école.")
        return redirect('eleves')
    if user.role == 'admin_ecole' and user.ecole_id and user.ecole_id != ecole_id:
        messages.warning(request, "Vous n'avez accès qu'à votre école.")
        return redirect('ecole_detail', ecole_id=user.ecole_id)
    ecole = get_object_or_404(
        Ecole.objects.select_related(
            'province_educationnelle',
            'province_educationnelle__province_administrative',
            'antenne',
        ),
        pk=ecole_id,
    )
    page = 'ecole_detail' if user.role == 'admin_ecole' else 'ecoles'
    return render(request, 'ecole_detail.html', {
        'page': page,
        'ecole_id': ecole.id,
        'ecole': ecole,
    })


@login_required
def vue_eleves(request):
    return render(request, 'eleves.html', {'page': 'eleves'})


@login_required
def vue_evaluations(request):
    """Saisie des notes et impression des bulletins (modèle RDC)."""
    user = request.user
    if (
        getattr(user, 'est_agent_territorial', False)
        or getattr(user, 'est_national', False)
    ):
        messages.warning(request, "Votre rôle n'a pas accès au module Évaluation.")
        return redirect('dashboard')
    classe = None
    if getattr(user, 'est_enseignant', False) and user.classe_id:
        from ecoles.models import Classe
        classe = (
            Classe.objects.select_related('section', 'option')
            .filter(pk=user.classe_id)
            .first()
        )
    # Module école : enseignant, administratif école
    return render(request, 'evaluations.html', {
        'page': 'evaluations',
        'est_enseignant': getattr(user, 'est_enseignant', False),
        'classe_id': getattr(user, 'classe_id', None) or '',
        'classe_nom': (classe.nom if classe else '') or getattr(user, 'classe_nom', '') or '',
        'section_id': (classe.section_id if classe else '') or '',
        'section_nom': (classe.section.nom if classe and classe.section_id else '') or '',
        'option_id': (classe.option_id if classe else '') or '',
        'option_nom': (classe.option.nom if classe and classe.option_id else '') or '',
        'ecole_id': getattr(user, 'ecole_id', None) or '',
        'peut_configurer': user.role == 'admin_ecole',
    })


@login_required
def vue_eleve_detail(request, eleve_id):
    """Page détail d'un élève (photo, identité, scolarité, cartes)."""
    user = request.user
    qs = Eleve.objects.select_related(
        'ecole',
        'ecole__province_educationnelle',
        'ecole__province_educationnelle__province_administrative',
        'ecole__antenne',
        'classe',
        'biometrie',
    )
    if getattr(user, 'est_enseignant', False):
        if not user.classe_id:
            messages.warning(request, "Aucune classe titulaire n'est associée à votre compte.")
            return redirect('eleves')
        qs = qs.filter(classe_id=user.classe_id)
        if user.ecole_id:
            qs = qs.filter(ecole_id=user.ecole_id)
    elif getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
        qs = qs.filter(ecole_id=user.ecole_id)
    elif user.role == 'agent_province_admin' and user.province_administrative_id:
        qs = qs.filter(
            ecole__province_educationnelle__province_administrative_id=(
                user.province_administrative_id
            ),
        )
    elif user.role == 'agent_provincial' and user.province_educationnelle_id:
        qs = qs.filter(ecole__province_educationnelle_id=user.province_educationnelle_id)
    elif user.role == 'agent_antenne' and user.antenne_id:
        qs = qs.filter(ecole__antenne_id=user.antenne_id)

    eleve = get_object_or_404(qs, pk=eleve_id)
    return render(request, 'eleve_detail.html', {
        'page': 'eleves',
        'eleve_id': eleve.id,
        'eleve': eleve,
    })


@login_required
def vue_cartes(request):
    if getattr(request.user, 'est_enseignant', False):
        messages.warning(request, "Accès aux cartes scolaires réservé aux administratifs.")
        return redirect('eleves')
    return render(request, 'cartes.html', {'page': 'cartes'})


@login_required
def vue_rapports(request):
    return render(request, 'rapports.html', {'page': 'rapports'})


@login_required
@ensure_csrf_cookie
def vue_parametres(request):
    """Gestion des données référentielles (provinces admin/éduc, antennes)."""
    if not getattr(request.user, 'est_national', False):
        messages.warning(request, 'Accès réservé aux agents nationaux.')
        return redirect('dashboard')
    return render(request, 'parametres.html', {'page': 'parametres'})


@login_required
@ensure_csrf_cookie
def vue_parametres_scolaire(request):
    """CRUD sections, options, classes et matières — administration nationale uniquement."""
    user = request.user
    if not getattr(user, 'est_national', False):
        messages.warning(request, 'Accès réservé à l\'administration nationale.')
        return redirect('dashboard')
    return render(request, 'parametres_scolaire.html', {
        'page': 'parametres_scolaire',
        'ecole_id': '',
        'ecole_figee': False,
    })


@login_required
@ensure_csrf_cookie
def vue_parametres_annees(request):
    """Référentiel national des années scolaires (une seule année active)."""
    user = request.user
    peut = getattr(user, 'est_admin', False) or getattr(user, 'est_national', False)
    if not peut:
        messages.warning(request, 'Accès réservé à l\'administration nationale.')
        return redirect('dashboard')
    return render(request, 'parametres_annees.html', {'page': 'parametres_annees'})


@login_required
@ensure_csrf_cookie
def vue_parametres_gestion_documentaire(request):
    """Gestion documentaire — référentiel national (arrêtés, agréments…)."""
    user = request.user
    peut = getattr(user, 'est_admin', False) or getattr(user, 'est_national', False)
    if not peut:
        messages.warning(request, 'Accès réservé à l\'administration nationale.')
        return redirect('dashboard')
    return render(
        request,
        'parametres_arretes.html',
        {'page': 'parametres_gestion_documentaire'},
    )


# Alias pour compatibilité
vue_parametres_arretes = vue_parametres_gestion_documentaire


@login_required
@ensure_csrf_cookie
def vue_utilisateurs(request):
    """Gestion des utilisateurs et des rôles."""
    if not getattr(request.user, 'est_admin', False):
        messages.warning(request, 'Accès réservé aux administrateurs.')
        return redirect('dashboard')
    return render(request, 'utilisateurs.html', {'page': 'utilisateurs'})


@login_required
@ensure_csrf_cookie
def vue_gestion_permissions(request):
    """Gestion des permissions par rôle — admin national uniquement."""
    if not getattr(request.user, 'est_admin', False):
        messages.warning(request, 'Accès réservé à l\'administrateur national.')
        return redirect('dashboard')
    from utilisateurs.matrice_permissions import get_contexte_permissions
    contexte = {'page': 'utilisateurs'}
    contexte.update(get_contexte_permissions())
    return render(request, 'gestion_permissions.html', contexte)


@login_required
@ensure_csrf_cookie
def vue_utilisateur_detail(request, utilisateur_id):
    """Page détail d'un utilisateur (identité, rôle, rattachement)."""
    if not getattr(request.user, 'est_admin', False):
        messages.warning(request, 'Accès réservé aux administrateurs.')
        return redirect('dashboard')
    from utilisateurs.models import Utilisateur
    utilisateur = get_object_or_404(
        Utilisateur.objects.select_related(
            'province_administrative',
            'province_educationnelle',
            'antenne',
            'ecole',
            'classe',
            'classe__section',
            'classe__option',
        ),
        pk=utilisateur_id,
    )
    return render(request, 'utilisateur_detail.html', {
        'page': 'utilisateurs',
        'utilisateur_id': utilisateur.id,
        'utilisateur': utilisateur,
    })


@login_required
@ensure_csrf_cookie
def vue_monitoring_utilisateurs(request):
    """Monitoring des utilisateurs connectés — admin uniquement."""
    if not getattr(request.user, 'est_admin', False):
        messages.warning(request, 'Accès réservé aux administrateurs.')
        return redirect('dashboard')
    return render(request, 'monitoring_utilisateurs.html', {'page': 'monitoring_utilisateurs'})


@login_required
@ensure_csrf_cookie
def vue_monitoring_utilisateurs_carte(request):
    """Carte interne des utilisateurs connectés — admin uniquement."""
    if not getattr(request.user, 'est_admin', False):
        messages.warning(request, 'Accès réservé aux administrateurs.')
        return redirect('dashboard')
    return render(request, 'monitoring_utilisateurs_carte.html', {'page': 'monitoring_utilisateurs'})


@login_required
@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def vue_structure_formulaire(request):
    """Formulaire unique StructureOrganisationnelle (héritage PA / PE / Antenne)."""
    from ecoles.forms import StructureOrganisationnelleForm

    if request.method == 'POST':
        form = StructureOrganisationnelleForm(request.POST)
        if form.is_valid():
            obj = form.save()
            type_label = dict(StructureOrganisationnelleForm.TYPE_CHOICES).get(
                form.cleaned_data['type_structure'], 'Structure'
            )
            messages.success(
                request,
                f'{type_label} « {obj.nom} » ({obj.code}) créée avec succès.',
            )
            journaliser(
                request.user,
                'Création structure',
                f'{type_label}: {obj.nom} ({obj.code})',
                request=request,
            )
            return redirect('parametres')
    else:
        initial_type = request.GET.get('type', StructureOrganisationnelleForm.TYPE_PA)
        form = StructureOrganisationnelleForm(initial={'type_structure': initial_type})

    return render(request, 'structure_formulaire.html', {
        'page': 'parametres',
        'form': form,
    })
