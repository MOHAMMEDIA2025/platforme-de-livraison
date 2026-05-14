"""
app/models/promotion.py
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id               = Column(Integer, primary_key=True)
    code             = Column(String, unique=True, nullable=False, index=True)
    description      = Column(String, nullable=True)
    type             = Column(String, default="pourcentage")  # pourcentage | montant_fixe | livraison_gratuite
    valeur           = Column(Float, default=0.0)
    minimum_commande = Column(Float, default=0.0)
    usage_max        = Column(Integer, nullable=True)   # None = illimité
    usage_count      = Column(Integer, default=0)
    date_fin         = Column(DateTime, nullable=True)  # None = pas d'expiration
    est_active       = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    def est_expiree(self) -> bool:
        if self.date_fin is None:
            return False
        return datetime.utcnow() > self.date_fin