# app/schemas/chat_history.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatHistoryOut(BaseModel):
    id            : int
    user_id       : Optional[int]
    session_id    : Optional[str]
    role          : str             # "user" | "bot"
    type_message  : str             # "text" | "voice"
    content       : str
    transcription : Optional[str]
    created_at    : Optional[datetime]

    class Config:
        from_attributes = True


class ChatHistoryList(BaseModel):
    items : List[ChatHistoryOut]