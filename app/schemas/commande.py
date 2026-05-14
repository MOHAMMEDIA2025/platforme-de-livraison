from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    produit_id: int
    quantite: int

class CommandeCreate(BaseModel):
    user_id: int
    adresse: str
    items: List[Item]