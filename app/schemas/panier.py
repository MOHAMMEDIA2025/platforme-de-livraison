from pydantic import BaseModel

class PanierItemCreate(BaseModel):
    produit_id: int
    quantite: int

class PanierItemUpdate(BaseModel):
    quantite: int