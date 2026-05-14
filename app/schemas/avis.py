from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AvisCreate(BaseModel):
    commande_id: int
    produit_id: Optional[int] = None
    livreur_id: Optional[int] = None
    note_produit: Optional[float] = Field(None, ge=1, le=5)
    note_livreur: Optional[float] = Field(None, ge=1, le=5)
    commentaire: Optional[str] = None

class AvisOut(BaseModel):
    id: int
    commande_id: int
    note_produit: Optional[float]
    note_livreur: Optional[float]
    commentaire: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
