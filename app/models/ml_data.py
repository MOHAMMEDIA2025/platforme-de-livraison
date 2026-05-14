from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SessionAchat(Base):
    """Enregistre chaque session d'achat client par catégorie."""
    __tablename__ = "sessions_achat"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    client_nom        = Column(String(100), nullable=False)
    categorie_fr      = Column(String(100), nullable=False)
    sous_categorie_fr = Column(String(100), nullable=True)
    categorie_en      = Column(String(100), nullable=False, default="")
    sous_categorie_en = Column(String(100), nullable=True)
    nb_achats         = Column(Integer, nullable=False, default=0)
    montant_total     = Column(Numeric(12, 2), nullable=False, default=0)
    temps_secondes    = Column(Integer, nullable=False, default=0)
    cree_le           = Column(DateTime, server_default=func.now())


class ProfilClient(Base):
    """Profil agrégé de chaque client pour les modèles ML."""
    __tablename__ = "profil_client"

    id                        = Column(Integer, primary_key=True, autoincrement=True)
    client_id                 = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    nb_commandes              = Column(Integer, nullable=False, default=0)
    montant_total             = Column(Numeric(12, 2), nullable=False, default=0)
    nb_produits               = Column(Integer, nullable=False, default=0)
    jours_depuis_derniere     = Column(Integer, nullable=True)
    categorie_dominante_fr    = Column(String(100), nullable=True)
    categorie_dominante_en    = Column(String(100), nullable=True)
    scat_dominante_fr         = Column(String(100), nullable=True)
    scat_dominante_en         = Column(String(100), nullable=True)
    derniere_livraison_statut = Column(String(50), nullable=True)
    methode_paiement          = Column(String(50), nullable=True)
    mis_a_jour_le             = Column(DateTime, server_default=func.now(), onupdate=func.now())
