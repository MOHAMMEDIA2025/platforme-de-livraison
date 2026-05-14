"""
app/routes/fidelite.py
Programme de fidélité : points, niveaux, transactions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_user, admin_only
from app.models.fidelite import PointFidelite, TransactionPoints
from app.models.commande import Commande
from app.models.user import User

router = APIRouter(prefix="/fidelite", tags=["Fidélité"])

# Règles de niveau
NIVEAUX = [
    {"nom": "Bronze",  "min": 0,    "couleur": "#cd7f32", "emoji": "🥉", "avantages": "5% de réduction sur toutes vos commandes"},
    {"nom": "Argent",  "min": 500,  "couleur": "#c0c0c0", "emoji": "🥈", "avantages": "10% de réduction + livraison offerte dès 100 DH"},
    {"nom": "Or",      "min": 1500, "couleur": "#ffd700", "emoji": "🥇", "avantages": "15% de réduction + livraison toujours offerte"},
    {"nom": "Platine", "min": 5000, "couleur": "#e5e4e2", "emoji": "💎", "avantages": "20% de réduction + service prioritaire + cadeaux exclusifs"},
]

POINTS_PAR_DH = 1  # 1 point par DH dépensé


def _get_niveau(points: int) -> dict:
    niveau_actuel = NIVEAUX[0]
    for n in NIVEAUX:
        if points >= n["min"]:
            niveau_actuel = n
    return niveau_actuel


def _get_prochain_niveau(points: int) -> dict | None:
    for n in NIVEAUX:
        if points < n["min"]:
            return n
    return None


def _get_ou_creer_fidelite(db: Session, user_id: int) -> PointFidelite:
    fidelite = db.query(PointFidelite).filter(PointFidelite.user_id == user_id).first()
    if not fidelite:
        fidelite = PointFidelite(user_id=user_id, points=0, niveau="Bronze")
        db.add(fidelite)
        db.commit()
        db.refresh(fidelite)
    return fidelite


@router.get("/mon-compte")
def mon_compte_fidelite(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Retourne le solde de points, le niveau et l'historique du client connecté."""
    user_id = int(current_user["sub"])
    fidelite = _get_ou_creer_fidelite(db, user_id)

    niveau_actuel = _get_niveau(fidelite.points)
    prochain = _get_prochain_niveau(fidelite.points)

    transactions = db.query(TransactionPoints).filter(
        TransactionPoints.user_id == user_id
    ).order_by(TransactionPoints.created_at.desc()).limit(10).all()

    return {
        "points": fidelite.points,
        "niveau": niveau_actuel,
        "prochain_niveau": prochain,
        "points_manquants": (prochain["min"] - fidelite.points) if prochain else 0,
        "progression": round(
            (fidelite.points - _get_niveau(fidelite.points)["min"]) /
            ((prochain["min"] - _get_niveau(fidelite.points)["min"]) or 1) * 100, 1
        ) if prochain else 100,
        "historique": [
            {
                "id": t.id,
                "delta": t.delta,
                "type": t.type,
                "description": t.description,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    }


@router.post("/crediter-commande/{commande_id}")
def crediter_points_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Crédite les points après une commande livrée (appelé automatiquement)."""
    user_id = int(current_user["sub"])

    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.user_id == user_id,
        Commande.statut == "livre"
    ).first()

    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable ou non livrée")

    # Vérifier si les points ont déjà été crédités
    existant = db.query(TransactionPoints).filter(
        TransactionPoints.commande_id == commande_id,
        TransactionPoints.type == "gain"
    ).first()
    if existant:
        raise HTTPException(status_code=400, detail="Points déjà crédités pour cette commande")

    points_gagnes = int(commande.total * POINTS_PAR_DH)  # 1 point par DH

    fidelite = _get_ou_creer_fidelite(db, user_id)
    fidelite.points += points_gagnes

    # Mettre à jour le niveau
    niveau = _get_niveau(fidelite.points)
    fidelite.niveau = niveau["nom"]

    transaction = TransactionPoints(
        user_id=user_id,
        commande_id=commande_id,
        delta=points_gagnes,
        type="gain",
        description=f"Commande #{commande_id} — {commande.total} DH"
    )
    db.add(transaction)
    db.commit()

    return {
        "points_gagnes": points_gagnes,
        "total_points": fidelite.points,
        "niveau": fidelite.niveau,
        "message": f"🎉 +{points_gagnes} points crédités !"
    }


@router.post("/bonus/{user_id}")
def crediter_bonus_admin(
    user_id: int,
    points: int,
    description: str = "Bonus administrateur",
    db: Session = Depends(get_db),
    _admin=Depends(admin_only)
):
    """[Admin] Crédite manuellement des points bonus à un client."""
    if points <= 0:
        raise HTTPException(status_code=400, detail="Le nombre de points doit être positif")

    fidelite = _get_ou_creer_fidelite(db, user_id)
    fidelite.points += points

    niveau = _get_niveau(fidelite.points)
    fidelite.niveau = niveau["nom"]

    transaction = TransactionPoints(
        user_id=user_id,
        commande_id=None,
        delta=points,
        type="bonus",
        description=description
    )
    db.add(transaction)
    db.commit()

    return {
        "points_credites": points,
        "total_points": fidelite.points,
        "niveau": fidelite.niveau,
        "message": f"✅ +{points} points bonus crédités à l'utilisateur #{user_id}"
    }


@router.get("/classement")
def classement_fidelite(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Top 10 des clients les plus fidèles."""
    top = db.query(PointFidelite).order_by(
        PointFidelite.points.desc()
    ).limit(10).all()

    result = []
    for i, f in enumerate(top):
        user = db.query(User).filter(User.id == f.user_id).first()
        niveau = _get_niveau(f.points)
        result.append({
            "rang": i + 1,
            "nom": user.nom if user else "—",
            "points": f.points,
            "niveau": niveau["nom"],
            "emoji": niveau["emoji"],
        })
    return result