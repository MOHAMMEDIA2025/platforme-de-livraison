"""
app/schemas/commande_catalogue.py

Schémas Pydantic pour :
  - CommandeCatalogue / LigneCommandeCatalogue
  - LivraisonDetail

CORRECTIF APPLIQUÉ :
  - prix_total_livraison : Decimal → float
    Raison : SQLAlchemy retourne NUMERIC(10,2) comme objet Python Decimal.
    FastAPI sérialise Decimal en *string* JSON, ce qui fait crasher
    .toFixed() dans le frontend React (TypeError: toFixed is not a function).
    En déclarant float, FastAPI sérialise en nombre JSON, et .toFixed()
    fonctionne correctement.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES MÉTIER
# ══════════════════════════════════════════════════════════════════════════════

METHODES_PAIEMENT = [
    "Carte Mastercard",
    "Carte Visa",
    "Paiement à la livraison",
    "Virement bancaire (RIB)",
]

STATUTS_LIVRAISON = ["Livré", "En attente", "En cours", "Annulé", "Retardé"]


# ══════════════════════════════════════════════════════════════════════════════
#  LIGNES COMMANDE CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

class LigneCommandeCatalogueCreate(BaseModel):
    produit_achete_fr: str
    produit_achete_en: str
    categorie_fr: str
    categorie_en: str
    sous_categorie_fr: str
    sous_categorie_en: str
    prix_unitaire: float
    quantite: int
    prix_ligne_avant_promo: float
    prix_ligne_apres_promo: float


class LigneCommandeCatalogueOut(LigneCommandeCatalogueCreate):
    id: int
    commande_id: int

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

class CommandeCatalogueCreate(BaseModel):
    nom_client: str
    date_commande: datetime
    code_promo: Optional[str] = None
    remise_appliquee: float = 0.00
    lignes: List[LigneCommandeCatalogueCreate]


class CommandeCatalogueOut(BaseModel):
    id: int
    nom_client: str
    date_commande: datetime
    code_promo: Optional[str]
    remise_appliquee: float
    lignes: List[LigneCommandeCatalogueOut]

    class Config:
        from_attributes = True


class CommandeCatalogueListOut(BaseModel):
    """Version allégée pour les listes (sans détail des lignes)."""
    id: int
    nom_client: str
    date_commande: datetime
    code_promo: Optional[str]
    remise_appliquee: float
    nb_lignes: int
    total_avant_promo: float
    total_apres_promo: float

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  LIVRAISONS DETAIL
# ══════════════════════════════════════════════════════════════════════════════

class LivraisonDetailCreate(BaseModel):
    nom_client: str
    nom_livreur: str
    date_livraison: datetime
    produits: str
    quantite_totale: int
    # ✅ CORRECTIF : float au lieu de Decimal
    # Decimal Python est sérialisé en string JSON par FastAPI → crash toFixed()
    prix_total_livraison: float
    methode_paiement: str
    localisation_client: str
    localisation_livreur: str
    notes_client: Optional[str] = None
    statut: str = "En attente"


class LivraisonDetailUpdate(BaseModel):
    statut: Optional[str] = None
    nom_livreur: Optional[str] = None
    notes_client: Optional[str] = None
    methode_paiement: Optional[str] = None


class LivraisonDetailOut(BaseModel):
    id_livraison: int
    nom_client: str
    nom_livreur: str
    date_livraison: datetime
    produits: str
    quantite_totale: int
    # ✅ CORRECTIF : float au lieu de Decimal
    # Sans ce changement, FastAPI retourne "94.00" (string) au lieu de 94.0 (number)
    # et le frontend plante sur .toFixed() : "TypeError: toFixed is not a function"
    prix_total_livraison: float
    methode_paiement: str
    localisation_client: str
    localisation_livreur: str
    notes_client: Optional[str]
    statut: str

    class Config:
        from_attributes = True