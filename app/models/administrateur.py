from sqlalchemy import Column, Integer, String
from app.database import Base

class Administrateur(Base):
    __tablename__ = "administrateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    email = Column(String, unique=True)
    password = Column(String)