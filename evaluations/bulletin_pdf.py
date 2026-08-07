"""
Génération PDF du bulletin scolaire officiel RDC
(modèle IGE/EPSP./172 — reproduction fidèle).
"""
from __future__ import annotations

import io
import math
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from eleves.models import Eleve
from .models import AnneeScolaire, BulletinDecision
from .services import _fmt, calculer_bulletin_eleve


NOIR = colors.black
GRIS = colors.Color(0.25, 0.25, 0.25)
FOND_MAX = colors.Color(0.92, 0.92, 0.92)
FOND_HEAD = colors.Color(0.94, 0.94, 0.94)
BLEU = colors.Color(0 / 255, 127 / 255, 255 / 255)
ROUGE = colors.Color(206 / 255, 17 / 255, 38 / 255)
JAUNE = colors.Color(252 / 255, 209 / 255, 22 / 255)
FILIGRANE = colors.Color(0.88, 0.88, 0.88)


def _draw_double_border(c: canvas.Canvas, x, y, w, h, gap=1.2 * mm):
    c.setStrokeColor(NOIR)
    c.setLineWidth(1.1)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setLineWidth(0.4)
    c.rect(x + gap, y + gap, w - 2 * gap, h - 2 * gap, stroke=1, fill=0)


def _draw_boxes(c: canvas.Canvas, x, y, n, box_w=3.0 * mm, box_h=4.0 * mm, text=''):
    chars = list((text or '').upper().replace(' ', '')[:n])
    for i in range(n):
        bx = x + i * box_w
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.45)
        c.rect(bx, y, box_w, box_h, stroke=1, fill=0)
        if i < len(chars):
            c.setFont('Helvetica', 6)
            c.setFillColor(NOIR)
            c.drawCentredString(bx + box_w / 2, y + 1.0 * mm, chars[i])


def _field(c, x, y, label, value, end_x=None, label_font=7):
    """Libellé + valeur (sans points de suite)."""
    c.setFillColor(NOIR)
    c.setFont('Helvetica-Bold', label_font)
    c.drawString(x, y, label)
    label_w = c.stringWidth(label, 'Helvetica-Bold', label_font)
    val = (value or '').strip()
    if val:
        c.setFont('Helvetica', label_font)
        c.drawString(x + label_w + 1.2 * mm, y, val)


def _draw_flag(c: canvas.Canvas, x, y, w=18 * mm, h=12 * mm):
    c.setFillColor(BLEU)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setStrokeColor(JAUNE)
    c.setLineWidth(2.4)
    c.line(x, y, x + w, y + h)
    c.setStrokeColor(ROUGE)
    c.setLineWidth(1.3)
    c.line(x, y, x + w, y + h)
    # Étoile (approximation)
    c.setFillColor(JAUNE)
    cx, cy = x + 3.6 * mm, y + h - 3.6 * mm
    _star(c, cx, cy, 2.0 * mm)


def _star(c, cx, cy, r):
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for px, py in pts[1:]:
        p.lineTo(px, py)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def _draw_logo_mineduc(c: canvas.Canvas, x, y, size=16 * mm):
    # Préférer le logo léger (évite PDF > 2 Mo)
    candidates = [
        Path(settings.BASE_DIR) / 'static' / 'img' / 'logo_MINEDUC1.png',
        Path(settings.BASE_DIR) / 'static' / 'img' / 'logo_MINEDUC.png',
        Path(settings.BASE_DIR) / 'static' / 'img' / 'armoiries_rdc.png',
    ]
    for path in candidates:
        if path.exists():
            c.drawImage(
                str(path), x, y, width=size, height=size,
                preserveAspectRatio=True, mask='auto',
            )
            return
    # Sceau circulaire de secours
    cx, cy = x + size / 2, y + size / 2
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.9)
    c.circle(cx, cy, size / 2 - 0.3 * mm, stroke=1, fill=0)
    c.setLineWidth(0.4)
    c.circle(cx, cy, size / 2 - 1.4 * mm, stroke=1, fill=0)
    c.setFont('Helvetica-Bold', 4.5)
    c.setFillColor(NOIR)
    c.drawCentredString(cx, cy + 1.2 * mm, 'R.D.C.')
    c.setFont('Helvetica', 3.8)
    c.drawCentredString(cx, cy - 1.8 * mm, 'MINEDUC')


