"""Services élèves — QR code unique."""
from __future__ import annotations

import io
import uuid

import qrcode
from django.core.files.base import ContentFile


def contenu_qr_eleve(eleve) -> str:
    """Charge utile unique et stable pour le QR de l'élève."""
    return (
        f'EDUC_RDC|ELEVE|{eleve.code_unique}|{eleve.matricule}|{eleve.pk}'
    )


def generer_qr_eleve(eleve, *, force: bool = False) -> bool:
    """
    Génère (ou régénère) l'image QR de l'élève.
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
