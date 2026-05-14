# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterSchema(BaseModel):
    nom: str
    email: EmailStr
    password: str
    telephone: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    nom: Optional[str] = None
