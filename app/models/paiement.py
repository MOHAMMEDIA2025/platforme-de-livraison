from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class StatutPaiement(str, enum.Enum):
    en_attente = "en_attente"
    complete   = "complete"
    echoue     = "echoue"
    rembourse  = "rembourse"

class MethodePaiement(str, enum.Enum):
    stripe   = "stripe"
    paypal   = "paypal"
    cash     = "cash"
    virement = "virement"

class Paiement(Base):
    __tablename__ = "paiements"

    id             = Column(Integer, primary_key=True, index=True)
    commande_id    = Column(Integer, ForeignKey("commandes.id"), nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    montant        = Column(Float, nullable=False)
    methode        = Column(Enum(MethodePaiement), nullable=False)
    statut         = Column(Enum(StatutPaiement), default=StatutPaiement.en_attente)
    transaction_id = Column(String, nullable=True)  # ID Stripe/PayPal
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    commande = relationship("Commande", back_populates="paiement")
    user     = relationship("User",     back_populates="paiements")