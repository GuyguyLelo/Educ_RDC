"""
Génère le document Word professionnel du workflow métier Educ_RDC.
Usage: python docs/generer_workflow_metier.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from docx.shared import Cm, Pt, RGBColor, Twips


# Couleurs institutionnelles (alignées UI Educ_RDC)
BLEU_NUIT = RGBColor(0x0B, 0x2A, 0x4A)
BLEU = RGBColor(0x1A, 0x56, 0x8C)
JAUNE = RGBColor(0xF2, 0xC9, 0x4C)
GRIS = RGBColor(0x5A, 0x67, 0x72)
BLANC = RGBColor(0xFF, 0xFF, 0xFF)
VERT = RGBColor(0x1F, 0x7A, 0x4D)


def set_run_font(run, size=11, bold=False, color=None, name='Calibri'):
    run.font.name = name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def shade_cell(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    # Remplacer un éventuel ombrage existant
    for child in list(tcPr):
        if child.tag == qn('w:shd'):
            tcPr.remove(child)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), hex_color)
    shd.set(qn('w:val'), 'clear')
    tcPr.append(shd)


def set_cell_border(cell, color='1A568C', size='4'):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), size)
        el.set(qn('w:color'), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char_begin = OxmlElement('w:fldChar')
    fld_char_begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' PAGE '
    fld_char_end = OxmlElement('w:fldChar')
    fld_char_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_char_begin)
    run._r.append(instr)
    run._r.append(fld_char_end)
    set_run_font(run, size=9, color=GRIS)


def style_document(doc: Document):
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.0)

    # Styles de base
    normal = doc.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    for level, size, color in (
        (1, 16, BLEU_NUIT),
        (2, 13, BLEU),
        (3, 11.5, BLEU_NUIT),
    ):
        style = doc.styles[f'Heading {level}']
        style.font.name = 'Calibri'
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(16 if level == 1 else 12)
        style.paragraph_format.space_after = Pt(8)

    # En-tête / pied
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run('Educ_RDC  ·  Workflow métier  ·  Confidentialité interne')
    set_run_font(run, size=9, color=GRIS)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run('République Démocratique du Congo  —  Identification scolaire nationale  —  Page ')
    set_run_font(r1, size=9, color=GRIS)
    add_page_number(fp)


def add_horizontal_line(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '12')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '1A568C')
    pBdr.append(bottom)
    pPr.append(pBdr)


def add_cover(doc: Document):
    for _ in range(3):
        doc.add_paragraph()

    bandeau = doc.add_paragraph()
    bandeau.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = bandeau.add_run('RÉPUBLIQUE DÉMOCRATIQUE DU CONGO')
    set_run_font(r, size=12, bold=True, color=BLEU_NUIT)

    sous = doc.add_paragraph()
    sous.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sous.add_run('Système national d’identification scolaire')
    set_run_font(r, size=11, color=BLEU)

    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_horizontal_line(line)

    titre = doc.add_paragraph()
    titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titre.paragraph_format.space_before = Pt(28)
    r = titre.add_run('PROCESUS MÉTIER COMPLET')
    set_run_font(r, size=26, bold=True, color=BLEU_NUIT, name='Calibri Light')

    sous_titre = doc.add_paragraph()
    sous_titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sous_titre.add_run('Workflow opérationnel de la plateforme Educ_RDC')
    set_run_font(r, size=14, color=BLEU)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Pt(36)
    r = meta.add_run(
        f'Document de référence\nVersion 1.1  ·  {date.today().strftime("%d/%m/%Y")}\n'
        'Destination : maîtrise d’ouvrage, exploitation et formation'
    )
    set_run_font(r, size=11, color=GRIS)

    for _ in range(4):
        doc.add_paragraph()

    box = doc.add_paragraph()
    box.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = box.add_run(
        'Ce document décrit les acteurs, la hiérarchie territoriale,\n'
        'les processus de bout en bout et les règles métier applicables.'
    )
    set_run_font(r, size=10, color=GRIS)

    doc.add_page_break()


def add_toc_like(doc: Document):
    doc.add_heading('Sommaire', level=1)
    items = [
        '1. Objet et périmètre de la plateforme',
        '2. Acteurs et responsabilités',
        '3. Architecture organisationnelle',
        '4. Vue d’ensemble du workflow',
        '5. Processus détaillés',
        '   5.1 Paramétrage du référentiel territorial',
        '   5.2 Identification des écoles',
        '   5.3 Gestion des classes',
        '   5.4 Enregistrement des élèves et des parents',
        '   5.5 Identification du personnel scolaire',
        '   5.6 Gestion des comptes utilisateurs',
        '   5.7 Biométrie',
        '   5.8 Cartes scolaires (API / fiche élève)',
        '   5.9 Imports Excel',
        '   5.10 Pilotage, tableaux de bord et rapports',
        '6. Matrice RACI synthétique',
        '7. Règles métier structurantes',
        '8. Modules applicatifs et navigation',
        '9. Parcours type de mise en service',
        '10. Glossaire',
        '11. Historique des versions',
    ]
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(item)
        set_run_font(r, size=11, color=BLEU_NUIT)
    doc.add_page_break()


def add_para(doc, text, bold=False, size=11):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    if level:
        p.paragraph_format.left_indent = Cm(1.2 * level)
    r = p.add_run(text)
    set_run_font(r, size=11)
    return p


def add_numbered(doc, text):
    p = doc.add_paragraph(style='List Number')
    p.clear()
    r = p.add_run(text)
    set_run_font(r, size=11)
    return p


def make_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        r = p.add_run(h)
        set_run_font(r, size=10, bold=True, color=BLANC)
        shade_cell(cell, '0B2A4A')
        set_cell_border(cell, '0B2A4A', '6')
    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ''
            p = cell.paragraphs[0]
            r = p.add_run(str(value))
            set_run_font(r, size=9.5)
            if r_idx % 2 == 1:
                shade_cell(cell, 'F4F7FA')
            set_cell_border(cell, 'C5D0DC', '4')
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table


def add_callout(doc, title, text):
    p = doc.add_paragraph()
    r = p.add_run(f'▶ {title}  ')
    set_run_font(r, size=10, bold=True, color=BLEU)
    r2 = p.add_run(text)
    set_run_font(r2, size=10, color=GRIS)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)


def build():
    doc = Document()
    style_document(doc)
    add_cover(doc)
    add_toc_like(doc)

    # 1
    doc.add_heading('1. Objet et périmètre de la plateforme', level=1)
    add_para(
        doc,
        'Educ_RDC est la plateforme nationale d’identification scolaire de la '
        'République Démocratique du Congo. Elle assure le recensement et le suivi '
        'des établissements, des classes, des élèves (identité, parents, photo), '
        'du personnel scolaire, de la biométrie et des cartes scolaires, avec un '
        'pilotage territorial par rôle.'
    )
    add_para(doc, 'Objectifs opérationnels', bold=True)
    for t in [
        'Structurer le référentiel territorial (PA → PE → Antenne → École → Classe).',
        'Identifier de façon fiable les écoles et leurs effectifs.',
        'Enregistrer les élèves avec identité complète et contacts parentaux.',
        'Gérer les cartes scolaires via l’API et la fiche élève (PDF / QR).',
        'Donner à chaque acteur une vue adaptée à son périmètre.',
        'Accélérer le déploiement via imports Excel contrôlés.',
    ]:
        add_bullet(doc, t)
    add_callout(
        doc,
        'Navigation v1.1',
        'Le menu latéral est fixe (ne défile pas). Le module « Cartes » n’apparaît plus '
        'dans le menu : les cartes restent accessibles depuis la fiche élève et l’API.',
    )

    # 2
    doc.add_heading('2. Acteurs et responsabilités', level=1)
    add_para(
        doc,
        'L’accès est authentifié. Les droits dépendent du rôle métier rattaché '
        'au compte utilisateur.'
    )
    make_table(
        doc,
        ['Rôle', 'Périmètre', 'Droits principaux', 'Accès UI notable'],
        [
            ['Administrateur (admin)', 'National', 'Tous modules + comptes', 'Utilisateurs, Paramètres, tout le reste'],
            ['Agent national', 'National', 'Écriture opérationnelle, paramétrage', 'Paramètres (pas Gestion Utilisateurs)'],
            ['Agent provincial', 'Province éducationnelle', 'Écoles / élèves / biométrie / cartes (API) du PE', 'Listes filtrées PE'],
            ['Agent antenne', 'Antenne', 'Écoles / élèves / biométrie / cartes (API) de l’antenne', 'Listes filtrées antenne'],
            ['Administratif école (admin_ecole)', 'Son école', 'Fiche école, classes, élèves, parents, personnel, imports', 'Menu « Mon école » uniquement'],
            ['Enseignant', 'Sa classe titulaire', 'Lecture seule (élèves, parents, biométrie, cartes fiche)', 'Élèves — pas d’accès Écoles / Mon école'],
        ],
        col_widths=[3.5, 3.2, 4.5, 4.5],
    )
    add_callout(
        doc,
        'Règle d’écriture API',
        'Les enseignants ne peuvent pas créer, modifier ni supprimer via l’API. '
        'Les classes ne sont modifiables que par admin ou administratif école. '
        'Les comptes utilisateurs sont gérés exclusivement par l’administrateur.',
    )

    # 3
    doc.add_heading('3. Architecture organisationnelle', level=1)
    add_para(
        doc,
        'La hiérarchie territoriale constitue le socle du filtrage des données '
        'et des workflows.'
    )
    make_table(
        doc,
        ['Niveau', 'Entité', 'Rattachement', 'Rôle clé'],
        [
            ['1', 'Province administrative (PA)', '—', 'Découpage administratif'],
            ['2', 'Province éducationnelle (PE)', 'PA', 'Pilotilotage éducatif provincial'],
            ['3', 'Antenne', 'PE', 'Relais opérationnel local'],
            ['4', 'École', 'PE + Antenne', 'Établissement identifié'],
            ['5', 'Classe', 'École', 'Unité pédagogique'],
            ['6', 'Élève', 'École + Classe', 'Dossier scolaire'],
        ],
        col_widths=[1.5, 4.5, 3.5, 5.5],
    )
    add_para(doc, 'Rattachements des utilisateurs', bold=True)
    for t in [
        'Agents : rattachement PA / PE / Antenne selon le rôle.',
        'Administratif école et enseignant : rattachement à une école.',
        'Enseignant : rattachement obligatoire à une classe titulaire de son école.',
    ]:
        add_bullet(doc, t)

    # 4
    doc.add_heading('4. Vue d’ensemble du workflow', level=1)
    add_para(
        doc,
        'Le processus global suit un ordre de dépendance strict. Le non-respect '
        'de cet ordre bloque les étapes aval (ex. : élève sans classe existante).'
    )
    make_table(
        doc,
        ['Étape', 'Processus', 'Prérequis', 'Résultat'],
        [
            ['1', 'Paramétrage territorial', 'Compte national', 'PA, PE, Antennes actives'],
            ['2', 'Identification des écoles', 'Antenne / PE existants', 'Écoles référencées'],
            ['3', 'Création des classes', 'École existante', 'Classes ouvertes'],
            ['4', 'Enregistrement élèves & parents', 'Classe existante', 'Dossiers élèves complets'],
            ['5', 'Personnel scolaire', 'École existante', 'Effectifs RH identifiés'],
            ['6', 'Comptes utilisateurs école', 'École (+ classe pour enseignant)', 'Accès applicatifs'],
            ['7', 'Biométrie & cartes', 'Élève (+ photo)', 'Dossier biométrique / carte'],
            ['8', 'Pilotilotage & rapports', 'Données opérationnelles', 'Indicateurs & PDF'],
        ],
        col_widths=[1.5, 4.2, 4.3, 5.0],
    )

    # 5
    doc.add_heading('5. Processus détaillés', level=1)

    # 5.1
    doc.add_heading('5.1 Paramétrage du référentiel territorial', level=2)
    add_para(doc, 'Objectif : constituer le référentiel national PA / PE / Antennes.', bold=True)
    add_para(doc, 'Acteurs : Administrateur, Agent national.')
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Se connecter avec un compte national, ouvrir le menu Paramètres.',
        'Créer les provinces administratives (nom, code unique).',
        'Créer les provinces éducationnelles rattachées à une PA.',
        'Créer les antennes rattachées à une PE (adresse, téléphone).',
        'Contrôler la cohérence via l’organigramme.',
        'Modifier ou supprimer depuis la modale de détail (jamais depuis la liste).',
    ]:
        add_numbered(doc, t)
    add_callout(
        doc,
        'Ordre imposé',
        'PA → PE → Antennes → Écoles. Une antenne ne peut exister sans PE ; '
        'une école doit être rattachée à une PE et une antenne.',
    )

    # 5.2
    doc.add_heading('5.2 Identification des écoles', level=2)
    add_para(doc, 'Objectif : référencer chaque établissement scolaire.', bold=True)
    add_para(doc, 'Acteurs : Admin, Agent national / provincial / antenne, Administratif école (sa fiche).')
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Accéder à la liste Écoles (filtrée selon le périmètre territorial).',
        'Créer une école : identité, code unique, type, niveau, adresse, contacts, GPS, directeur, effectifs, rattachement PE/Antenne.',
        'Compléter la fiche : photos de l’établissement, localisation, effectifs.',
        'Pour l’administratif école : accès exclusif via « Mon école » (pas de liste nationale).',
        'Suppression éventuelle uniquement depuis la fiche détail.',
    ]:
        add_numbered(doc, t)
    add_para(doc, 'Règles', bold=True)
    for t in [
        'L’enseignant n’a aucun accès aux écrans Écoles.',
        'L’administratif école ne voit et ne gère que son établissement.',
        'Les agents ne voient que les écoles de leur PE ou antenne.',
    ]:
        add_bullet(doc, t)

    # 5.3
    doc.add_heading('5.3 Gestion des classes', level=2)
    add_para(doc, 'Objectif : ouvrir les classes pédagogiques avant tout enrôlement élève.', bold=True)
    add_para(doc, 'Acteurs : Administrateur, Administratif école.')
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Ouvrir la fiche école → section Classes.',
        'Créer une classe (nom unique dans l’école, code optionnel, statut actif).',
        'Importer éventuellement un fichier Excel/CSV de classes.',
        'Modifier / supprimer depuis la modale d’édition.',
        'Vérifier que les classes existent avant l’import ou la saisie des élèves.',
    ]:
        add_numbered(doc, t)
    add_callout(
        doc,
        'Point de contrôle',
        'Sans classe créée, aucun élève ne peut être enregistré et aucun compte '
        'enseignant ne peut être rattaché à une classe titulaire.',
    )

    # 5.4
    doc.add_heading('5.4 Enregistrement des élèves et des parents', level=2)
    add_para(doc, 'Objectif : constituer le dossier scolaire complet de l’élève.', bold=True)
    add_para(doc, 'Acteurs : Admin, agents territoriaux, administratif école ; enseignant en consultation.')
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Accéder à Élèves (ou depuis la fiche école).',
        'Saisir l’identité : matricule, N° identification / permanent, nom, postnom, prénom, sexe, naissance.',
        'Rattacher l’élève à une école et à une classe existante de cette école.',
        'Renseigner l’adresse de résidence.',
        'Saisir l’identité du père (noms, téléphone, e-mail, profession, photo).',
        'Saisir l’identité de la mère (mêmes informations).',
        'Désigner le tuteur / responsable (lien de parenté, contacts, photo).',
        'Déposer la photo de l’élève (initialise automatiquement la biométrie).',
        'Contrôler la fiche détail ; mettre à jour parents/photos si besoin.',
        'Importer en masse via Excel après création des classes.',
    ]:
        add_numbered(doc, t)
    make_table(
        doc,
        ['Bloc', 'Informations gérées'],
        [
            ['Identité élève', 'Matricule, N° ID / permanent, nom, postnom, prénom, sexe, date et lieu de naissance, photo'],
            ['Scolarité', 'École, classe obligatoire, adresse'],
            ['Père', 'Identité, téléphone, e-mail, profession, photo'],
            ['Mère', 'Identité, téléphone, e-mail, profession, photo'],
            ['Tuteur', 'Lien (père/mère/tuteur/oncle-tante/grand-parent/autre), nom, contacts, photo'],
        ],
        col_widths=[3.5, 12.0],
    )

    # 5.5
    doc.add_heading('5.5 Identification du personnel scolaire', level=2)
    add_para(
        doc,
        'Objectif : identifier le personnel RH de l’école (distinct des comptes de connexion).',
        bold=True,
    )
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Ouvrir la fiche école → section Personnel.',
        'Identifier un agent : matricule, identité, fonction (directeur, enseignant, secrétaire, etc.), contacts.',
        'Importer un fichier Excel/CSV de personnel si besoin.',
        'Mettre à jour les fiches via les modales d’édition.',
    ]:
        add_numbered(doc, t)

    # 5.6
    doc.add_heading('5.6 Gestion des comptes utilisateurs', level=2)
    add_para(doc, 'Objectif : délivrer les accès applicatifs selon le rôle et le périmètre.', bold=True)
    add_para(doc, 'Acteur exclusif : Administrateur.')
    add_para(doc, 'Enchaînement', bold=True)
    for t in [
        'Ouvrir Gestion Utilisateurs.',
        'Créer un agent territorial : rôle + rattachement PA/PE/Antenne.',
        'Créer un administratif école : rôle admin_ecole + école obligatoire.',
        'Créer un enseignant : école + classe titulaire obligatoire.',
        'Activer / désactiver le compte ; réinitialiser le mot de passe si besoin.',
        'Supprimer uniquement depuis la modale d’édition.',
    ]:
        add_numbered(doc, t)
    add_callout(
        doc,
        'Séparation des responsabilités',
        'Le personnel scolaire (RH) n’est pas un compte de connexion. '
        'Un enseignant RH peut exister sans compte ; un compte enseignant '
        'nécessite une classe titulaire.',
    )

    # 5.7
    doc.add_heading('5.7 Biométrie', level=2)
    add_para(doc, 'Objectif : constituer le dossier biométrique de l’élève.', bold=True)
    for t in [
        'La photo élève crée ou met à jour automatiquement l’enregistrement biométrique.',
        'Une empreinte de référence est générée (hash technique) et peut être validée via l’API.',
        'La fiche élève affiche le statut (validée / en attente) et la date de capture.',
        'Les indicateurs du tableau de bord comptabilisent les biométries validées du périmètre.',
    ]:
        add_numbered(doc, t)

    # 5.8
    doc.add_heading('5.8 Cartes scolaires (API / fiche élève)', level=2)
    add_para(doc, 'Objectif : produire et consulter les cartes scolaires sécurisées.', bold=True)
    add_callout(
        doc,
        'UI v1.1',
        'Le menu « Cartes » a été retiré de la navigation. La consultation opérationnelle '
        'se fait depuis la fiche élève (PDF / QR). L’émission et la gestion restent disponibles via l’API.',
    )
    for t in [
        'Émission via l’API (numéro automatique type RDC-…, expiration par défaut à +3 ans).',
        'Génération d’un QR code associé à la carte.',
        'Consultation et téléchargement PDF / QR depuis la fiche élève.',
        'Statuts : active, expirée, annulée.',
        'Les indicateurs « cartes actives » restent visibles au tableau de bord et dans les rapports.',
    ]:
        add_numbered(doc, t)

    # 5.9
    doc.add_heading('5.9 Imports Excel', level=2)
    add_para(doc, 'Objectif : accélérer le déploiement massif avec contrôle qualité.', bold=True)
    make_table(
        doc,
        ['Modèle', 'Où le télécharger', 'Où l’importer', 'Notes'],
        [
            ['PA / PE / Antennes', 'Paramètres → Modèles', 'Saisie UI Paramètres', 'Référentiel national'],
            ['Classes', 'Fiche école / modèles', 'Fiche école', 'Avant les élèves'],
            ['Élèves (+ parents)', 'Élèves / modèles', 'Page Élèves', 'Classe déjà créée'],
            ['Personnel', 'Fiche école / modèles', 'Fiche école', 'École obligatoire'],
            ['Écoles', 'Modèles / commandes', 'Procédures d’import dédiées', 'Après antennes'],
        ],
        col_widths=[3.2, 3.8, 3.5, 4.5],
    )
    add_para(
        doc,
        'Ordre recommandé d’import : Classes → Élèves → Comptes enseignants. '
        'Les imports élèves peuvent mettre à jour un dossier existant (même matricule).'
    )

    # 5.10
    doc.add_heading('5.10 Pilotage, tableaux de bord et rapports', level=2)
    add_para(doc, 'Objectif : suivre les indicateurs selon le périmètre de l’acteur.', bold=True)
    make_table(
        doc,
        ['Rôle', 'Portée du dashboard', 'Actions typiques'],
        [
            ['Admin / Agent national', 'Nationale', 'Suivi global, exports, administration'],
            ['Agent provincial', 'Province éducationnelle', 'Pilotage des antennes et écoles'],
            ['Agent antenne', 'Antenne', 'Suivi écoles / élèves / rapports'],
            ['Administratif école', 'École', 'Fiche école, élèves, parents, personnel, biométrie'],
            ['Enseignant', 'Classe titulaire', 'Consultation élèves de la classe (lecture seule)'],
        ],
        col_widths=[4.0, 4.5, 7.0],
    )
    add_para(
        doc,
        'Indicateurs principaux : élèves (dont répartition H/F), écoles, cartes actives, '
        'biométries validées, personnel (scope école). Export PDF disponible depuis Rapports. '
        'Aucun raccourci dashboard ne renvoie vers un menu Cartes.'
    )

    # 6 RACI
    doc.add_heading('6. Matrice RACI synthétique', level=1)
    add_para(
        doc,
        'R = Réalise  ·  A = Approuve / responsable  ·  C = Consulté  ·  I = Informé  ·  — = Non concerné'
    )
    make_table(
        doc,
        ['Processus', 'Admin', 'Nat.', 'Prov.', 'Antenne', 'Admin école', 'Enseignant'],
        [
            ['Paramétrage PA/PE/Antenne', 'A/R', 'R', '—', '—', '—', '—'],
            ['Identification écoles', 'A', 'R', 'R', 'R', 'R (sienne)', '—'],
            ['Gestion des classes', 'A/R', 'I', 'I', 'I', 'R', '—'],
            ['Élèves & parents', 'A', 'R', 'R', 'R', 'R', 'I (lecture)'],
            ['Personnel scolaire', 'A', 'R', 'R', 'R', 'R', '—'],
            ['Comptes utilisateurs', 'A/R', '—', '—', '—', 'I', '—'],
            ['Biométrie', 'A', 'R', 'R', 'R', 'R', 'I'],
            ['Cartes (API / fiche élève)', 'A', 'R', 'R', 'R', 'R', 'I'],
            ['Imports Excel', 'A', 'R', 'R', 'R', 'R', '—'],
            ['Dashboard / rapports', 'A/R', 'R', 'R', 'R', 'R', 'R'],
        ],
        col_widths=[4.2, 1.8, 1.6, 1.6, 1.8, 2.4, 2.4],
    )

    # 7
    doc.add_heading('7. Règles métier structurantes', level=1)
    rules = [
        'L’enseignant ne voit que les élèves de sa classe titulaire ; sans classe, aucune donnée élève.',
        'L’enseignant est en lecture seule (pas de création, modification, import ni suppression).',
        'L’enseignant n’a pas accès au menu « Mon école » ni à la liste des écoles.',
        'L’administratif école n’accède qu’à « Mon école » et aux données de son établissement.',
        'Les agents provinciaux / antenne sont filtrés automatiquement sur leur territoire.',
        'La classe est obligatoire pour tout élève et doit appartenir à son école.',
        'La classe titulaire est obligatoire pour tout compte enseignant.',
        'Les suppressions UI s’effectuent depuis la fiche détail ou la modale d’édition, jamais depuis les listes.',
        'La photo élève initialise / synchronise le dossier biométrique.',
        'Les parents (père, mère, tuteur) portent identité, contacts et photos.',
        'Les codes des structures territoriales sont uniques au niveau national.',
        'Les cartes portent un numéro automatique, une durée de validité et un QR code ; pas de menu Cartes dédié.',
        'La création des comptes applicatifs est réservée à l’administrateur.',
        'Le menu latéral est fixe : seul le contenu principal défile.',
    ]
    for i, rule in enumerate(rules, 1):
        p = doc.add_paragraph()
        r = p.add_run(f'R{i:02d}. ')
        set_run_font(r, size=11, bold=True, color=BLEU)
        r2 = p.add_run(rule)
        set_run_font(r2, size=11)

    # 8
    doc.add_heading('8. Modules applicatifs et navigation', level=1)
    add_para(doc, 'Menu latéral (ordre d’affichage)', bold=True)
    make_table(
        doc,
        ['Entrée menu', 'Visibilité', 'Fonction'],
        [
            ['Tableau de bord', 'Tous les rôles', 'Pilotage et indicateurs'],
            ['Mon école', 'Administratif école uniquement', 'Fiche de son établissement'],
            ['Écoles', 'Tous sauf enseignant et admin_ecole', 'Liste / identification des écoles'],
            ['Élèves', 'Tous (enseignant = sa classe)', 'Dossiers, parents, photo, import'],
            ['Rapports', 'Tous les rôles', 'Analyse et export PDF'],
            ['Gestion Utilisateurs', 'Administrateur uniquement', 'Comptes et rattachements'],
            ['Paramètres', 'Admin + Agent national', 'Référentiel territorial, modèles'],
        ],
        col_widths=[4.0, 5.0, 6.5],
    )
    add_para(
        doc,
        'Hors menu : les cartes scolaires sont consultées depuis la fiche élève ; '
        'l’API REST / JWT couvre les opérations avancées (émission de cartes, biométrie, etc.). '
        'Le menu latéral reste fixe à l’écran pendant le défilement du contenu.'
    )

    # 9
    doc.add_heading('9. Parcours type de mise en service', level=1)
    add_para(
        doc,
        'Scénario recommandé pour ouvrir une province / antenne / école en production :'
    )
    steps = [
        ('J0 — Gouvernance', 'Créer les comptes admin et agents nationaux ; valider le découpage PA/PE.'),
        ('J1 — Référentiel', 'Saisir PA, PE, Antennes ; contrôler l’organigramme.'),
        ('J2 — Établissements', 'Identifier les écoles de l’antenne (saisie ou import).'),
        ('J3 — Classes', 'Créer / importer les classes par école.'),
        ('J4 — Élèves', 'Importer ou saisir les élèves avec parents et photos.'),
        ('J5 — RH & accès', 'Identifier le personnel ; créer les comptes admin_ecole et enseignants.'),
        ('J6 — Biométrie & cartes', 'Compléter photos, valider biométries ; émettre les cartes (API) et les consulter sur la fiche élève.'),
        ('J7 — Pilotage', 'Former les acteurs sur leur dashboard, menus selon rôle, et exports PDF.'),
    ]
    for title, text in steps:
        p = doc.add_paragraph()
        r = p.add_run(f'{title} — ')
        set_run_font(r, size=11, bold=True, color=VERT)
        r2 = p.add_run(text)
        set_run_font(r2, size=11)

    # 10
    doc.add_heading('10. Glossaire', level=1)
    make_table(
        doc,
        ['Terme', 'Définition'],
        [
            ['PA', 'Province administrative'],
            ['PE', 'Province éducationnelle'],
            ['Antenne', 'Structure de rattachement opérationnelle sous une PE'],
            ['Administratif école', 'Compte de gestion de l’établissement (admin_ecole)'],
            ['Classe titulaire', 'Classe dont l’enseignant est responsable dans l’application'],
            ['Matricule', 'Identifiant unique de l’élève'],
            ['Biométrie', 'Dossier photo / empreinte associé à l’élève'],
            ['Carte scolaire', 'Support d’identification avec QR et validité ; consultable sur fiche élève / API'],
            ['Périmètre', 'Sous-ensemble de données visible selon le rôle'],
            ['Mon école', 'Vue dédiée de l’administratif école (hors enseignant)'],
        ],
        col_widths=[4.0, 11.5],
    )

    # 11 Historique
    doc.add_heading('11. Historique des versions', level=1)
    make_table(
        doc,
        ['Version', 'Date', 'Évolutions'],
        [
            ['1.0', '05/08/2026', 'Version initiale du workflow métier Educ_RDC'],
            [
                '1.1',
                date.today().strftime('%d/%m/%Y'),
                'Retrait du menu Cartes ; menu latéral fixe ; '
                'enseignant sans accès Mon école ; '
                'identité parents (père/mère/tuteur + photos/contacts) ; '
                'suppressions depuis détail/modales ; '
                'mise à jour navigation et RACI',
            ],
        ],
        col_widths=[2.2, 2.8, 10.5],
    )

    # Clôture
    doc.add_heading('Approbation', level=1)
    add_para(
        doc,
        'Document généré à partir du fonctionnement réel de la plateforme Educ_RDC (v1.1). '
        'Il constitue la référence métier pour la formation, l’exploitation et la recette.'
    )
    make_table(
        doc,
        ['Rôle', 'Nom', 'Date', 'Visa'],
        [
            ['Maîtrise d’ouvrage', '', '', ''],
            ['Responsable métier', '', '', ''],
            ['Responsable technique', '', '', ''],
        ],
        col_widths=[4.5, 4.5, 3.0, 3.5],
    )

    out_dir = Path(__file__).resolve().parent
    out = out_dir / 'Educ_RDC_Workflow_Metier.docx'
    try:
        doc.save(out)
    except PermissionError:
        out = out_dir / 'Educ_RDC_Workflow_Metier_v1.1.docx'
        doc.save(out)
        print('Fichier principal verrouillé (ouvert dans Word ?) — sauvegarde alternative.')
    print(f'Document généré : {out}')
    return out


if __name__ == '__main__':
    build()
