from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.produit import Produit
from app.models.panier import PanierItem


def create_commande_from_panier(db: Session, user_id: int, adresse: str):
    panier_items = db.query(PanierItem).filter(PanierItem.user_id == user_id).all()

    if not panier_items:
        raise HTTPException(status_code=400, detail="Panier vide")

    commande = Commande(user_id=user_id, adresse=adresse)
    db.add(commande)
    db.commit()
    db.refresh(commande)

    total = 0

    for item in panier_items:
        produit = db.query(Produit).filter(Produit.id == item.produit_id).first()

        # ✅ CORRECTION IMPORTANTE
        if not produit:
            raise HTTPException(
                status_code=400,
                detail=f"Produit ID {item.produit_id} introuvable"
            )

        if produit.stock is None:
            raise HTTPException(
                status_code=400,
                detail=f"Stock invalide pour produit {produit.nom}"
            )

        if produit.stock < item.quantite:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour {produit.nom}"
            )

        produit.stock -= item.quantite

        ligne = LigneCommande(
            commande_id=commande.id,
            produit_id=produit.id,
            quantite=item.quantite
        )

        db.add(ligne)
        total += produit.prix * item.quantite

    commande.total = total

    # vider panier
    db.query(PanierItem).filter(PanierItem.user_id == user_id).delete()

    db.commit()
    db.refresh(commande)

    return commande