from sqlalchemy.orm import Session
from app.models.produit import Produit

def create_produit(db: Session, data):
    produit = Produit(**data.dict())
    db.add(produit)
    db.commit()
    db.refresh(produit)
    return produit

def get_produits(db: Session):
    return db.query(Produit).all()

def get_produit(db: Session, produit_id: int):
    return db.query(Produit).filter(Produit.id == produit_id).first()

def update_produit(db: Session, produit_id: int, data):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if produit:
        produit.nom = data.nom
        produit.description = data.description
        produit.prix = data.prix
        produit.stock = data.stock
        db.commit()
        db.refresh(produit)
    return produit

def delete_produit(db: Session, produit_id: int):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if produit:
        db.delete(produit)
        db.commit()
    return produit