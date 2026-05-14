# app/schemas/code_promo.py

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime


class CodePromoCreate(BaseModel):
    code: str
    description: Optional[str] = None
    type: str = "pourcentage"
    valeur: float
    min_commande: float = 0.0
    nb_utilisations_max: int = 100
    date_expiration: Optional[datetime] = None

    @field_validator("code", mode="before")
    @classmethod
    def code_uppercase(cls, v):
        return v.strip().upper()

    @field_validator("type", mode="before")
    @classmethod
    def type_valide(cls, v):
        if v not in ("pourcentage", "fixe"):
            raise ValueError("type doit être 'pourcentage' ou 'fixe'")
        return v

    @field_validator("valeur", mode="before")
    @classmethod
    def valeur_positive(cls, v):
        if v <= 0:
            raise ValueError("La valeur doit être positive")
        return v


class CodePromoUpdate(BaseModel):
    description: Optional[str] = None
    est_actif: Optional[bool] = None
    nb_utilisations_max: Optional[int] = None
    date_expiration: Optional[datetime] = None


class CodePromoOut(BaseModel):
    id: int
    code: str
    description: Optional[str]
    type: str
    valeur: float
    min_commande: float
    nb_utilisations_max: int
    nb_utilisations: int
    est_actif: bool
    date_expiration: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ✅ CORRECTION BUG :
# Le frontend envoie { code: "...", total_commande: 150.0 }
# On accepte les deux noms via @model_validator.
# Sans ça, montant_commande reçoit toujours 0.0 et
# le code échoue le test "min_commande" même pour 0 DH minimum.
class ValiderPromoIn(BaseModel):
    code: str
    # Accepte "montant_commande" (appel API direct) ou "total_commande" (frontend React)
    montant_commande: Optional[float] = None
    total_commande:   Optional[float] = None

    @model_validator(mode="after")
    def resoudre_montant(self):
        """
        Priorité : total_commande (frontend) > montant_commande (API directe) > 0.0
        """
        if self.total_commande is not None:
            self.montant_commande = self.total_commande
        elif self.montant_commande is None:
            self.montant_commande = 0.0
        return self


class ValiderPromoOut(BaseModel):
    valide: bool
    message: str
    reduction: float = 0.0
    type: Optional[str] = None
    valeur: Optional[float] = None