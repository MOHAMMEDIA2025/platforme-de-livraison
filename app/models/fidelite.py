from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class PointFidelite(Base):
    __tablename__ = "points_fidelite"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    points      = Column(Integer, default=0)           # total accumulé
    niveau      = Column(String, default="Bronze")     # Bronze | Argent | Or | Platine
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransactionPoints(Base):
    __tablename__ = "transactions_points"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    commande_id = Column(Integer, ForeignKey("commandes.id"), nullable=True)
    delta       = Column(Integer, nullable=False)        # +100 ou -50
    type        = Column(String, nullable=False)         # gain | depense | bonus
    description = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)