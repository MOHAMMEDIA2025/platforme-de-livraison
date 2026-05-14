from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id            = Column(Integer, primary_key=True)
    commande_id   = Column(Integer, ForeignKey("commandes.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite      = Column(Integer, nullable=False)
    prix_unitaire = Column(Float, nullable=True)
    nom_produit   = Column(String, nullable=True)

    commande = relationship("Commande", back_populates="lignes")