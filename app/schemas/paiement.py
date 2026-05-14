from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class MethodeEnum(str, Enum):
    stripe   = "stripe"
    paypal   = "paypal"
    cash     = "cash"
    virement = "virement"

class PaiementCreate(BaseModel):
    commande_id : int
    methode     : MethodeEnum

class PaiementOut(BaseModel):
    id             : int
    commande_id    : int
    montant        : float
    methode        : str
    statut         : str
    transaction_id : Optional[str] = None
    created_at     : datetime

    class Config:
        from_attributes = True

class StripeSessionOut(BaseModel):
    checkout_url : str
    session_id   : str