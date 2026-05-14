from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class PanierItem(Base):
    __tablename__ = "panier_items"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    produit_id = Column(Integer, ForeignKey("produits.id"))
    quantite   = Column(Integer, default=1)