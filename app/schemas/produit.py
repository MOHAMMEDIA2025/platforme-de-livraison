"""
app/schemas/produit.py — VERSION AVEC GALERIE img_yanda
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date


class ProduitCreate(BaseModel):
    nom: str
    nom_eng: Optional[str] = None
    prix: float
    quantite: Optional[int] = 0
    categorie: Optional[str] = "Général"
    categorie_eng: Optional[str] = None
    category_plus: Optional[str] = None
    category_plus_eng: Optional[str] = None
    promotion: Optional[float] = None
    stock: Optional[int] = 0
    description: Optional[str] = None
    description_eng: Optional[str] = None
    caracteristique: Optional[str] = None
    caracteristique_eng: Optional[str] = None
    date_ajout: Optional[date] = None

    # Images
    image_url: Optional[str] = None
    est_promo: Optional[bool] = False
    prix_promo: Optional[float] = None

    # ✅ NOUVEAU : dossier galerie img_yanda
    image_folder: Optional[str] = None


class ProduitUpdate(BaseModel):
    nom: Optional[str] = None
    nom_eng: Optional[str] = None
    prix: Optional[float] = None
    quantite: Optional[int] = None
    categorie: Optional[str] = None
    categorie_eng: Optional[str] = None
    category_plus: Optional[str] = None
    category_plus_eng: Optional[str] = None
    promotion: Optional[float] = None
    stock: Optional[int] = None
    description: Optional[str] = None
    description_eng: Optional[str] = None
    caracteristique: Optional[str] = None
    caracteristique_eng: Optional[str] = None

    # Images
    image_url: Optional[str] = None
    est_promo: Optional[bool] = None
    prix_promo: Optional[float] = None

    # ✅ NOUVEAU : dossier galerie img_yanda
    image_folder: Optional[str] = None


class ProduitOut(BaseModel):
    id: int
    nom: Optional[str] = ""
    nom_eng: Optional[str] = None
    prix: Optional[float] = 0.0
    quantite: Optional[int] = 0
    categorie: Optional[str] = "Général"
    categorie_eng: Optional[str] = None
    category_plus: Optional[str] = None
    category_plus_eng: Optional[str] = None
    promotion: Optional[float] = None
    stock: Optional[int] = 0
    description: Optional[str] = ""
    description_eng: Optional[str] = None
    caracteristique: Optional[str] = None
    caracteristique_eng: Optional[str] = None
    date_ajout: Optional[date] = None

    # Champs calculés
    est_disponible: Optional[bool] = True
    est_promo: Optional[bool] = False
    prix_promo: Optional[float] = None
    note_moyenne: Optional[float] = 0.0
    nb_avis: Optional[int] = 0
    image_url: Optional[str] = None

    # ✅ NOUVEAU : galerie complète
    image_folder: Optional[str] = None
    image_urls: Optional[List[str]] = []

    @field_validator("nom", mode="before")
    @classmethod
    def nom_not_null(cls, v):
        return v if v is not None else ""

    @field_validator("prix", mode="before")
    @classmethod
    def prix_not_null(cls, v):
        return v if v is not None else 0.0

    @field_validator("categorie", mode="before")
    @classmethod
    def categorie_not_null(cls, v):
        return v if v is not None else "Général"

    @field_validator("stock", mode="before")
    @classmethod
    def stock_not_null(cls, v):
        return v if v is not None else 0

    class Config:
        from_attributes = True