def _draw_watermark(c: canvas.Canvas, cx, cy, size=55 * mm):
    """Filigrane armoiries (cercle + étoile) au centre du tableau."""
    c.saveState()
    c.setStrokeColor(FILIGRANE)
    c.setFillColor(FILIGRANE)
    c.setLineWidth(1.2)
    c.circle(cx, cy, size / 2, stroke=1, fill=0)
    c.circle(cx, cy, size / 2 - 3 * mm, stroke=1, fill=0)
    _star(c, cx, cy + 2 * mm, size * 0.18)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(cx, cy - 10 * mm, 'R.D. CONGO')
    c.restoreState()


def _checkbox_dash(c, x, y, label, checked=False):
    """Case style officiel : tiret + case + libellé."""
    c.setFillColor(NOIR)
    c.setFont('Helvetica', 7)
    c.drawString(x, y + 0.4 * mm, '-')
    bx = x + 3.2 * mm
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.6)
    c.rect(bx, y, 3.0 * mm, 3.0 * mm, stroke=1, fill=0)
    if checked:
        c.setFont('Helvetica-Bold', 8)
        c.drawString(bx + 0.4 * mm, y + 0.3 * mm, 'X')
    c.setFont('Helvetica', 7)
    c.drawString(bx + 4.2 * mm, y + 0.4 * mm, label)


def _maxima_cells(base: Decimal) -> list[str]:
    """P1 P2 Exam Tot | P3 P4 Exam Tot | TG | % | Sign."""
    p = base
    exam = base * 2
    tot = base * 4
    tg = base * 8
    return [
        _fmt(p), _fmt(p), _fmt(exam), _fmt(tot),
        _fmt(p), _fmt(p), _fmt(exam), _fmt(tot),
        _fmt(tg), '', '',
    ]


def _sum_cols(lignes, code_map) -> tuple[list, list]:
    """Totaux et maxima par colonne numérique (9 cols : p1..tg)."""
    tot = [Decimal('0')] * 9
    mx = [Decimal('0')] * 9
    has = [False] * 9

    for ligne in lignes:
        base = ligne['maximum_base']
        cells_max = _maxima_cells(base)
        for i in range(9):
            try:
                mx[i] += Decimal(cells_max[i] or '0')
            except Exception:
                pass
        notes = ligne['notes']

        def nv(code):
            pid = code_map.get(code)
            if pid is None:
                return None
            return notes.get(pid)

        vals = [
            nv('p1'), nv('p2'), nv('exam1'), ligne.get('tot1'),
            nv('p3'), nv('p4'), nv('exam2'), ligne.get('tot2'),
            ligne.get('total'),
        ]
        for i, v in enumerate(vals):
            if v is not None:
                tot[i] += Decimal(str(v))
                has[i] = True

    tot_fmt = [_fmt(tot[i]) if has[i] else '' for i in range(9)]
    mx_fmt = [_fmt(v) for v in mx]
    pct_fmt = []
    for i in range(9):
        if has[i] and mx[i] > 0:
            pct_fmt.append(_fmt(tot[i] * 100 / mx[i], 2))
        else:
            pct_fmt.append('')
    return mx_fmt, tot_fmt, pct_fmt


def _motif_barcode(c, x, y, w, h=2.2 * mm):
    """Motif décoratif type code-barres (APPLICATION / CONDUITE)."""
    c.saveState()
    c.setFillColor(colors.Color(0.15, 0.15, 0.15))
    xx = x
    i = 0
    while xx < x + w:
        bw = 0.5 * mm if i % 3 else 1.1 * mm
        c.rect(xx, y, bw, h, stroke=0, fill=1)
        xx += bw + 0.45 * mm
        i += 1
    c.restoreState()


