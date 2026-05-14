from sqlalchemy.orm import Session
from app.models.panier import PanierItem
from app.models.produit import Produit


def add_to_panier(db: Session, user_id: int, produit_id: int, quantite: int):
    item = db.query(PanierItem).filter(
        PanierItem.user_id == user_id,
        PanierItem.produit_id == produit_id
    ).first()

    if item:
        item.quantite += quantite
    else:
        item = PanierItem(
            user_id=user_id,
            produit_id=produit_id,
            quantite=quantite
        )
        db.add(item)

    db.commit()
    db.refresh(item)
    return item


def get_panier(db: Session, user_id: int):
    items = db.query(PanierItem).filter(PanierItem.user_id == user_id).all()

    result = []
    total = 0

    for item in items:
        produit = db.query(Produit).filter(Produit.id == item.produit_id).first()

        if produit:
            sous_total = produit.prix * item.quantite
            total += sous_total

            result.append({
                "id": item.id,
                "produit": produit.nom,
                "prix": produit.prix,
                "quantite": item.quantite,
                "sous_total": sous_total
            })

    return {"items": result, "total": total}


def update_panier_item(db: Session, item_id: int, user_id: int, quantite: int):
    item = db.query(PanierItem).filter(
        PanierItem.id == item_id,
        PanierItem.user_id == user_id
    ).first()

    if item:
        item.quantite = quantite
        db.commit()
        db.refresh(item)

    return item


def remove_from_panier(db: Session, item_id: int, user_id: int):
    item = db.query(PanierItem).filter(
        PanierItem.id == item_id,
        PanierItem.user_id == user_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    return item


def clear_panier(db: Session, user_id: int):
    db.query(PanierItem).filter(PanierItem.user_id == user_id).delete()
    db.commit()