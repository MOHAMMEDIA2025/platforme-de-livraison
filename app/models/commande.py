from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Commande(Base):
    __tablename__ = "commandes"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    livreur_id      = Column(Integer, ForeignKey("livreurs.id"), nullable=True)
    total           = Column(Float, default=0.0)
    statut          = Column(String, default="pending")
    # pending | en_preparation | en_route | livre | annule
    statut_paiement = Column(String, default="en_attente")
    # en_attente | payee | cash_en_attente | virement_en_attente
    adresse         = Column(String, nullable=False)
    note_client     = Column(String, nullable=True)
    code_promo      = Column(String, nullable=True)
    reduction       = Column(Float, default=0.0)
    frais_livraison = Column(Float, default=15.0)
    is_rated        = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    note_livreur    = Column(Float, nullable=True)
    commentaire     = Column(String, nullable=True)

    paiement = relationship("Paiement", back_populates="commande", uselist=False)
    client   = relationship("User",    back_populates="commandes")
    livreur  = relationship("Livreur", back_populates="commandes")
    lignes   = relationship("LigneCommande", back_populates="commande")
    avis     = relationship("Avis",    back_populates="commande", uselist=False)