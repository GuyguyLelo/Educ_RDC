"""Génération PDF de la fiche élève."""
from __future__ import annotations

import io
import math
from datetime import datetime

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


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


def _dessiner_en_tete(c, largeur, hauteur):
    c.setFillColorRGB(0.0, 0.5, 1.0)
    c.rect(0, hauteur - 32 * mm, largeur, 32 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 0.82, 0.09)
    c.rect(0, hauteur - 34 * mm, largeur, 2 * mm, fill=1, stroke=0)
    c.setFillColorRGB(0.81, 0.07, 0.15)
    c.rect(0, hauteur - 36 * mm, largeur, 2 * mm, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(largeur / 2, hauteur - 14 * mm, 'RÉPUBLIQUE DÉMOCRATIQUE DU CONGO')
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(largeur / 2, hauteur - 21 * mm, 'Ministère de l’Éducation Nationale')
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(largeur / 2, hauteur - 28 * mm, 'Fiche élève — Educ_RDC')


def _section(c, titre, y, largeur):
    c.setFillColorRGB(0.024, 0.16, 0.29)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(18 * mm, y, titre)
    y -= 2 * mm
    c.setStrokeColorRGB(0.0, 0.5, 1.0)
    c.setLineWidth(1)
    c.line(18 * mm, y, largeur - 18 * mm, y)
    return y - 7 * mm


def _ligne(c, label, valeur, y, x=20 * mm, x_val=70 * mm):
    c.setFillColorRGB(0.35, 0.4, 0.45)
    c.setFont('Helvetica', 9)
    c.drawString(x, y, label)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x_val, y, _texte(valeur)[:72])
    return y - 5.5 * mm


def _photo(c, eleve, x, y, w=32 * mm, h=40 * mm):
    photo = eleve.get_photo()
    c.setStrokeColorRGB(0.75, 0.78, 0.82)
    c.setLineWidth(0.8)
    c.rect(x, y - h, w, h, fill=0, stroke=1)
    if not photo:
        c.setFillColorRGB(0.55, 0.58, 0.62)
        c.setFont('Helvetica', 8)
        c.drawCentredString(x + w / 2, y - h / 2, 'Sans photo')
        return
    try:
        path = photo.path
        c.drawImage(
            path,
            x + 0.8 * mm,
            y - h + 0.8 * mm,
            width=w - 1.6 * mm,
            height=h - 1.6 * mm,
            preserveAspectRatio=True,
            mask='auto',
        )
    except Exception:
        c.setFillColorRGB(0.55, 0.58, 0.62)
        c.setFont('Helvetica', 8)
        c.drawCentredString(x + w / 2, y - h / 2, 'Photo indisponible')


