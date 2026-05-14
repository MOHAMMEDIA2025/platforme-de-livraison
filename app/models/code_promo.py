from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.database import Base


class CodePromo(Base):
    __tablename__ = "codes_promo"

    id                   = Column(Integer, primary_key=True)
    code                 = Column(String, unique=True, nullable=False)           # ex: "BIENVENUE20"
    description          = Column(String, nullable=True)
    type                 = Column(String, default="pourcentage")                 # pourcentage | fixe
    valeur               = Column(Float, nullable=False)                         # 20 = 20% ou 20 DH
    min_commande         = Column(Float, default=0.0)                            # montant minimum requis
    nb_utilisations_max  = Column(Integer, default=100)                          # -1 = illimité
    nb_utilisations      = Column(Integer, default=0)
    est_actif            = Column(Boolean, default=True)
    date_expiration      = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    def est_valide(self, montant_commande: float) -> tuple[bool, str]:
        """Retourne (valide, message_erreur)."""
        if not self.est_actif:
            return False, "Code promo désactivé"
        if self.date_expiration and datetime.utcnow() > self.date_expiration:
            return False, "Code promo expiré"
        if self.nb_utilisations_max != -1 and self.nb_utilisations >= self.nb_utilisations_max:
            return False, "Quota d'utilisations atteint"
        if montant_commande < self.min_commande:
            return False, f"Montant minimum requis : {self.min_commande} DH"
        return True, ""

    def calculer_reduction(self, montant: float) -> float:
        """Retourne le montant de la réduction."""
        if self.type == "pourcentage":
            return round(montant * self.valeur / 100, 2)
        return round(min(self.valeur, montant), 2)   # ne peut pas dépasser le total
