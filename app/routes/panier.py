from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.panier import PanierItem
from app.models.produit import Produit

router = APIRouter(prefix="/panier", tags=["Panier"])


# ── Voir mon panier ───────────────────────────────────────────────────────────
@router.get("/")
def get_panier(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    items = db.query(PanierItem).filter(PanierItem.user_id == user_id).all()

    result = []
    total = 0.0

    for item in items:
        produit = db.query(Produit).filter(Produit.id == item.produit_id).first()
        if produit:
            # ✅ CORRECTION : on vérifie est_disponible_col ou stock > 0
            stock_reel = produit.stock or 0
            if stock_reel > 0:
                prix_effectif = produit.prix_promo if produit.est_promo and produit.prix_promo else produit.prix
                sous_total = prix_effectif * item.quantite
                total += sous_total
                result.append({
                    "id": item.id,
                    "produit_id": produit.id,
                    "produit": produit.nom,
                    "image_url": produit.image_url,
                    "categorie": produit.categorie,
                    "prix": prix_effectif,
                    "prix_original": produit.prix,
                    "est_promo": produit.est_promo,
                    "quantite": item.quantite,
                    "stock_max": stock_reel,
                    "sous_total": round(sous_total, 2)
                })

    return {
        "items": result,
        "total": round(total, 2),
        "nb_articles": sum(i["quantite"] for i in result)
    }


# ── Ajouter au panier ─────────────────────────────────────────────────────────
@router.post("/")
def add_to_panier(
    produit_id: int,
    quantite: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])

    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    # ✅ CORRECTION : stock est un entier, pas un booléen
    stock_reel = produit.stock if produit.stock is not None else 0

    if stock_reel <= 0:
        raise HTTPException(status_code=400, detail="Produit indisponible (stock épuisé)")

    if stock_reel < quantite:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuffisant (disponible: {stock_reel})"
        )

    item = db.query(PanierItem).filter(
        PanierItem.user_id == user_id,
        PanierItem.produit_id == produit_id
    ).first()

    if item:
        new_qty = item.quantite + quantite
        if new_qty > stock_reel:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant (max: {stock_reel})"
            )
        item.quantite = new_qty
    else:
        item = PanierItem(user_id=user_id, produit_id=produit_id, quantite=quantite)
        db.add(item)

    db.commit()
    db.refresh(item)
    return {"message": "Ajouté au panier", "item_id": item.id, "quantite": item.quantite}


# ── Modifier quantité ─────────────────────────────────────────────────────────
@router.put("/{item_id}")
def update_item(
    item_id: int,
    quantite: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    item = db.query(PanierItem).filter(
        PanierItem.id == item_id,
        PanierItem.user_id == user_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Article introuvable")

    produit = db.query(Produit).filter(Produit.id == item.produit_id).first()
    if produit:
        stock_reel = produit.stock if produit.stock is not None else 0
        if quantite > stock_reel:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant (max: {stock_reel})"
            )

    if quantite <= 0:
        db.delete(item)
        db.commit()
        return {"message": "Article supprimé"}

    item.quantite = quantite
    db.commit()
    db.refresh(item)
    return {"message": "Quantité mise à jour", "quantite": item.quantite}


# ── Supprimer un article ──────────────────────────────────────────────────────
@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    item = db.query(PanierItem).filter(
        PanierItem.id == item_id,
        PanierItem.user_id == user_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Article introuvable")

    db.delete(item)
    db.commit()
    return {"message": "Article supprimé du panier"}


# ── Vider le panier ───────────────────────────────────────────────────────────
@router.delete("/")
def clear_panier(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    db.query(PanierItem).filter(PanierItem.user_id == user_id).delete()
    db.commit()
    return {"message": "Panier vidé"}