from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.core.dependencies import get_current_user, client_only, admin_only
from app.models.avis import Avis
from app.models.commande import Commande
from app.models.produit import Produit
from app.models.livreur import Livreur
from app.schemas.avis import AvisCreate, AvisOut

router = APIRouter(prefix="/avis", tags=["Avis"])


# ── CLIENT : soumettre un avis après livraison ────────────────────────────────
@router.post("/")
def soumettre_avis(
    data: AvisCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])

    # Vérifier que la commande appartient au client et est livrée
    commande = db.query(Commande).filter(
        Commande.id == data.commande_id,
        Commande.user_id == user_id,
        Commande.statut == "livre"
    ).first()

    if not commande:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez noter que vos commandes livrées"
        )

    if commande.is_rated:
        raise HTTPException(status_code=400, detail="Vous avez déjà noté cette commande")

    avis = Avis(
        user_id=user_id,
        commande_id=data.commande_id,
        produit_id=data.produit_id,
        livreur_id=commande.livreur_id,
        note_produit=data.note_produit,
        note_livreur=data.note_livreur,
        commentaire=data.commentaire,
    )
    db.add(avis)
    commande.is_rated = True
    db.commit()
    db.refresh(avis)

    # Recalculer la note moyenne du produit
    if data.produit_id and data.note_produit:
        _recalculer_note_produit(db, data.produit_id)

    # Recalculer la note moyenne du livreur
    if commande.livreur_id and data.note_livreur:
        _recalculer_note_livreur(db, commande.livreur_id)

    return {"message": "Avis soumis avec succès. Merci !", "avis_id": avis.id}


def _recalculer_note_produit(db: Session, produit_id: int):
    result = db.query(func.avg(Avis.note_produit)).filter(
        Avis.produit_id == produit_id,
        Avis.note_produit.isnot(None),
        Avis.est_valide == True
    ).scalar()

    nb = db.query(Avis).filter(
        Avis.produit_id == produit_id,
        Avis.note_produit.isnot(None)
    ).count()

    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if produit and result:
        produit.note_moyenne = round(float(result), 2)
        produit.nb_avis = nb
        db.commit()


def _recalculer_note_livreur(db: Session, livreur_id: int):
    result = db.query(func.avg(Avis.note_livreur)).filter(
        Avis.livreur_id == livreur_id,
        Avis.note_livreur.isnot(None),
        Avis.est_valide == True
    ).scalar()

    livreur = db.query(Livreur).filter(Livreur.id == livreur_id).first()
    if livreur and result:
        livreur.note_moyenne = round(float(result), 2)
        db.commit()


# ── PUBLIC : avis d'un produit ────────────────────────────────────────────────
@router.get("/produit/{produit_id}")
def avis_produit(produit_id: int, db: Session = Depends(get_db)):
    avis_list = db.query(Avis).filter(
        Avis.produit_id == produit_id,
        Avis.est_valide == True,
        Avis.note_produit.isnot(None)
    ).order_by(Avis.created_at.desc()).limit(20).all()

    return [
        {
            "id": a.id,
            "note": a.note_produit,
            "commentaire": a.commentaire,
            "created_at": a.created_at.isoformat()
        }
        for a in avis_list
    ]


# ── ADMIN : supprimer un avis abusif ─────────────────────────────────────────
@router.delete("/{avis_id}")
def supprimer_avis(
    avis_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    avis = db.query(Avis).filter(Avis.id == avis_id).first()
    if not avis:
        raise HTTPException(status_code=404, detail="Avis introuvable")

    avis.est_valide = False
    db.commit()

    if avis.produit_id:
        _recalculer_note_produit(db, avis.produit_id)
    if avis.livreur_id:
        _recalculer_note_livreur(db, avis.livreur_id)

    return {"message": "Avis masqué"}