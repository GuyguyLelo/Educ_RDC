"""Calculs de notes et génération PDF du bulletin officiel RDC."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from eleves.models import Eleve
from .models import (
    AnneeScolaire,
    BulletinDecision,
    Note,
    PeriodeEvaluation,
    ProgrammeClasse,
)


ZERO = Decimal('0')


def _d(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value))


def _fmt(value: Decimal | None, digits=1) -> str:
    if value is None:
        return ''
    q = Decimal('0.1') if digits == 1 else Decimal('0.01')
    return str(value.quantize(q, rounding=ROUND_HALF_UP))


def maximum_periode(programme: ProgrammeClasse, periode: PeriodeEvaluation) -> Decimal:
    return (programme.maximum_effectif * periode.facteur_maximum).quantize(Decimal('0.01'))


def calculer_ligne_matiere(
    programme: ProgrammeClasse,
    periodes: list[PeriodeEvaluation],
    notes_map: dict[int, Decimal | None],
) -> dict[str, Any]:
    """Calcule totaux semestre / annuel pour une matière (régime secondaire)."""
    by_code = {p.code: p for p in periodes}
    cells = {}
    for p in periodes:
        cells[p.code] = notes_map.get(p.id)

    def tot_semestre(codes_tj, code_exam):
        vals = []
        maxi = ZERO
        for code in codes_tj + [code_exam]:
            p = by_code.get(code)
            if not p:
                continue
            maxi += maximum_periode(programme, p)
            v = cells.get(code)
            if v is not None:
                vals.append(_d(v))
        if not vals:
            return None, maxi
        return sum(vals, ZERO), maxi

    tot1, max1 = tot_semestre(['p1', 'p2'], 'exam1')
    tot2, max2 = tot_semestre(['p3', 'p4'], 'exam2')

    # Primaire : trimestres
    if 't1' in by_code:
        vals = []
        maxi = ZERO
        for code in ('t1', 't2', 't3'):
            p = by_code.get(code)
            if not p:
                continue
            maxi += maximum_periode(programme, p)
            v = cells.get(code)
            if v is not None:
                vals.append(_d(v))
        total = sum(vals, ZERO) if vals else None
        return {
            'matiere': programme.matiere.nom,
            'maximum_base': programme.maximum_effectif,
            'notes': cells,
            'tot1': None,
            'max1': ZERO,
            'tot2': None,
            'max2': ZERO,
            'total': total,
            'max_total': maxi,
            'pourcentage': (
                (total * 100 / maxi).quantize(Decimal('0.01'))
                if total is not None and maxi > 0 else None
            ),
        }

    total = None
    max_total = max1 + max2
    if tot1 is not None or tot2 is not None:
        total = (tot1 or ZERO) + (tot2 or ZERO)

    return {
        'matiere': programme.matiere.nom,
        'maximum_base': programme.maximum_effectif,
        'notes': cells,
        'tot1': tot1,
        'max1': max1,
        'tot2': tot2,
        'max2': max2,
        'total': total,
        'max_total': max_total,
        'pourcentage': (
            (total * 100 / max_total).quantize(Decimal('0.01'))
            if total is not None and max_total > 0 else None
        ),
    }


def calculer_bulletin_eleve(eleve: Eleve, annee: AnneeScolaire) -> dict[str, Any]:
    if not eleve.classe_id:
        raise ValueError("L'élève n'est rattaché à aucune classe.")

    periodes = list(annee.periodes.all().order_by('ordre'))
    programmes = list(
        ProgrammeClasse.objects.filter(
            annee=annee, classe_id=eleve.classe_id,
        ).select_related('matiere')
    )
    # Grouper comme le bulletin officiel : par maximum croissant puis ordre
    programmes.sort(key=lambda p: (p.maximum_effectif, p.ordre, p.matiere.nom))
    notes = Note.objects.filter(
        eleve=eleve,
        programme__in=programmes,
        periode__annee=annee,
    )
    notes_by_prog: dict[int, dict[int, Decimal | None]] = {}
    for n in notes:
        notes_by_prog.setdefault(n.programme_id, {})[n.periode_id] = n.valeur

    lignes = []
    total_obtenu = ZERO
    total_max = ZERO
    has_note = False
    for prog in programmes:
        ligne = calculer_ligne_matiere(prog, periodes, notes_by_prog.get(prog.id, {}))
        lignes.append(ligne)
        if ligne['total'] is not None:
            has_note = True
            total_obtenu += ligne['total']
            total_max += ligne['max_total']
        else:
            total_max += ligne['max_total']

    pourcentage = None
    if has_note and total_max > 0:
        pourcentage = (total_obtenu * 100 / total_max).quantize(Decimal('0.01'))

    decision, _ = BulletinDecision.objects.get_or_create(eleve=eleve, annee=annee)
    classmates = Eleve.objects.filter(classe_id=eleve.classe_id, actif=True)
    effectif = classmates.count()

    return {
        'eleve': eleve,
        'annee': annee,
        'periodes': periodes,
        'lignes': lignes,
        'total_obtenu': total_obtenu if has_note else None,
        'total_max': total_max,
        'pourcentage': pourcentage,
        'decision': decision,
        'effectif': effectif,
        'ecole': eleve.ecole,
        'classe': eleve.classe,
    }


def actualiser_classement(annee: AnneeScolaire, classe_id: int) -> None:
    """Calcule place / pourcentage pour tous les élèves de la classe."""
    eleves = list(Eleve.objects.filter(classe_id=classe_id, actif=True))
    scores = []
    for el in eleves:
        data = calculer_bulletin_eleve(el, annee)
        pct = data['pourcentage']
        scores.append((el, data, pct if pct is not None else Decimal('-1')))

    scores.sort(key=lambda x: x[2], reverse=True)
    effectif = len(eleves)
    place = 0
    last_pct = None
    for idx, (el, data, pct) in enumerate(scores, start=1):
        if pct != last_pct:
            place = idx
            last_pct = pct
        decision = data['decision']
        decision.total_obtenu = data['total_obtenu']
        decision.total_max = data['total_max']
        decision.pourcentage = data['pourcentage']
        decision.place = place if pct >= 0 else None
        decision.effectif = effectif
        if decision.decision == BulletinDecision.Decision.EN_ATTENTE and pct is not None and pct >= 0:
            decision.decision = (
                BulletinDecision.Decision.PASSE if pct >= 50
                else BulletinDecision.Decision.DOUBLE
            )
        decision.save()


def generer_pdf_bulletin(eleve: Eleve, annee: AnneeScolaire) -> bytes:
    """Bulletin PDF conforme au modèle officiel IGE/EPSP RDC."""
    from .bulletin_pdf import generer_pdf_bulletin_officiel
    return generer_pdf_bulletin_officiel(eleve, annee)
