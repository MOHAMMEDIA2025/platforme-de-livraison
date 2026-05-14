"""
app/models/commande_catalogue.py

Modèles pour les deux nouvelles tables du catalogue de commandes :
  - CommandeCatalogue      → table `commandes_catalogue`
  - LigneCommandeCatalogue → table `commande_catalogue_lignes`

Ces tables sont DISTINCTES de la table `commandes` (flux de livraison).
Elles servent à stocker les données analytiques / historiques importées.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class CommandeCatalogue(Base):
    __tablename__ = "commandes_catalogue"

    id                  = Column(Integer, primary_key=True, index=True)
    nom_client          = Column(String(100), nullable=False)
    date_commande       = Column(DateTime, nullable=False)
    code_promo          = Column(String(30), nullable=True, default=None)
    remise_appliquee    = Column(Numeric(5, 2), nullable=False, default=0.00)

    # relation 1 → N vers les lignes
    lignes = relationship(
        "LigneCommandeCatalogue",
        back_populates="commande",
        cascade="all, delete-orphan"
    )


class LigneCommandeCatalogue(Base):
    __tablename__ = "commande_catalogue_lignes"

    id                      = Column(Integer, primary_key=True, index=True)
    commande_id             = Column(
        Integer,
        ForeignKey("commandes_catalogue.id", ondelete="CASCADE"),
        nullable=False
    )

    # Produit (bilingue)
    produit_achete_fr       = Column(String(150), nullable=False)
    produit_achete_en       = Column(String(150), nullable=False)

    # Catégories (bilingue)
    categorie_fr            = Column(String(60), nullable=False)
    categorie_en            = Column(String(60), nullable=False)
    sous_categorie_fr       = Column(String(60), nullable=False)
    sous_categorie_en       = Column(String(60), nullable=False)

    # Prix & quantité
    prix_unitaire           = Column(Numeric(10, 2), nullable=False)
    quantite                = Column(Integer, nullable=False, default=1)
    prix_ligne_avant_promo  = Column(Numeric(10, 2), nullable=False)
    prix_ligne_apres_promo  = Column(Numeric(10, 2), nullable=False)

    # relation inverse
    commande = relationship("CommandeCatalogue", back_populates="lignes")