# app/models/avis.py — VERSION CORRIGÉE
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Avis(Base):
    __tablename__ = "avis"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"),           nullable=False)
    commande_id  = Column(Integer, ForeignKey("commandes.id"),       nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=True)
    livreur_id   = Column(Integer, ForeignKey("livreurs.id"),        nullable=True)

    note_produit = Column(Float,   nullable=True)
    note_livreur = Column(Float,   nullable=True)
    commentaire  = Column(String,  nullable=True)
    est_valide   = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    client   = relationship("User",     back_populates="avis")
    commande = relationship("Commande", back_populates="avis")
    produit  = relationship("Produit",  back_populates="avis")
    # ✅ CORRECTION : ajout de la relation livreur (manquait back_populates)
    livreur  = relationship("Livreur",  back_populates="avis")