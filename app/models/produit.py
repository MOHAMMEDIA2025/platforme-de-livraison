from sqlalchemy import Column, Integer, String, Float, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base


class Produit(Base):
    __tablename__ = "produits"

    id                  = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nom                 = Column(String, nullable=True)
    nom_eng             = Column(String, nullable=True)
    quantite            = Column(Integer, nullable=True, default=0)
    prix                = Column(Float, nullable=True)
    categorie           = Column(String, nullable=True, default="Général")
    categorie_eng       = Column(String, nullable=True)
    category_plus       = Column(String, nullable=True)
    category_plus_eng   = Column(String, nullable=True)
    date_ajout          = Column(Date, nullable=True)
    promotion           = Column(Float, nullable=True)
    description         = Column(String, nullable=True)
    description_eng     = Column(String, nullable=True)
    caracteristique     = Column(String, nullable=True)
    caracteristique_eng = Column(String, nullable=True)
    stock               = Column(Integer, nullable=True, default=0)
    est_disponible      = Column(Boolean, nullable=True, default=True)
    note_moyenne        = Column(Float, nullable=True, default=0.0)
    nb_avis             = Column(Integer, nullable=True, default=0)
    image_url           = Column(String, nullable=True)
    prix_promo          = Column(Float, nullable=True)
    est_promo           = Column(Boolean, nullable=True, default=False)
    image_folder        = Column(String(200), nullable=True)

    avis = relationship("Avis", back_populates="produit")
