"""Services élèves — identification & QR code unique."""
from __future__ import annotations

import io
import re
import uuid

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

# Format officiel : AAAA-0001 (année + numéro d'ordre)
MATRICULE_RE = re.compile(r'^(\d{4})-(\d+)$')


def annee_pour_matricule() -> int:
    """Année utilisée dans le matricule (fin d'année scolaire active, sinon année civile)."""
    try:
        from evaluations.models import AnneeScolaire
        annee = AnneeScolaire.get_active()
    except Exception:
        annee = None
    if annee:
        if getattr(annee, 'date_fin', None):
            return annee.date_fin.year
        m = re.search(r'(\d{4})\s*$', (annee.libelle or '').strip())
        if m:
            return int(m.group(1))
    return timezone.localdate().year


def ordre_depuis_matricule(matricule: str | None) -> str | None:
    """Extrait le numéro d'ordre du matricule (ex. 2026-0001 → 0001)."""
    if not matricule:
        return None
    s = str(matricule).strip()
    m = MATRICULE_RE.match(s)
    if m:
        return m.group(2)
    m = re.search(r'(\d+)\s*$', s)
    return m.group(1) if m else None


def composer_matricule(annee: int, ordre: int) -> str:
    return f'{int(annee)}-{int(ordre):04d}'


def generer_prochain_matricule() -> str:
    """Prochain matricule libre au format AAAA-0001 (séquence nationale par année)."""
    from .models import Eleve

    annee = annee_pour_matricule()
    prefix = f'{annee}-'
    with transaction.atomic():
        mats = (
            Eleve.objects.select_for_update()
            .filter(matricule__startswith=prefix)
            .values_list('matricule', flat=True)
        )
        max_ordre = 0
        for mat in mats:
            m = MATRICULE_RE.match(mat or '')
            if m and int(m.group(1)) == annee:
                max_ordre = max(max_ordre, int(m.group(2)))
        return composer_matricule(annee, max_ordre + 1)


def composer_numero_identification(code_ecole: str | None, matricule: str | None) -> str | None:
    """Numéro Identification = code école + numéro d'ordre du matricule."""
    code = (code_ecole or '').strip()
    ordre = ordre_depuis_matricule(matricule)
    if not code or not ordre:
        return None
    return f'{code}-{ordre}'


def contenu_qr_eleve(eleve) -> str:
    """Charge utile unique et stable pour le QR de l'élève."""
    return (
        f'EDUC_RDC|ELEVE|{eleve.code_unique}|{eleve.matricule}|{eleve.pk}'
    )


def generer_qr_eleve(eleve, *, force: bool = False) -> bool:
    """
    Génère l'image QR de l'élève (une seule fois).
    force=True réservé aux migrations / maintenance — le QR métier est immuable.
    Retourne True si le fichier a été (re)créé.
    """
    if not eleve.pk or not eleve.code_unique:
        return False
    if eleve.qr_code and not force:
        return False

    img = qrcode.make(contenu_qr_eleve(eleve), border=2)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    nom = f'qr_eleve_{eleve.code_unique}.png'
    if eleve.qr_code:
        eleve.qr_code.delete(save=False)
    eleve.qr_code.save(nom, ContentFile(buffer.read()), save=False)
    eleve.save(update_fields=['qr_code'])
    return True


def assurer_qr_eleve(eleve):
    """Garantit code_unique + image QR présents."""
    if not eleve.code_unique:
        eleve.code_unique = f'ELV-{uuid.uuid4().hex[:16].upper()}'
        eleve.save(update_fields=['code_unique'])
    if not eleve.qr_code:
        generer_qr_eleve(eleve)
    return eleve
