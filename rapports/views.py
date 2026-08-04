"""Vues API et rapports — statistiques dashboard + export PDF."""
import io

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ecoles.models import Ecole, ProvinceEducationnelle
from eleves.models import Eleve
from cartes.models import Carte
from enrolement.models import Enrolement
from biometrie.models import Biometrie
from .models import Rapport


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistiques_dashboard(request):
    """Statistiques dynamiques pour le dashboard."""
    user = request.user
    ecoles_qs = Ecole.objects.filter(active=True)
    eleves_qs = Eleve.objects.filter(actif=True)
    cartes_qs = Carte.objects.filter(statut=Carte.Statut.ACTIVE)
    enrolements_qs = Enrolement.objects.all()

    if user.role == 'agent_provincial' and user.province_educationnelle_id:
        pe = user.province_educationnelle_id
        ecoles_qs = ecoles_qs.filter(province_educationnelle_id=pe)
        eleves_qs = eleves_qs.filter(ecole__province_educationnelle_id=pe)
        cartes_qs = cartes_qs.filter(eleve__ecole__province_educationnelle_id=pe)
        enrolements_qs = enrolements_qs.filter(eleve__ecole__province_educationnelle_id=pe)
    elif user.role == 'agent_antenne' and user.antenne_id:
        ecoles_qs = ecoles_qs.filter(antenne_id=user.antenne_id)
        eleves_qs = eleves_qs.filter(ecole__antenne_id=user.antenne_id)
        cartes_qs = cartes_qs.filter(eleve__ecole__antenne_id=user.antenne_id)
        enrolements_qs = enrolements_qs.filter(eleve__ecole__antenne_id=user.antenne_id)

    par_province = list(
        ProvinceEducationnelle.objects.annotate(
            nb_ecoles=Count('ecoles', filter=Q(ecoles__active=True)),
            nb_eleves=Count('ecoles__eleves', filter=Q(ecoles__eleves__actif=True)),
        ).values('nom', 'nb_ecoles', 'nb_eleves')[:10]
    )

    return Response({
        'nb_eleves': eleves_qs.count(),
        'nb_ecoles': ecoles_qs.count(),
        'nb_cartes': cartes_qs.count(),
        'nb_enrolements': enrolements_qs.count(),
        'enrolements_en_attente': enrolements_qs.filter(statut='en_attente').count(),
        'enrolements_valides': enrolements_qs.filter(statut='valide').count(),
        'biometries_validees': Biometrie.objects.filter(validee=True).count(),
        'par_province': par_province,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_rapport_pdf(request):
    """Export PDF d'un rapport global."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largeur, hauteur = A4

    c.setFillColorRGB(0, 0.5, 1)
    c.rect(0, hauteur - 50, largeur, 50, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(largeur / 2, hauteur - 32, 'Educ_RDC — Rapport Administratif')

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica', 12)
    y = hauteur - 90
    stats = [
        f'Écoles actives : {Ecole.objects.filter(active=True).count()}',
        f'Élèves actifs : {Eleve.objects.filter(actif=True).count()}',
        f'Cartes actives : {Carte.objects.filter(statut="active").count()}',
        f'Enrôlements validés : {Enrolement.objects.filter(statut="valide").count()}',
        f'Enrôlements en attente : {Enrolement.objects.filter(statut="en_attente").count()}',
    ]
    for ligne in stats:
        c.drawString(50, y, ligne)
        y -= 24

    c.setFillColorRGB(0.808, 0.067, 0.149)
    c.rect(0, 30, largeur, 20, fill=1, stroke=0)
    c.showPage()
    c.save()
    buffer.seek(0)

    Rapport.objects.create(
        titre='Rapport global Educ_RDC',
        type_rapport=Rapport.TypeRapport.GLOBAL,
        genere_par=request.user,
    )

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_educ_rdc.pdf"'
    return response
