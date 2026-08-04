"""Vues frontend (pages HTML) et journal d'activité."""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
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


@require_http_methods(['GET', 'POST'])
def vue_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            journaliser(user, 'Connexion', request=request)
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
    return render(request, 'ecoles.html', {'page': 'ecoles'})


@login_required
def vue_eleves(request):
    return render(request, 'eleves.html', {'page': 'eleves'})


@login_required
def vue_eleve_detail(request, eleve_id):
    """Page détail d'un élève (photo, identité, scolarité, cartes)."""
    eleve = get_object_or_404(
        Eleve.objects.select_related(
            'ecole', 'ecole__province', 'ecole__antenne', 'biometrie',
        ),
        pk=eleve_id,
    )
    return render(request, 'eleve_detail.html', {
        'page': 'eleves',
        'eleve_id': eleve.id,
        'eleve': eleve,
    })


@login_required
def vue_enrolement(request):
    return render(request, 'enrolement.html', {'page': 'enrolement'})


@login_required
def vue_cartes(request):
    return render(request, 'cartes.html', {'page': 'cartes'})


@login_required
def vue_rapports(request):
    return render(request, 'rapports.html', {'page': 'rapports'})


@login_required
def vue_parametres(request):
    """Gestion des données référentielles (provinces, antennes)."""
    return render(request, 'parametres.html', {'page': 'parametres'})
