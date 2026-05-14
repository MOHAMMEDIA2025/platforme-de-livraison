from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    email       = Column(String, unique=True, index=True, nullable=False)
    password    = Column(String, nullable=False)
    role        = Column(String, default="client")   # client | livreur | admin
    nom         = Column(String, nullable=True)
    telephone   = Column(String, nullable=True)
    avatar      = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    commandes     = relationship("Commande",     back_populates="client")
    avis          = relationship("Avis",         back_populates="client")
    notifications = relationship("Notification", back_populates="user")
    paiements = relationship("Paiement", back_populates="user")