"""Génération PDF — liste des élèves (classe enseignant)."""
from __future__ import annotations

import io
from datetime import datetime

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


# Bleu ciel
BLEU_CIEL = (0.53, 0.81, 0.92)  # ~#87CEEB


def _texte(valeur, defaut='—'):
    if valeur is None:
        return defaut
    text = str(valeur).strip()
    return text or defaut


def _date_fr(valeur):
    if not valeur:
        return '—'
    if hasattr(valeur, 'strftime'):
        return valeur.strftime('%d/%m/%Y')
    return str(valeur)


def _tronquer(texte, max_len):
    t = _texte(texte)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + '…'


def generer_pdf_liste_eleves(eleves, *, contexte=None) -> bytes:
    """
    Liste PDF portrait des élèves.
    contexte: ecole, classe, section, option, enseignant, recherche.
    """
    contexte = contexte or {}
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largeur, hauteur = A4

    marge_g = 14 * mm
    marge_d = 14 * mm
    y_min = 30 * mm  # enseignant + pied
    row_h = 8 * mm
    table_w = largeur - marge_g - marge_d

    cols = [
        ('N°', 12 * mm),
        ('Nom complet', 95 * mm),
        ('N° Identification', 48 * mm),
        ('Sexe', 22 * mm),
    ]

    enseignant = _texte(contexte.get('enseignant'))
    effectif = len(eleves)
    recherche = (contexte.get('recherche') or '').strip()

    def _ligne_separatrice(y, epaisseur=1.8):
        c.setStrokeColorRGB(*BLEU_CIEL)
        c.setLineWidth(epaisseur)
        c.line(marge_g, y, largeur - marge_d, y)

    def _pied_page(page_num):
        if enseignant != '—':
            c.setFillColorRGB(0.02, 0.16, 0.29)
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(largeur / 2, 22 * mm, f'Enseignant : {enseignant}')

        c.setFillColorRGB(0.35, 0.4, 0.45)
        c.setFont('Helvetica', 8)
        meta = f'Page {page_num}'
        if recherche:
            meta = f'Filtre : « {_tronquer(recherche, 28)} »  ·  {meta}'
        c.drawRightString(largeur - marge_d, 22 * mm, meta)

        c.setFillColorRGB(0.81, 0.07, 0.15)
        c.rect(0, 8 * mm, largeur, 6 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0.35, 0.4, 0.45)
        c.setFont('Helvetica', 7)
        c.drawRightString(
            largeur - marge_d,
            15.5 * mm,
            f'Imprimé le {_date_fr(timezone.localdate())} à {datetime.now().strftime("%H:%M")}',
        )

    def _entete_page(page_num):
        c.setFillColorRGB(0.0, 0.5, 1.0)
        c.rect(0, hauteur - 28 * mm, largeur, 28 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 0.82, 0.09)
        c.rect(0, hauteur - 30 * mm, largeur, 2 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0.81, 0.07, 0.15)
        c.rect(0, hauteur - 32 * mm, largeur, 2 * mm, fill=1, stroke=0)

        c.setFillColorRGB(1, 1, 1)
        c.setFont('Helvetica-Bold', 11)
        c.drawCentredString(largeur / 2, hauteur - 11 * mm, 'RÉPUBLIQUE DÉMOCRATIQUE DU CONGO')
        c.setFont('Helvetica-Bold', 12)
        c.drawCentredString(largeur / 2, hauteur - 18 * mm, 'Ministère de l’Éducation Nationale')
        c.setFont('Helvetica', 9)
        c.drawCentredString(largeur / 2, hauteur - 24.5 * mm, 'Liste des élèves — Educ_RDC')

        y = hauteur - 40 * mm
        c.setFillColorRGB(0.02, 0.16, 0.29)
        c.setFont('Helvetica-Bold', 9)
        ecole = _texte(contexte.get('ecole'))
        classe = _texte(contexte.get('classe'))
        section = _texte(contexte.get('section'))
        option = _texte(contexte.get('option'))
        c.drawString(marge_g, y, f'École : {_tronquer(ecole, 55)}')
        y -= 5 * mm
        c.drawString(marge_g, y, f'Classe : {classe}')
        y -= 5 * mm
        c.drawString(marge_g, y, f'Section : {section}')
        c.drawRightString(largeur - marge_d, y, f'Option : {option}')
        y -= 12 * mm  # ligne vide avant le tableau

        # En-tête tableau
        c.setFillColorRGB(0.88, 0.95, 0.98)
        c.rect(marge_g, y - 1.5 * mm, table_w, row_h, fill=1, stroke=0)
        c.setFillColorRGB(0.02, 0.16, 0.29)
        c.setFont('Helvetica-Bold', 8)
        x = marge_g + 1 * mm
        for label, w in cols:
            c.drawString(x, y, label)
            x += w
        y -= 2 * mm
        _ligne_separatrice(y, epaisseur=2.4)
        return y - (row_h - 2 * mm)

    page_num = 1
    y = _entete_page(page_num)

    if not eleves:
        c.setFillColorRGB(0.4, 0.45, 0.5)
        c.setFont('Helvetica-Oblique', 10)
        c.drawString(marge_g, y - 4 * mm, 'Aucun élève à afficher.')
    else:
        for idx, eleve in enumerate(eleves, start=1):
            if y < y_min + row_h:
                _pied_page(page_num)
                c.showPage()
                page_num += 1
                y = _entete_page(page_num)

            c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica', 8)
            valeurs = [
                str(idx),
                _tronquer(eleve.nom_complet, 48),
                _tronquer(eleve.numero_identification, 24),
                _tronquer(eleve.get_sexe_display(), 10),
            ]
            x = marge_g + 1 * mm
            for (_label, w), val in zip(cols, valeurs):
                c.drawString(x, y, val)
                x += w

            y -= 2.5 * mm
            _ligne_separatrice(y, epaisseur=1.8)
            y -= (row_h - 2.5 * mm)

    # Effectif juste après le tableau
    if y < y_min + 8 * mm:
        _pied_page(page_num)
        c.showPage()
        page_num += 1
        y = _entete_page(page_num)
    y -= 3 * mm
    c.setFillColorRGB(0.02, 0.16, 0.29)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(marge_g, y, f'Effectif : {effectif}')

    _pied_page(page_num)
    c.save()
    buffer.seek(0)
    return buffer.read()
