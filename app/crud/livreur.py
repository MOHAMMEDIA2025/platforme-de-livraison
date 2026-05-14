from sqlalchemy.orm import Session
from app.models.livreur import Livreur

def create_livreur(db: Session, data):
    livreur = Livreur(**data.dict(), statut="disponible")
    db.add(livreur)
    db.commit()
    db.refresh(livreur)
    return livreur

def get_livreurs(db: Session):
    return db.query(Livreur).all()