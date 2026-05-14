from pydantic import BaseModel

class LivreurCreate(BaseModel):
    nom: str
    telephone: str

class UpdateStatut(BaseModel):
    statut: str