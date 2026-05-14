from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MessageSupport(Base):
    __tablename__ = "messages_support"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    contenu     = Column(String, nullable=False)
    est_admin   = Column(Boolean, default=False)   # True = message vient de l'admin
    est_lu      = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)