# app/schemas/schemas.py — VERSION CORRIGÉE
from pydantic import BaseModel
from typing import List, Optional


# ── Commande ──────────────────────────────────────────────────────────────────

class Item(BaseModel):
    produit_id: int
    quantite: int


class CommandeCreate(BaseModel):
    adresse: str
    note_client: Optional[str] = None
    # ✅ CORRECTION : code_promo doit être présent ici pour que la route /from-panier
    # puisse lire le champ code_promo envoyé depuis le frontend
    code_promo: Optional[str] = None
    # ✅ CORRECTION BUG #1 : methode_paiement manquait → fallback toujours "Paiement à la livraison"
    # Valeurs acceptées côté frontend : "stripe" | "card" | "visa" | "mastercard" | "cash" | "virement"
    methode_paiement: Optional[str] = "cash"


class CommandeOut(BaseModel):
    id: int
    total: float
    statut: str
    adresse: str
    frais_livraison: float
    reduction: float
    is_rated: bool

    class Config:
        from_attributes = True


# ── Livreur ───────────────────────────────────────────────────────────────────

class LivreurCreate(BaseModel):
    nom: str
    telephone: str
    vehicule: Optional[str] = "moto"
    zone: Optional[str] = None


class UpdateStatut(BaseModel):
    statut: str


class LivreurOut(BaseModel):
    id: int
    nom: str
    telephone: str
    statut: str
    note_moyenne: float
    nb_livraisons: int
    vehicule: str
    is_online: bool

    class Config:
        from_attributes = True