def _etoile(c, cx, cy, r):
    """Étoile à 5 branches (motif RDC)."""
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    path = c.beginPath()
    path.moveTo(pts[0][0], pts[0][1])
    for px, py in pts[1:]:
        path.lineTo(px, py)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def _sceau(c, cx, cy, taille):
    """Sceau circulaire (double cercle + étoile)."""
    c.setLineWidth(1.1)
    c.circle(cx, cy, taille / 2, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.circle(cx, cy, taille / 2 - 3.5 * mm, stroke=1, fill=0)
    _etoile(c, cx, cy + 1.5 * mm, taille * 0.16)
    c.setFont('Helvetica-Bold', max(6, int(taille / mm * 0.22)))
    c.drawCentredString(cx, cy - taille * 0.22, 'R.D. CONGO')


def _dessiner_filigrane(c, largeur, hauteur):
    """Filigrane : motif de sceaux + texte « EDUCATION NATIONALE RDC »."""
    c.saveState()
    gris = (0.78, 0.82, 0.86)
    c.setStrokeColorRGB(*gris)
    c.setFillColorRGB(*gris)
    try:
        c.setFillAlpha(0.14)
        c.setStrokeAlpha(0.14)
    except Exception:
        pass

    # Motif de fond : grille de petits sceaux
    pas_x, pas_y = 48 * mm, 42 * mm
    petit = 18 * mm
    y0 = 28 * mm
    row = 0
    y = y0
    while y < hauteur - 40 * mm:
        x = 12 * mm + (pas_x / 2 if row % 2 else 0)
        while x < largeur - 10 * mm:
            c.setLineWidth(0.5)
            c.circle(x, y, petit / 2, stroke=1, fill=0)
            c.circle(x, y, petit / 2 - 1.8 * mm, stroke=1, fill=0)
            _etoile(c, x, y + 0.6 * mm, petit * 0.14)
            x += pas_x
        y += pas_y
        row += 1

    # Sceau central plus marqué
    try:
        c.setFillAlpha(0.16)
        c.setStrokeAlpha(0.22)
    except Exception:
        pass
    cx, cy = largeur / 2, hauteur / 2 - 5 * mm
    _sceau(c, cx, cy, 78 * mm)

    # Texte diagonal
    try:
        c.setFillAlpha(0.22)
    except Exception:
        pass
    c.setFillColorRGB(0.72, 0.76, 0.80)
    c.setFont('Helvetica-Bold', 34)
    c.saveState()
    c.translate(largeur / 2, hauteur / 2)
    c.rotate(35)
    c.drawCentredString(0, 10, 'EDUCATION NATIONALE RDC')
    c.setFont('Helvetica', 12)
    c.drawCentredString(0, -12, 'RÉPUBLIQUE DÉMOCRATIQUE DU CONGO')
    c.restoreState()

    c.restoreState()


def generer_pdf_fiche_eleve(eleve) -> bytes:
    """Produit un PDF A4 de la fiche d'identité scolaire de l'élève."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largeur, hauteur = A4

    _dessiner_filigrane(c, largeur, hauteur)
    _dessiner_en_tete(c, largeur, hauteur)

    y = hauteur - 48 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(18 * mm, y, eleve.nom_complet)
    y -= 6 * mm
    c.setFillColorRGB(0.3, 0.35, 0.4)
    c.setFont('Helvetica', 11)
    label_id = 'Numéro Identification : '
    c.drawString(18 * mm, y, label_id)
    c.setFont('Helvetica-Bold', 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(18 * mm + c.stringWidth(label_id, 'Helvetica', 11), y, _texte(eleve.numero_identification))
    y -= 6 * mm
    c.setFont('Helvetica', 11)
    c.setFillColorRGB(0.3, 0.35, 0.4)
    c.drawString(18 * mm, y, f'Numéro Permanent : {_texte(eleve.numero_permanent)}')
    y -= 6 * mm
    c.setFont('Helvetica', 11)
    c.setFillColorRGB(0.3, 0.35, 0.4)
    c.drawString(18 * mm, y, f'Numéro Impôt : {_texte(eleve.numero_impot)}')

    photo_x = largeur - 52 * mm
    photo_top = hauteur - 38 * mm  # juste sous le bandeau
    _photo(c, eleve, photo_x, photo_top)

    # QR unique sous la photo
    qr_size = 28 * mm
    qr_y = photo_top - 40 * mm - 3 * mm
    if eleve.qr_code:
        try:
            c.drawImage(
                eleve.qr_code.path,
                photo_x + 2 * mm,
                qr_y - qr_size,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass
    c.setFillColorRGB(0.3, 0.35, 0.4)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(photo_x + 16 * mm, qr_y - qr_size - 4 * mm, _texte(eleve.code_unique))

    y = hauteur - 78 * mm
    y = _section(c, 'Identité', y, largeur)
    y = _ligne(c, 'Nom', eleve.nom, y)
    y = _ligne(c, 'Postnom', eleve.postnom, y)
    y = _ligne(c, 'Prénom', eleve.prenom, y)
    y = _ligne(c, 'Sexe', eleve.get_sexe_display(), y)
    y = _ligne(c, 'Né(e) le', _date_fr(eleve.date_naissance), y)
    y = _ligne(c, 'Lieu de naissance', eleve.lieu_naissance, y)
    y = _ligne(c, 'Code QR', eleve.code_unique, y)

    y -= 3 * mm
    y = _section(c, 'Scolarité', y, largeur)
    ecole = eleve.ecole
    y = _ligne(c, 'École', ecole.nom if ecole else '—', y)
    y = _ligne(c, 'Code école', getattr(ecole, 'code', None), y)
    classe = eleve.classe if eleve.classe_id else None
    parts = []
    if classe:
        parts.append(classe.nom)
        if getattr(classe, 'section', None) and classe.section.nom:
            parts.append(classe.section.nom)
        if getattr(classe, 'option', None) and classe.option.nom:
            parts.append(classe.option.nom)
    y = _ligne(c, 'Classe', ' · '.join(parts) if parts else '—', y)
    y = _ligne(c, 'Adresse', eleve.adresse, y)
    inscription = eleve.date_inscription.date() if eleve.date_inscription else None
    y = _ligne(c, 'Inscription', _date_fr(inscription), y)

    y -= 3 * mm
    y = _section(c, 'Parents & contacts', y, largeur)
    y = _ligne(c, 'Père', eleve.nom_complet_pere or '—', y)
    y = _ligne(c, 'Tél. père', eleve.telephone_pere, y)
    y = _ligne(c, 'Profession père', eleve.profession_pere, y)
    y = _ligne(c, 'Mère', eleve.nom_complet_mere or '—', y)
    y = _ligne(c, 'Tél. mère', eleve.telephone_mere, y)
    y = _ligne(c, 'Profession mère', eleve.profession_mere, y)
    y = _ligne(c, 'Tuteur', eleve.nom_tuteur, y)
    y = _ligne(c, 'Lien tuteur', eleve.get_lien_tuteur_display() if eleve.lien_tuteur else '—', y)
    y = _ligne(c, 'Tél. tuteur', eleve.telephone_tuteur, y)

    bio = getattr(eleve, 'biometrie', None)
    if bio:
        y -= 3 * mm
        y = _section(c, 'Biométrie', y, largeur)
        y = _ligne(c, 'Statut', 'Validée' if bio.validee else 'En attente', y)

    cartes = list(getattr(eleve, 'cartes', []).all()[:3]) if hasattr(eleve, 'cartes') else []
    if cartes:
        y -= 3 * mm
        y = _section(c, 'Cartes scolaires', y, largeur)
        for carte in cartes:
            y = _ligne(
                c,
                carte.numero_carte,
                f'{carte.get_statut_display()} — exp. {_date_fr(carte.date_expiration)}',
                y,
                x_val=70 * mm,
            )

    # Date d'impression — bas droit
    c.setFillColorRGB(0.35, 0.4, 0.45)
    c.setFont('Helvetica', 8)
    c.drawRightString(
        largeur - 14 * mm,
        22 * mm,
        f'Imprimé le {_date_fr(timezone.localdate())} à {datetime.now().strftime("%H:%M")}',
    )

    c.setFillColorRGB(0.81, 0.07, 0.15)
    c.rect(0, 12 * mm, largeur, 8 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica', 8)
    c.drawCentredString(
        largeur / 2,
        14.5 * mm,
        'Document généré par Educ_RDC — usage administratif scolaire',
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