def generer_pdf_bulletin_officiel(eleve: Eleve, annee: AnneeScolaire) -> bytes:
    """Reproduce le bulletin officiel IGE/EPSP en portrait A4."""
    data = calculer_bulletin_eleve(eleve, annee)
    ecole = data['ecole']
    classe = data['classe']
    periodes = data['periodes']
    decision: BulletinDecision = data['decision']
    secondaire = annee.regime == AnneeScolaire.Regime.SECONDAIRE

    buffer = io.BytesIO()
    page = A4
    c = canvas.Canvas(buffer, pagesize=page)
    width, height = page
    margin = 6 * mm
    inner = 1.6 * mm
    content_x = margin + inner
    content_w = width - 2 * (margin + inner)

    _draw_double_border(c, margin, margin, width - 2 * margin, height - 2 * margin)

    # ——— Tableau d'en-tête complet (République → CODE / N° PERM.) ———
    top = height - margin - inner - 1.5 * mm
    pad = 1.4 * mm
    row_rep = 15 * mm            # drapeau + titres + sceau
    row_full = 5.6 * mm          # N° ID, PROVINCE
    row_id = 5.2 * mm            # VILLE…CODE
    n_id_rows = 4
    header_table_h = row_rep + 2 * row_full + n_id_rows * row_id
    hx = content_x
    hw = content_w
    hy_top = top
    hy_bot = top - header_table_h
    mid_x = hx + hw / 2

    c.setStrokeColor(NOIR)
    c.setLineWidth(0.8)
    c.rect(hx, hy_bot, hw, header_table_h, stroke=1, fill=0)

    # Séparatrices horizontales
    heights = (row_rep, row_full, row_full) + (row_id,) * n_id_rows
    y_line = hy_top
    for h in heights:
        y_line -= h
        if y_line > hy_bot + 0.1:
            c.setLineWidth(0.55)
            c.line(hx, y_line, hx + hw, y_line)

    # Séparatrice verticale (bloc identité 2 colonnes uniquement)
    split_top = hy_top - row_rep - 2 * row_full
    c.setLineWidth(0.55)
    c.line(mid_x, hy_bot, mid_x, split_top)

    # — Ligne République —
    rep_bot = hy_top - row_rep
    _draw_flag(c, hx + 2 * mm, rep_bot + 1.5 * mm, w=17 * mm, h=11.5 * mm)
    _draw_logo_mineduc(c, hx + hw - 16 * mm, rep_bot + 0.5 * mm, size=13.5 * mm)
    c.setFillColor(NOIR)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawCentredString(width / 2, hy_top - 5.5 * mm, 'REPUBLIQUE DEMOCRATIQUE DU CONGO')
    c.setFont('Helvetica-Bold', 6.8)
    c.drawCentredString(
        width / 2, hy_top - 9.5 * mm,
        "MINISTERE DE L'EDUCATION NATIONALE ET NOUVELLE CITOYENNETE",
    )

    # — N° ID. —
    row0_y = rep_bot - row_full
    c.setFont('Helvetica-Bold', 7.5)
    c.drawString(hx + pad, row0_y + 1.6 * mm, 'N° ID.')
    nid = (eleve.numero_identification or eleve.matricule or '')[:27]
    box_w_id = min(3.0 * mm, (hw - 16 * mm) / 27)
    _draw_boxes(
        c, hx + 13 * mm, row0_y + 0.7 * mm, 27,
        box_w=box_w_id, box_h=3.8 * mm, text=nid,
    )

    # — PROVINCE EDUCATIONNELLE —
    row1_y = row0_y - row_full
    pe = getattr(ecole, 'province_educationnelle', None)
    _field(c, hx + pad, row1_y + 1.6 * mm, 'PROVINCE EDUCATIONNELLE :', pe.nom if pe else '')

    # — Identité 2 colonnes —
    sexe = (eleve.get_sexe_display()[0] if eleve.sexe else '')
    nom = (eleve.nom_complet or '')[:32]
    lieu = (eleve.lieu_naissance or '')[:20]
    date_n = eleve.date_naissance.strftime('%d / %m / %Y') if eleve.date_naissance else ''

    id_rows = [
        ('VILLE :', '', 'eleve_sexe'),
        ('COMMUNE / TER. (1) :', '', 'ne_le'),
        ('ECOLE :', ecole.nom[:38], 'classe'),
        ('CODE :', None, 'perm'),
    ]

    ry = split_top
    for llabel, lval, rkind in id_rows:
        ry -= row_id
        ty = ry + 1.5 * mm
        c.setFillColor(NOIR)

        if rkind == 'perm':
            c.setFont('Helvetica-Bold', 7)
            c.drawString(hx + pad, ty, 'CODE :')
            _draw_boxes(
                c, hx + 14 * mm, ry + 0.6 * mm, 10,
                box_w=3.0 * mm, box_h=3.6 * mm, text=ecole.code or '',
            )
            c.setFont('Helvetica-Bold', 7)
            c.drawString(mid_x + pad, ty, 'N° PERM. :')
            _draw_boxes(
                c, mid_x + 17 * mm, ry + 0.6 * mm, 15,
                box_w=2.75 * mm, box_h=3.6 * mm,
                text=eleve.numero_permanent or '',
            )
            continue

        _field(c, hx + pad, ty, llabel, lval or '')

        if rkind == 'eleve_sexe':
            sexe_x = hx + hw - 20 * mm
            _field(c, mid_x + pad, ty, 'ELEVE :', nom)
            c.setFont('Helvetica-Bold', 7)
            c.drawString(sexe_x, ty, 'SEXE :')
            if sexe:
                c.setFont('Helvetica', 7)
                c.drawString(sexe_x + 11 * mm, ty, sexe)
        elif rkind == 'ne_le':
            le_x = hx + hw - 32 * mm
            _field(c, mid_x + pad, ty, 'NE(E) A :', lieu)
            c.setFont('Helvetica-Bold', 7)
            c.drawString(le_x, ty, 'LE')
            if date_n:
                c.setFont('Helvetica', 7)
                c.drawString(le_x + 5 * mm, ty, date_n)
        elif rkind == 'classe':
            _field(c, mid_x + pad, ty, 'CLASSE :', classe.nom if classe else '')

    y = hy_bot - 4 * mm

    # ——— Titre ———
    titre_classe = (classe.nom if classe else 'CLASSE').upper()
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(
        width / 2, y,
        f'BULLETIN DE LA {titre_classe}   ANNEE SCOLAIRE {annee.libelle}',
    )
    y -= 2.2 * mm

    # ——— Tableau ———
    if secondaire:
        h1 = [
            'BRANCHES',
            'PREMIER SEMESTRE', '', '', '',
            'SECOND SEMESTRE', '', '', '',
            'T.G.',
            'EXAMEN DE\nREPECHAGE', '',
        ]
        h2 = [
            '',
            'TR. JOURNAL.', '', 'EXAM.', 'TOT.',
            'TR. JOURNAL.', '', 'EXAM.', 'TOT.',
            '',
            '%', 'SIGN.\nPROF.',
        ]
        h3 = [
            '',
            '1ère P.', '2e P.', '', '',
            '3e P.', '4e P.', '', '',
            '',
            '', '',
        ]
        table_data = [h1, h2, h3]
        spans = [
            ('SPAN', (1, 0), (4, 0)),
            ('SPAN', (5, 0), (8, 0)),
            ('SPAN', (10, 0), (11, 0)),
            ('SPAN', (0, 0), (0, 2)),
            ('SPAN', (1, 1), (2, 1)),
            ('SPAN', (5, 1), (6, 1)),
            ('SPAN', (3, 1), (3, 2)),
            ('SPAN', (4, 1), (4, 2)),
            ('SPAN', (7, 1), (7, 2)),
            ('SPAN', (8, 1), (8, 2)),
            ('SPAN', (9, 0), (9, 2)),
            ('SPAN', (10, 1), (10, 2)),
            ('SPAN', (11, 1), (11, 2)),
        ]
        code_map = {p.code: p.id for p in periodes}

        def note_val(notes, code):
            pid = code_map.get(code)
            if pid is None:
                return ''
            v = notes.get(pid)
            return _fmt(v) if v is not None else ''

        last_max = None
        for ligne in data['lignes']:
            base = ligne['maximum_base']
            if last_max != base:
                table_data.append(['MAXIMA'] + _maxima_cells(base))
                last_max = base
            notes = ligne['notes']
            table_data.append([
                ligne['matiere'],
                note_val(notes, 'p1'),
                note_val(notes, 'p2'),
                note_val(notes, 'exam1'),
                _fmt(ligne['tot1']) if ligne['tot1'] is not None else '',
                note_val(notes, 'p3'),
                note_val(notes, 'p4'),
                note_val(notes, 'exam2'),
                _fmt(ligne['tot2']) if ligne['tot2'] is not None else '',
                _fmt(ligne['total']) if ligne['total'] is not None else '',
                '',
                '',
            ])

        # Lignes vides pour densifier comme le formulaire imprimé
        for _ in range(max(0, 18 - len(data['lignes']))):
            table_data.append([''] + [''] * 11)

        mx_fmt, tot_fmt, pct_fmt = _sum_cols(data['lignes'], code_map)
        table_data.append(['MAXIMA GENERAUX'] + mx_fmt + ['', ''])
        table_data.append(['TOTAUX'] + tot_fmt + ['', ''])
        if not any(pct_fmt):
            pct_row = [''] * 9
            pct_row[8] = _fmt(data['pourcentage'], 2) if data['pourcentage'] is not None else ''
        else:
            pct_row = pct_fmt
        table_data.append(['POURCENTAGE'] + pct_row + ['', ''])
        place = f'{decision.place or ""} / {data["effectif"] or ""}'.strip()
        if place == '/':
            place = ' / '
        place_row = [''] * 9
        place_row[8] = place
        # Cadre PASSE/DOUBLE : 4 lignes (PLACE → Signature), colonnes % + SIGN.
        place_idx = len(table_data)
        table_data.append(["PLACE/NBRE D'ELEVES"] + place_row + ['', ''])
        table_data.append(['APPLICATION', decision.appreciation or '', '', '', '', '', '', '', '', '', '', ''])
        table_data.append(['CONDUITE', decision.conduite or '', '', '', '', '', '', '', '', '', '', ''])
        table_data.append(['Signature du responsable', '', '', '', '', '', '', '', '', '', '', ''])
        app_idx = place_idx

        usable_w = content_w
        col_w = [
            usable_w * 0.205,
            usable_w * 0.060, usable_w * 0.060, usable_w * 0.058, usable_w * 0.058,
            usable_w * 0.060, usable_w * 0.060, usable_w * 0.058, usable_w * 0.058,
            usable_w * 0.055,
            usable_w * 0.055, usable_w * 0.093,
        ]
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 2), 5.2),
            ('FONTSIZE', (0, 3), (-1, -1), 5.2),
            ('BACKGROUND', (0, 0), (-1, 2), FOND_HEAD),
            ('GRID', (0, 0), (-1, -1), 0.35, NOIR),
            ('BOX', (0, 0), (-1, -1), 0.8, NOIR),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0.7),
            ('TOPPADDING', (0, 0), (-1, -1), 0.7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.7),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ] + spans

        for i, row in enumerate(table_data):
            if row and str(row[0]).startswith('MAXIMA'):
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), FOND_MAX))
                style_cmds.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
            if row and row[0] in (
                'MAXIMA GENERAUX', 'TOTAUX', 'POURCENTAGE',
                "PLACE/NBRE D'ELEVES",
            ):
                style_cmds.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
            if row and row[0] == "PLACE/NBRE D'ELEVES":
                style_cmds.append(('SPAN', (10, i), (11, i + 3)))  # cadre décision
            if row and row[0] in (
                "PLACE/NBRE D'ELEVES", 'APPLICATION', 'CONDUITE', 'Signature du responsable',
            ):
                style_cmds.append(('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'))
                if row[0] != "PLACE/NBRE D'ELEVES":
                    style_cmds.append(('SPAN', (1, i), (9, i)))
                    style_cmds.append(('ALIGN', (1, i), (1, i), 'LEFT'))

        table = Table(table_data, colWidths=col_w, repeatRows=3)
        table.setStyle(TableStyle(style_cmds))
    else:
        headers = ['BRANCHES', '1er Trimestre', '2ème Trimestre', '3ème Trimestre', 'T.G.', '%']
        table_data = [headers]
        code_map = {p.code: p.id for p in periodes}
        for ligne in data['lignes']:
            notes = ligne['notes']

            def nv(code):
                pid = code_map.get(code)
                if pid is None:
                    return ''
                v = notes.get(pid)
                return _fmt(v) if v is not None else ''

            table_data.append([
                ligne['matiere'], nv('t1'), nv('t2'), nv('t3'),
                _fmt(ligne['total']) if ligne['total'] is not None else '',
                _fmt(ligne['pourcentage'], 2) if ligne['pourcentage'] is not None else '',
            ])
        table_data.append([
            'TOTAUX', '', '', '',
            _fmt(data['total_obtenu']) if data['total_obtenu'] is not None else '',
            _fmt(data['pourcentage'], 2) if data['pourcentage'] is not None else '',
        ])
        usable_w = content_w
        col_w = [usable_w * 0.35] + [usable_w * 0.13] * 5
        table = Table(table_data, colWidths=col_w, repeatRows=1)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, 0), FOND_HEAD),
            ('GRID', (0, 0), (-1, -1), 0.4, NOIR),
            ('BOX', (0, 0), (-1, -1), 0.8, NOIR),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        app_idx = None

    # Espace réservé au pied de page officiel
    footer_h = 40 * mm
    max_table_h = y - (margin + inner + footer_h)
    tw, th = table.wrap(usable_w, max_table_h)
    table_bottom = y - th
    row_heights = list(getattr(table, '_rowHeights', []) or [])

    # Filigrane derrière le tableau
    _draw_watermark(c, width / 2, table_bottom + th / 2, size=min(48 * mm, th * 0.5))

    table.drawOn(c, content_x, table_bottom)

    # Motifs APPLICATION / CONDUITE + cadre PASSE / DOUBLE
    if secondaire and app_idx is not None and row_heights:
        # 4 dernières lignes = PLACE → Signature (cadre décision officiel)
        block_h = sum(row_heights[-4:])
        h_sig = row_heights[-1]
        h_cond = row_heights[-2]
        h_app = row_heights[-3]

        if not (decision.appreciation or '').strip():
            _motif_barcode(
                c, content_x + col_w[0] + 1.5 * mm,
                table_bottom + h_sig + h_cond + h_app * 0.25,
                sum(col_w[1:10]) - 3 * mm, h=max(1.6 * mm, h_app * 0.45),
            )
        if not (decision.conduite or '').strip():
            _motif_barcode(
                c, content_x + col_w[0] + 1.5 * mm,
                table_bottom + h_sig + h_cond * 0.25,
                sum(col_w[1:10]) - 3 * mm, h=max(1.6 * mm, h_cond * 0.45),
            )

        dec_x = content_x + sum(col_w[:10])
        dec_w = col_w[10] + col_w[11]
        dec_y = table_bottom
        dec_h = block_h
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.8)
        c.setFillColor(colors.white)
        c.rect(dec_x, dec_y, dec_w, dec_h, stroke=1, fill=1)

        _checkbox_dash(
            c, dec_x + 1.0 * mm, dec_y + dec_h - 5.2 * mm, 'PASSE (1)',
            checked=decision.decision == BulletinDecision.Decision.PASSE,
        )
        _checkbox_dash(
            c, dec_x + 1.0 * mm, dec_y + dec_h - 9.8 * mm, 'DOUBLE (1)',
            checked=decision.decision == BulletinDecision.Decision.DOUBLE,
        )
        c.setFillColor(NOIR)
        c.setFont('Helvetica', 5.5)
        c.setFont('Helvetica', 5.5)
        if decision.date_decision:
            c.drawString(
                dec_x + 1.2 * mm, dec_y + 9.5 * mm,
                f'LE  {decision.date_decision.strftime("%d / %m / %Y")}',
            )
        else:
            c.drawString(dec_x + 1.2 * mm, dec_y + 9.5 * mm, 'LE')
        c.setFont('Helvetica', 5.2)
        c.drawString(dec_x + 1.2 * mm, dec_y + 5.8 * mm, "Le Chef d'Etablissement")
        c.drawString(dec_x + 1.2 * mm, dec_y + 2.5 * mm, "Sceau de l'Ecole")

    # ——— Pied de page officiel (libellés exacts du modèle) ———
    y = table_bottom - 3.2 * mm
    c.setFillColor(NOIR)
    c.setFont('Helvetica', 6.2)
    ligne_rep = (
        "- L'élève ne pourra passer dans la classe supérieure s'il n'a subi "
        "avec succès un examen de repêchage en "
    )
    c.drawString(content_x, y, ligne_rep)

    y -= 3.3 * mm
    c.setFont('Helvetica', 6.2)
    c.drawString(content_x, y, "- L'élève passe dans la classe supérieure (1)")
    y -= 3.0 * mm
    c.drawString(content_x, y, "- L'élève double sa classe (1)")

    y -= 3.8 * mm
    c.setFont('Helvetica', 6.5)
    if decision.date_decision:
        c.drawString(
            content_x, y,
            f'Fait à, le {decision.date_decision.strftime("%d / %m / %Y")}',
        )
    else:
        c.drawString(content_x, y, 'Fait à, le')

    y -= 7.5 * mm
    c.setFont('Helvetica', 6.5)
    c.drawString(content_x, y, "Signature de l'élève")
    c.drawCentredString(width / 2, y, "Sceau de l'Ecole")
    c.drawRightString(content_x + content_w, y, "Chef d'Etablissement, Noms et Signature")

    y -= 9.5 * mm
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.5)
    c.line(content_x, y, content_x + 40 * mm, y)
    c.circle(width / 2, y + 2.8 * mm, 7 * mm, stroke=1, fill=0)
    c.line(content_x + content_w - 52 * mm, y, content_x + content_w, y)
    if ecole.directeur:
        c.setFont('Helvetica', 5.5)
        c.drawRightString(content_x + content_w, y + 2.2 * mm, ecole.directeur)

    # Mentions légales (bas de page)
    base = margin + inner + 2 * mm
    c.setFont('Helvetica', 5.5)
    c.setFillColor(NOIR)
    c.drawString(content_x, base + 7.2 * mm, '(1) Biffer la mention inutile.')
    c.setFont('Helvetica-Oblique', 5.5)
    c.drawString(
        content_x, base + 4.6 * mm,
        "Note importante : Le bulletin est sans valeur s'il est raturé ou surchargé.",
    )
    c.setFillColor(GRIS)
    c.drawString(
        content_x, base + 2.0 * mm,
        'Interdiction formelle de reproduire ce bulletin sous peine des sanctions prévues par la loi.',
    )
    c.setFillColor(NOIR)
    c.setFont('Helvetica-Bold', 6)
    c.drawRightString(content_x + content_w, base + 2.0 * mm, 'IGE/EPSP./ 172')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
