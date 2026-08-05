"""Services de génération de QR code et PDF pour les cartes scolaires."""
import io
import uuid
from datetime import timedelta

import qrcode
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import Carte


def generer_qr_code(carte: Carte) -> None:
    """Génère et attache un QR code à la carte."""
    contenu = (
        f'EDUC_RDC|{carte.numero_carte}|{carte.eleve.matricule}|'
        f'{carte.eleve.nom_complet}|{carte.date_expiration}'
    )
    img = qrcode.make(contenu)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    nom_fichier = f'qr_{carte.numero_carte}.png'
    carte.qr_code.save(nom_fichier, ContentFile(buffer.read()), save=False)


def creer_carte_pour_eleve(eleve) -> Carte:
    """Crée une carte scolaire pour un élève."""
    carte = Carte(
        eleve=eleve,
        numero_carte=f'RDC-{uuid.uuid4().hex[:12].upper()}',
        date_expiration=timezone.now().date() + timedelta(days=365 * 3),
        statut=Carte.Statut.ACTIVE,
    )
    generer_qr_code(carte)
    carte.save()
    return carte


def generer_pdf_carte(carte: Carte) -> bytes:
    """Génère un PDF simple de la carte scolaire."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largeur, hauteur = A4

    # En-tête
    c.setFillColorRGB(0, 0.5, 1)  # Bleu RDC
    c.rect(0, hauteur - 40 * mm, largeur, 40 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(largeur / 2, hauteur - 20 * mm, 'RÉPUBLIQUE DÉMOCRATIQUE DU CONGO')
    c.setFont('Helvetica', 12)
    c.drawCentredString(largeur / 2, hauteur - 30 * mm, 'Carte Scolaire Nationale — Educ_RDC')

    # Corps
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 14)
    y = hauteur - 60 * mm
    c.drawString(30 * mm, y, 'Informations de l\'élève')
    c.setFont('Helvetica', 11)
    lignes = [
        f'Numéro de carte : {carte.numero_carte}',
        f'Matricule : {carte.eleve.matricule}',
        f'Nom complet : {carte.eleve.nom_complet}',
        f'Sexe : {carte.eleve.get_sexe_display()}',
        f'Date de naissance : {carte.eleve.date_naissance}',
        f'École : {carte.eleve.ecole.nom}',
        f'Classe : {carte.eleve.classe.nom if carte.eleve.classe_id else "—"}',
        f'Émission : {carte.date_emission:%d/%m/%Y}',
        f'Expiration : {carte.date_expiration:%d/%m/%Y}',
        f'Statut : {carte.get_statut_display()}',
    ]
    y -= 10 * mm
    for ligne in lignes:
        c.drawString(30 * mm, y, ligne)
        y -= 8 * mm

    # Bandeau jaune/rouge
    c.setFillColorRGB(0.988, 0.82, 0.086)  # Jaune
    c.rect(0, 20 * mm, largeur, 8 * mm, fill=1, stroke=0)
    c.setFillColorRGB(0.808, 0.067, 0.149)  # Rouge
    c.rect(0, 12 * mm, largeur, 8 * mm, fill=1, stroke=0)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
