from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    titre      = Column(String, nullable=False)
    message    = Column(String, nullable=False)
    type       = Column(String, default="info")    # success | info | warning | error
    icon       = Column(String, default="🔔")
    lien       = Column(String, nullable=True)
    est_lue    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user       = relationship("User", back_populates="notifications")