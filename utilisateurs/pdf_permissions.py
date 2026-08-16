"""Génération PDF — matrice des permissions par rôle."""
from __future__ import annotations

import io

from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .matrice_permissions import get_contexte_permissions

BLEU = (0.0, 0.5, 1.0)
ROUGE = (0.81, 0.07, 0.15)
GRIS = (0.35, 0.4, 0.45)


def _tronquer(texte, max_len):
    t = (texte or '').strip() or '—'
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + '…'


def generer_pdf_matrice_permissions(*, genere_par=None) -> bytes:
    """PDF paysage : matrice capacités × rôles + légende."""
    ctx = get_contexte_permissions()
    roles = ctx['roles_permissions']
    lignes = ctx['lignes_matrice']
    legende = ctx['niveaux_legende']

    buffer = io.BytesIO()
    page = landscape(A4)
    largeur, hauteur = page
    c = canvas.Canvas(buffer, pagesize=page)

    marge_g = 12 * mm
    marge_d = 12 * mm
    marge_h = 14 * mm
    y_min = 16 * mm
    table_w = largeur - marge_g - marge_d

    # Colonnes : domaine | capacité | rôles…
    col_domaine = 28 * mm
    col_capa = 58 * mm
    col_roles_w = table_w - col_domaine - col_capa
    col_role = col_roles_w / max(len(roles), 1)
    row_h = 7.2 * mm

    now = timezone.localtime()

    def _entete(page_num):
        c.setFillColorRGB(*BLEU)
        c.rect(0, hauteur - 18 * mm, largeur, 18 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(marge_g, hauteur - 11 * mm, 'Educ_RDC — Matrice des permissions')
        c.setFont('Helvetica', 8)
        c.drawRightString(
            largeur - marge_d,
            hauteur - 11 * mm,
            f'Généré le {now.strftime("%d/%m/%Y %H:%M")}',
        )

        y = hauteur - 24 * mm
        c.setFillColorRGB(0.1, 0.15, 0.2)
        c.setFont('Helvetica', 8)
        leg = '  ·  '.join(f"{n['court']} = {n['label']}" for n in legende)
        c.drawString(marge_g, y, _tronquer(leg, 140))
        if genere_par:
            c.setFillColorRGB(*GRIS)
            c.drawRightString(largeur - marge_d, y, f'Par : {_tronquer(genere_par, 40)}')

        y = hauteur - 32 * mm
        c.setFillColorRGB(0.94, 0.96, 0.98)
        c.rect(marge_g, y - 2 * mm, table_w, row_h + 2 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0.05, 0.2, 0.35)
        c.setFont('Helvetica-Bold', 7.5)
        x = marge_g + 1.5 * mm
        c.drawString(x, y + 1.5 * mm, 'Domaine')
        x = marge_g + col_domaine + 1.5 * mm
        c.drawString(x, y + 1.5 * mm, 'Capacité')
        x = marge_g + col_domaine + col_capa
        for role in roles:
            label = _tronquer(role['label'], 16)
            c.drawCentredString(x + col_role / 2, y + 1.5 * mm, label)
            x += col_role
        c.setStrokeColorRGB(0.75, 0.8, 0.85)
        c.setLineWidth(0.4)
        c.line(marge_g, y - 2 * mm, largeur - marge_d, y - 2 * mm)
        return y - 2 * mm - row_h

    def _pied(page_num):
        c.setFillColorRGB(*ROUGE)
        c.rect(0, 0, largeur, 8 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont('Helvetica', 7)
        c.drawString(marge_g, 2.8 * mm, 'Source : code applicatif — consultation admin')
        c.drawRightString(largeur - marge_d, 2.8 * mm, f'Page {page_num}')

    page_num = 1
    y = _entete(page_num)

    for idx, ligne in enumerate(lignes):
        if y < y_min + row_h:
            _pied(page_num)
            c.showPage()
            page_num += 1
            y = _entete(page_num)

        if idx % 2 == 0:
            c.setFillColorRGB(0.97, 0.98, 0.99)
            c.rect(marge_g, y - 1.5 * mm, table_w, row_h, fill=1, stroke=0)

        c.setFillColorRGB(0.25, 0.3, 0.35)
        c.setFont('Helvetica-Bold' if ligne.get('show_domaine') else 'Helvetica', 7)
        domaine = ligne['domaine'] if ligne.get('show_domaine') else ''
        c.drawString(marge_g + 1.5 * mm, y + 1 * mm, _tronquer(domaine, 18))

        c.setFillColorRGB(0.1, 0.12, 0.16)
        c.setFont('Helvetica', 7)
        c.drawString(
            marge_g + col_domaine + 1.5 * mm,
            y + 1 * mm,
            _tronquer(ligne['libelle'], 42),
        )

        x = marge_g + col_domaine + col_capa
        c.setFont('Helvetica', 6.5)
        for cell in ligne['cellules']:
            court = cell['niveau_meta']['court']
            niveau = cell['niveau']
            if niveau == 'write':
                c.setFillColorRGB(0.06, 0.48, 0.27)
            elif niveau == 'read':
                c.setFillColorRGB(0.0, 0.34, 0.66)
            elif niveau == 'partial':
                c.setFillColorRGB(0.54, 0.43, 0.0)
            elif niveau == 'denied':
                c.setFillColorRGB(0.62, 0.05, 0.11)
            else:
                c.setFillColorRGB(0.4, 0.45, 0.5)
            c.drawCentredString(x + col_role / 2, y + 1 * mm, court)
            x += col_role

        c.setStrokeColorRGB(0.88, 0.9, 0.92)
        c.setLineWidth(0.3)
        c.line(marge_g, y - 1.5 * mm, largeur - marge_d, y - 1.5 * mm)
        y -= row_h

    # Résumés des rôles (pages suivantes)
    _pied(page_num)
    c.showPage()
    page_num += 1

    roles_details = ctx['roles_details']
    y = hauteur - marge_h
    c.setFillColorRGB(*BLEU)
    c.rect(0, hauteur - 16 * mm, largeur, 16 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(marge_g, hauteur - 10 * mm, 'Détail des rôles')
    y = hauteur - 24 * mm

    for role in roles_details:
        besoin = 22 * mm + len(role.get('domaines') or []) * 4 * mm
        if y < y_min + besoin:
            _pied(page_num)
            c.showPage()
            page_num += 1
            c.setFillColorRGB(*BLEU)
            c.rect(0, hauteur - 16 * mm, largeur, 16 * mm, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont('Helvetica-Bold', 13)
            c.drawString(marge_g, hauteur - 10 * mm, 'Détail des rôles (suite)')
            y = hauteur - 24 * mm

        c.setFillColorRGB(0.05, 0.2, 0.35)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(marge_g, y, role['label'])
        c.setFont('Helvetica', 8)
        c.setFillColorRGB(*GRIS)
        c.drawString(marge_g + 70 * mm, y, f"({role['code']})")
        y -= 4.5 * mm
        c.setFillColorRGB(0.15, 0.18, 0.22)
        c.setFont('Helvetica', 8)
        c.drawString(marge_g, y, _tronquer(f"Périmètre : {role['scope']}", 120))
        y -= 4 * mm
        # résumé wrap simple
        resume = role.get('resume') or ''
        c.setFillColorRGB(0.3, 0.35, 0.4)
        while resume:
            chunk = resume[:110]
            if len(resume) > 110:
                cut = chunk.rfind(' ')
                if cut > 60:
                    chunk = resume[:cut]
            c.drawString(marge_g, y, chunk.strip())
            resume = resume[len(chunk):].lstrip()
            y -= 3.5 * mm
        y -= 2 * mm
        for bloc in role.get('domaines') or []:
            writes = sum(1 for i in bloc['items'] if i['niveau'] == 'write')
            reads = sum(1 for i in bloc['items'] if i['niveau'] == 'read')
            denied = sum(1 for i in bloc['items'] if i['niveau'] == 'denied')
            partial = sum(1 for i in bloc['items'] if i['niveau'] == 'partial')
            c.setFillColorRGB(0.1, 0.15, 0.2)
            c.setFont('Helvetica-Bold', 7.5)
            c.drawString(marge_g + 3 * mm, y, bloc['domaine'])
            c.setFont('Helvetica', 7)
            c.setFillColorRGB(*GRIS)
            c.drawString(
                marge_g + 35 * mm,
                y,
                f'Écriture {writes} · Lecture {reads} · Partiel {partial} · Interdit {denied}',
            )
            y -= 3.8 * mm
        y -= 4 * mm

    _pied(page_num)
    c.save()
    buffer.seek(0)
    return buffer.read()
