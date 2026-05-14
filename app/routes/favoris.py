from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.favori import Favori
from app.models.produit import Produit

router = APIRouter(prefix="/favoris", tags=["Favoris"])


@router.get("/")
def mes_favoris(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    favoris = db.query(Favori).filter(Favori.user_id == user_id).all()

    result = []
    for f in favoris:
        produit = db.query(Produit).filter(Produit.id == f.produit_id).first()
        if produit:
            result.append({
                "favori_id": f.id,
                "produit_id": produit.id,
                "nom": produit.nom,
                "prix": produit.prix,
                "prix_promo": produit.prix_promo,
                "est_promo": produit.est_promo,
                "categorie": produit.categorie,
                "image_url": f"/img/{produit.image_folder}/1" if produit.image_folder else produit.image_url,
                "note_moyenne": produit.note_moyenne,
                "stock": produit.stock,
                "est_disponible": produit.est_disponible,
                "added_at": f.created_at.isoformat()
            })
    return result


@router.post("/{produit_id}")
def ajouter_favori(
    produit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])

    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    existant = db.query(Favori).filter(
        Favori.user_id == user_id,
        Favori.produit_id == produit_id
    ).first()

    if existant:
        return {"message": "Déjà dans vos favoris", "favori_id": existant.id}

    favori = Favori(user_id=user_id, produit_id=produit_id)
    db.add(favori)
    db.commit()
    db.refresh(favori)
    return {"message": "Ajouté aux favoris ❤️", "favori_id": favori.id}


@router.delete("/{produit_id}")
def supprimer_favori(
    produit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    favori = db.query(Favori).filter(
        Favori.user_id == user_id,
        Favori.produit_id == produit_id
    ).first()

    if favori:
        db.delete(favori)
        db.commit()
    return {"message": "Retiré des favoris"}


@router.get("/check/{produit_id}")
def is_favori(
    produit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    existant = db.query(Favori).filter(
        Favori.user_id == user_id,
        Favori.produit_id == produit_id
    ).first()
    return {"est_favori": existant is not None}