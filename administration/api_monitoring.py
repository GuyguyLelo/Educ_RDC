"""API monitoring — sessions + autorisations accès hors RDC (admin)."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utilisateurs.permissions import EstAdmin

from .acces_exterieur import (
    autoriser_demande,
    refuser_demande,
    revoquer_demande,
    serialiser_autorisation,
)
from .geoip import geo_depuis_navigateur
from .models import AutorisationAccesExterieur
from .monitoring import lister_sessions_actives, resume_sessions, supprimer_session
from .views import journaliser


class PresenceGeoView(APIView):
    """Enregistre la géolocalisation navigateur de la session courante."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        geo = geo_depuis_navigateur(
            request.data.get('latitude'),
            request.data.get('longitude'),
            request.data.get('accuracy'),
            label=request.data.get('label') or '',
        )
        if geo.get('lat') is None or geo.get('lon') is None:
            return Response(
                {'detail': 'Coordonnées latitude / longitude requises.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.session['_presence_geo'] = geo
        request.session.modified = True
        return Response({'detail': 'Géolocalisation enregistrée.', 'geo': geo})


class MonitoringSessionsView(APIView):
    """Liste des utilisateurs connectés (sessions Django actives)."""

    permission_classes = [IsAuthenticated, EstAdmin]

    def get(self, request):
        sessions = lister_sessions_actives()
        current_key = request.session.session_key
        for row in sessions:
            row['est_session_courante'] = bool(
                current_key and row['session_key'] == current_key
            )
        return Response({
            'resume': resume_sessions(sessions),
            'results': sessions,
            'count': len(sessions),
        })


class MonitoringSessionDetailView(APIView):
    """Déconnecter une session (forcer la fermeture)."""

    permission_classes = [IsAuthenticated, EstAdmin]

    def delete(self, request, session_key):
        if request.session.session_key and session_key == request.session.session_key:
            return Response(
                {'detail': 'Vous ne pouvez pas fermer votre propre session ici.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cible = None
        for row in lister_sessions_actives():
            if row['session_key'] == session_key:
                cible = row
                break
        if not supprimer_session(session_key):
            return Response(
                {'detail': 'Session introuvable ou déjà expirée.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        detail = (
            f"{cible['username']} ({cible['role_display']})"
            if cible else session_key
        )
        journaliser(
            request.user,
            'Déconnexion forcée',
            f'Session fermée : {detail}',
            request=request,
        )
        return Response({'detail': 'Session déconnectée.', 'session_key': session_key})


class AccesExterieurListView(APIView):
    """Liste des demandes / autorisations d'accès hors RDC."""

    permission_classes = [IsAuthenticated, EstAdmin]

    def get(self, request):
        statut = (request.query_params.get('statut') or '').strip()
        qs = AutorisationAccesExterieur.objects.select_related(
            'utilisateur', 'decide_par',
        ).all()
        if statut:
            qs = qs.filter(statut=statut)
        else:
            # Par défaut : en attente + autorisations actives
            qs = qs.filter(statut__in=[
                AutorisationAccesExterieur.Statut.EN_ATTENTE,
                AutorisationAccesExterieur.Statut.AUTORISE,
            ])
        rows = [serialiser_autorisation(o) for o in qs[:200]]
        en_attente = AutorisationAccesExterieur.objects.filter(
            statut=AutorisationAccesExterieur.Statut.EN_ATTENTE,
        ).count()
        return Response({
            'count': len(rows),
            'en_attente': en_attente,
            'results': rows,
        })


class AccesExterieurDecisionView(APIView):
    """Autoriser / refuser / révoquer une demande."""

    permission_classes = [IsAuthenticated, EstAdmin]

    def post(self, request, pk):
        try:
            demande = AutorisationAccesExterieur.objects.select_related('utilisateur').get(pk=pk)
        except AutorisationAccesExterieur.DoesNotExist:
            return Response({'detail': 'Demande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        action = (request.data.get('action') or '').strip().lower()
        motif = (request.data.get('motif') or '').strip()
        jours = request.data.get('jours', 7)
        toutes_ip = bool(request.data.get('toutes_ip'))

        if action == 'autoriser':
            if demande.statut not in (
                AutorisationAccesExterieur.Statut.EN_ATTENTE,
                AutorisationAccesExterieur.Statut.REFUSE,
                AutorisationAccesExterieur.Statut.REVOQUE,
            ):
                return Response(
                    {'detail': 'Cette demande ne peut plus être autorisée.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            autoriser_demande(
                demande, request.user,
                jours=int(jours or 7),
                toutes_ip=toutes_ip,
                motif=motif,
            )
            journaliser(
                request.user,
                'Accès hors RDC autorisé',
                f'{demande.utilisateur.username} — IP {demande.adresse_ip} — {jours}j',
                request=request,
            )
            return Response({
                'detail': 'Accès hors RDC autorisé.',
                'result': serialiser_autorisation(demande),
            })

        if action == 'refuser':
            refuser_demande(demande, request.user, motif=motif)
            journaliser(
                request.user,
                'Accès hors RDC refusé',
                f'{demande.utilisateur.username} — IP {demande.adresse_ip}',
                request=request,
            )
            return Response({
                'detail': 'Demande refusée.',
                'result': serialiser_autorisation(demande),
            })

        if action == 'revoquer':
            revoquer_demande(demande, request.user, motif=motif)
            journaliser(
                request.user,
                'Accès hors RDC révoqué',
                f'{demande.utilisateur.username} — IP {demande.adresse_ip}',
                request=request,
            )
            return Response({
                'detail': 'Autorisation révoquée.',
                'result': serialiser_autorisation(demande),
            })

        return Response(
            {'detail': 'Action invalide (autoriser | refuser | revoquer).'},
            status=status.HTTP_400_BAD_REQUEST,
        )
