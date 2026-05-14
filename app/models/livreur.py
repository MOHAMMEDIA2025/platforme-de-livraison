from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Livreur(Base):
    __tablename__ = "livreurs"

    id               = Column(Integer, primary_key=True)
    nom              = Column(String, nullable=False)
    telephone        = Column(String)
    statut           = Column(String, default="disponible")  # disponible | occupé | hors_ligne
    lat              = Column(Float,  nullable=True)
    lng              = Column(Float,  nullable=True)
    note_moyenne     = Column(Float,  default=5.0)
    nb_livraisons    = Column(Integer, default=0)
    vehicule         = Column(String,  default="moto")       # moto | velo | voiture
    zone             = Column(String,  nullable=True)
    is_online        = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    commandes        = relationship("Commande", back_populates="livreur")

    # ✅ CORRECTION : relation manquante — requise par Avis.back_populates="avis"
    avis             = relationship("Avis", back_populates="livreur")