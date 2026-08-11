"""Middleware présence + contrôle accès hors RDC."""
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect


class PresenceMiddleware:
    """Enregistre l'activité des utilisateurs authentifiés dans leur session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from .monitoring import enregistrer_presence
            enregistrer_presence(request)
        except Exception:
            pass
        return self.get_response(request)


class AccesExterieurMiddleware:
    """
    Bloque les sessions hors RDC non autorisées (sauf administrateurs).
    Les IP locales / privées restent autorisées.
    """

    EXEMPT_PREFIXES = (
        '/static/',
        '/media/',
        '/api/auth/',
        '/logout/',
    )

    MSG = (
        'Connexion depuis l’extérieur de la RDC non autorisée. '
        'Une demande a été envoyée à l’administrateur.'
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return self.get_response(request)

        try:
            from .acces_exterieur import (
                a_autorisation_valide,
                analyser_localisation_requete,
                creer_ou_rafraichir_demande,
            )
            ip, geo, hors = analyser_localisation_requete(request)
            request.acces_hors_rdc = hors
            request.acces_geo = geo
            if not hors or a_autorisation_valide(user, ip):
                return self.get_response(request)

            creer_ou_rafraichir_demande(user, ip, geo)
            logout(request)

            if path.startswith('/api/'):
                return JsonResponse({'detail': self.MSG}, status=403)

            messages.error(request, self.MSG)
            # Page login : laisser afficher le message
            if path.rstrip('/') in ('',):
                return self.get_response(request)
            return redirect('login')
        except Exception:
            return self.get_response(request)
