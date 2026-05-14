# app/models/chat_history.py
# Modèle pour stocker l'historique des conversations chatbot client

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id   = Column(String(100), nullable=True, index=True)
    role         = Column(String(10), nullable=False)          # "user" | "bot"
    type_message = Column(String(10), default="text")          # "text" | "voice"
    content      = Column(Text, nullable=False)
    reponse      = Column(Text, nullable=True)
    transcription = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)
