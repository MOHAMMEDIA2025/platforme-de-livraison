# app/routes/code_promo.py
#
# ✅ CORRECTION PRINCIPALE :
# Le frontend crée les codes via /promotions (table `promotions`, modèle Promotion).
# Mais /code-promo/valider cherchait dans `codes_promo` (modèle CodePromo) → toujours "invalide".
# Fix : /code-promo/valider requête maintenant la table `promotions`.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import admin_only
from app.models.promotion import Promotion          # ✅ table correcte
from app.schemas.code_promo import ValiderPromoIn, ValiderPromoOut
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/code-promo", tags=["Codes Promo"])


# ── CLIENT : valider un code avant commande ───────────────────────────────────
@router.post("/valider", response_model=ValiderPromoOut)
def valider_code(data: ValiderPromoIn, db: Session = Depends(get_db)):
    """
    Endpoint appelé par le frontend (EtapeAvantages).
    Cherche le code dans la table `promotions` (créée par l'admin via /promotions).
    """
    promo = db.query(Promotion).filter(
        Promotion.code == data.code.strip().upper()
    ).first()

    if not promo:
        return ValiderPromoOut(valide=False, message="Code promo invalide", reduction=0.0)

    # Vérifications de validité
    if not promo.est_active:
        return ValiderPromoOut(valide=False, message="Code promo désactivé", reduction=0.0)

    if promo.est_expiree():
        return ValiderPromoOut(valide=False, message="Code promo expiré", reduction=0.0)

    if promo.usage_max is not None and promo.usage_count >= promo.usage_max:
        return ValiderPromoOut(valide=False, message="Quota d'utilisations atteint", reduction=0.0)

    montant = data.montant_commande  # résolu par le @model_validator dans ValiderPromoIn

    if montant < promo.minimum_commande:
        return ValiderPromoOut(
            valide=False,
            message=f"Montant minimum requis : {promo.minimum_commande} DH",
            reduction=0.0
        )

    # Calcul de la réduction
    if promo.type == "pourcentage":
        reduction = round(montant * promo.valeur / 100, 2)
    elif promo.type == "montant_fixe":
        reduction = round(min(promo.valeur, montant), 2)
    elif promo.type == "livraison_gratuite":
        reduction = 15.0   # frais de livraison standard
    else:
        reduction = 0.0

    return ValiderPromoOut(
        valide=True,
        message=f"Code appliqué : -{reduction} DH",
        reduction=reduction,
        type=promo.type,
        valeur=promo.valeur
    )