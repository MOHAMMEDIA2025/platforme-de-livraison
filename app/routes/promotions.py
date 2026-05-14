"""
app/routes/promotions.py
Gestion complète des promotions : codes promo + flash sales + bannières promo
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.database import get_db
from app.core.dependencies import admin_only, get_current_user
from app.models.promotion import Promotion
from app.models.commande import Commande
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/promotions", tags=["Promotions"])


# ─── Schemas ─────────────────────────────────────────────────────────────────
class PromotionCreate(BaseModel):
    code: str
    description: Optional[str] = None
    type: str = "pourcentage"       # "pourcentage" | "montant_fixe" | "livraison_gratuite"
    valeur: float = 10.0            # ex: 20 → 20% ou 20 DH
    minimum_commande: float = 0.0
    usage_max: Optional[int] = None
    date_fin: Optional[datetime] = None
    est_active: bool = True

class PromotionUpdate(BaseModel):
    description: Optional[str] = None
    valeur: Optional[float] = None
    minimum_commande: Optional[float] = None
    usage_max: Optional[int] = None
    date_fin: Optional[datetime] = None
    est_active: Optional[bool] = None

class CodePromoVerif(BaseModel):
    code: str
    total_panier: float


# ─── ADMIN : créer une promotion ─────────────────────────────────────────────
@router.post("/")
def create_promotion(
    data: PromotionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    existing = db.query(Promotion).filter(
        Promotion.code == data.code.upper()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce code promo existe déjà")

    promo = Promotion(
        code=data.code.upper().strip(),
        description=data.description,
        type=data.type,
        valeur=data.valeur,
        minimum_commande=data.minimum_commande,
        usage_max=data.usage_max,
        usage_count=0,
        date_fin=data.date_fin,
        est_active=data.est_active
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


# ─── ADMIN : liste toutes les promotions ─────────────────────────────────────
@router.get("/")
def list_promotions(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    promos = db.query(Promotion).order_by(Promotion.created_at.desc()).all()
    result = []
    for p in promos:
        # Calcul du CA généré par ce code
        ca = db.query(func.sum(Commande.reduction)).filter(
            Commande.code_promo == p.code
        ).scalar() or 0

        result.append({
            "id": p.id,
            "code": p.code,
            "description": p.description,
            "type": p.type,
            "valeur": p.valeur,
            "minimum_commande": p.minimum_commande,
            "usage_max": p.usage_max,
            "usage_count": p.usage_count,
            "date_fin": p.date_fin.isoformat() if p.date_fin else None,
            "est_active": p.est_active,
            "est_expiree": p.est_expiree(),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "economie_totale": round(float(ca), 2),
        })
    return result


# ─── ADMIN : modifier une promotion ─────────────────────────────────────────
@router.put("/{promo_id}")
def update_promotion(
    promo_id: int,
    data: PromotionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion introuvable")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(promo, field, value)

    db.commit()
    db.refresh(promo)
    return promo


# ─── ADMIN : activer / désactiver ────────────────────────────────────────────
@router.patch("/{promo_id}/toggle")
def toggle_promotion(
    promo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion introuvable")

    promo.est_active = not promo.est_active
    db.commit()
    return {"message": f"Promotion {'activée' if promo.est_active else 'désactivée'}", "est_active": promo.est_active}


# ─── ADMIN : supprimer ───────────────────────────────────────────────────────
@router.delete("/{promo_id}")
def delete_promotion(
    promo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion introuvable")
    db.delete(promo)
    db.commit()
    return {"message": "Promotion supprimée"}


# ─── CLIENT / PUBLIC : vérifier un code promo ───────────────────────────────
@router.post("/verifier")
def verifier_code_promo(
    data: CodePromoVerif,
    db: Session = Depends(get_db)
):
    promo = db.query(Promotion).filter(
        Promotion.code == data.code.upper().strip()
    ).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Code promo invalide")
    if not promo.est_active:
        raise HTTPException(status_code=400, detail="Ce code promo est inactif")
    if promo.est_expiree():
        raise HTTPException(status_code=400, detail="Ce code promo est expiré")
    if promo.usage_max and promo.usage_count >= promo.usage_max:
        raise HTTPException(status_code=400, detail="Ce code promo a atteint sa limite d'utilisation")
    if data.total_panier < promo.minimum_commande:
        raise HTTPException(
            status_code=400,
            detail=f"Commande minimale requise : {promo.minimum_commande} DH"
        )

    # Calculer la réduction
    if promo.type == "pourcentage":
        reduction = round(data.total_panier * promo.valeur / 100, 2)
    elif promo.type == "montant_fixe":
        reduction = min(promo.valeur, data.total_panier)
    elif promo.type == "livraison_gratuite":
        reduction = 15.0  # frais de livraison standard
    else:
        reduction = 0.0

    return {
        "valide": True,
        "code": promo.code,
        "type": promo.type,
        "valeur": promo.valeur,
        "reduction": reduction,
        "description": promo.description or f"Réduction de {promo.valeur}{'%' if promo.type == 'pourcentage' else ' DH'}",
    }