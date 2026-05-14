"""
app/models/livraison_detail.py

Modèle pour la table `livraisons_detail` (données de livraison enrichies).

Cette table est DISTINCTE de la table `commandes` existante.
Elle stocke des informations résumées sur chaque livraison avec livreur,
localisation, méthode de paiement et statut.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from app.database import Base


class LivraisonDetail(Base):
    __tablename__ = "livraisons_detail"

    id_livraison            = Column(Integer, primary_key=True, index=True)

    # Personnes
    nom_client              = Column(String(100), nullable=False)
    nom_livreur             = Column(String(100), nullable=False)

    # Temps
    date_livraison          = Column(DateTime, nullable=False)

    # Produits (résumé du panier livré)
    produits                = Column(Text, nullable=False)   # "Produit A (x2), Produit B (x1)"
    quantite_totale         = Column(Integer, nullable=False)

    # Prix
    prix_total_livraison    = Column(Numeric(10, 2), nullable=False)

    # Paiement
    # valeurs possibles : 'Carte Mastercard', 'Carte Visa',
    #                     'Paiement à la livraison', 'Virement bancaire (RIB)'
    methode_paiement        = Column(String(60), nullable=False)

    # Localisations
    localisation_client     = Column(String(200), nullable=False)   # adresse de destination
    localisation_livreur    = Column(String(200), nullable=False)   # point de départ du livreur

    # Extra
    notes_client            = Column(Text, nullable=True, default=None)

    # valeurs possibles : 'Livré', 'En attente', 'En cours', 'Annulé', 'Retardé'
    statut                  = Column(String(30), nullable=False, default="En attente")