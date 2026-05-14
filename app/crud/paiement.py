from sqlalchemy.orm import Session
from app.models.paiement import Paiement, StatutPaiement

def get_paiement_by_commande(db: Session, commande_id: int):
    return db.query(Paiement).filter(Paiement.commande_id == commande_id).first()

def update_statut_paiement(db: Session, paiement_id: int, statut: StatutPaiement):
    p = db.query(Paiement).filter(Paiement.id == paiement_id).first()
    if p:
        p.statut = statut
        db.commit()
        db.refresh(p)
    return p