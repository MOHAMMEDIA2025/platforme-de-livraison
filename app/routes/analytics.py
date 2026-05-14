"""
app/routes/analytics.py

Collecte de données comportementales pour les modèles ML futurs :
  POST /analytics/session     — enregistre une session d'achat (temps passé + catégorie)
  POST /analytics/refresh-profil — recalcule le profil ML du client connecté
  GET  /analytics/profil      — retourne le profil ML du client connecté
  GET  /analytics/export-csv  — export CSV admin (profil_client)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import csv
import io

from app.database import get_db
from app.core.dependencies import get_current_user, admin_only
from app.models.ml_data import SessionAchat, ProfilClient
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.produit import Produit
from app.models.paiement import Paiement

router = APIRouter(prefix="/analytics", tags=["Analytics ML"])


# ── Schémas ───────────────────────────────────────────────────────────────────

class SessionPayload(BaseModel):
    categorie_fr:      str
    sous_categorie_fr: Optional[str] = None
    categorie_en:      Optional[str] = ""
    sous_categorie_en: Optional[str] = None
    nb_achats:         int = 0
    montant_total:     float = 0.0
    temps_secondes:    int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calcul_profil(db: Session, user_id: int) -> dict:
    """Calcule les métriques ML agrégées pour un client."""
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    # Commandes livrées
    commandes = db.query(Commande).filter(
        Commande.user_id == user_id,
        Commande.statut == "livre"
    ).order_by(Commande.created_at.desc()).all()

    nb_commandes = len(commandes)
    montant_total = sum(c.total or 0 for c in commandes)

    # Jours depuis dernière commande
    jours_depuis = None
    if commandes:
        last = commandes[0].created_at
        if last:
            jours_depuis = (datetime.utcnow() - last).days

    # Nombre total de produits achetés
    nb_produits = db.query(func.sum(LigneCommande.quantite)).join(
        Commande, LigneCommande.commande_id == Commande.id
    ).filter(
        Commande.user_id == user_id,
        Commande.statut == "livre"
    ).scalar() or 0

    # Catégorie dominante (par montant)
    cat_row = db.execute(text("""
        SELECT p.categorie, SUM(lc.prix_unitaire * lc.quantite) AS total
        FROM lignes_commande lc
        JOIN produits p ON p.id = lc.produit_id
        JOIN commandes c ON c.id = lc.commande_id
        WHERE c.user_id = :uid AND c.statut = 'livre'
        GROUP BY p.categorie
        ORDER BY total DESC
        LIMIT 1
    """), {"uid": user_id}).fetchone()

    categorie_dominante_fr = cat_row[0] if cat_row else None

    # Sous-catégorie dominante
    scat_row = db.execute(text("""
        SELECT p.category_plus, SUM(lc.prix_unitaire * lc.quantite) AS total
        FROM lignes_commande lc
        JOIN produits p ON p.id = lc.produit_id
        JOIN commandes c ON c.id = lc.commande_id
        WHERE c.user_id = :uid AND c.statut = 'livre' AND p.category_plus IS NOT NULL
        GROUP BY p.category_plus
        ORDER BY total DESC
        LIMIT 1
    """), {"uid": user_id}).fetchone()

    scat_dominante_fr = scat_row[0] if scat_row else None

    # Dernière commande statut livraison + méthode paiement
    derniere_statut = commandes[0].statut if commandes else None

    paiement_row = db.query(Paiement).filter(
        Paiement.user_id == user_id
    ).order_by(Paiement.created_at.desc()).first()

    methode = str(paiement_row.methode) if paiement_row else None

    return {
        "client_id": user_id,
        "nb_commandes": nb_commandes,
        "montant_total": round(float(montant_total), 2),
        "nb_produits": int(nb_produits),
        "jours_depuis_derniere": jours_depuis,
        "categorie_dominante_fr": categorie_dominante_fr,
        "categorie_dominante_en": None,
        "scat_dominante_fr": scat_dominante_fr,
        "scat_dominante_en": None,
        "derniere_livraison_statut": derniere_statut,
        "methode_paiement": methode,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/session")
def enregistrer_session(
    payload: SessionPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Enregistre une session d'achat (appelé par le frontend quand le client quitte une catégorie)."""
    from app.models.user import User
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    nom = user.nom or user.email or f"user_{user_id}" if user else f"user_{user_id}"

    session = SessionAchat(
        client_nom=nom,
        categorie_fr=payload.categorie_fr,
        sous_categorie_fr=payload.sous_categorie_fr,
        categorie_en=payload.categorie_en or "",
        sous_categorie_en=payload.sous_categorie_en,
        nb_achats=payload.nb_achats,
        montant_total=payload.montant_total,
        temps_secondes=payload.temps_secondes,
    )
    db.add(session)
    db.commit()
    return {"message": "Session enregistrée", "id": session.id}


@router.post("/refresh-profil")
def refresh_profil(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Recalcule et sauvegarde le profil ML du client connecté."""
    user_id = int(current_user["sub"])
    data = _calcul_profil(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    profil = db.query(ProfilClient).filter(ProfilClient.client_id == user_id).first()
    if profil:
        for k, v in data.items():
            if k != "client_id":
                setattr(profil, k, v)
        profil.mis_a_jour_le = datetime.utcnow()
    else:
        profil = ProfilClient(**data)
        db.add(profil)

    db.commit()
    db.refresh(profil)
    return {"message": "Profil mis à jour", "profil": data}


@router.get("/profil")
def get_profil(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Retourne le profil ML du client connecté."""
    user_id = int(current_user["sub"])
    profil = db.query(ProfilClient).filter(ProfilClient.client_id == user_id).first()
    if not profil:
        # Calcul à la volée si absent
        data = _calcul_profil(db, user_id)
        return data
    return {
        "client_id": profil.client_id,
        "nb_commandes": profil.nb_commandes,
        "montant_total": float(profil.montant_total),
        "nb_produits": profil.nb_produits,
        "jours_depuis_derniere": profil.jours_depuis_derniere,
        "categorie_dominante_fr": profil.categorie_dominante_fr,
        "scat_dominante_fr": profil.scat_dominante_fr,
        "derniere_livraison_statut": profil.derniere_livraison_statut,
        "methode_paiement": profil.methode_paiement,
        "mis_a_jour_le": profil.mis_a_jour_le,
    }


@router.post("/refresh-all-profils")
def refresh_all_profils(
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    """Recalcule les profils ML de tous les clients (admin)."""
    from app.models.user import User
    clients = db.query(User).filter(User.role == "client").all()
    updated = 0
    for user in clients:
        data = _calcul_profil(db, user.id)
        if not data:
            continue
        profil = db.query(ProfilClient).filter(ProfilClient.client_id == user.id).first()
        if profil:
            for k, v in data.items():
                if k != "client_id":
                    setattr(profil, k, v)
            profil.mis_a_jour_le = datetime.utcnow()
        else:
            profil = ProfilClient(**data)
            db.add(profil)
        updated += 1
    db.commit()
    return {"message": f"{updated} profils mis à jour"}


@router.get("/export-csv")
def export_csv(
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    """Export CSV de profil_client pour entraînement ML (admin)."""
    profils = db.query(ProfilClient).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "client_id", "nb_commandes", "montant_total", "nb_produits",
        "jours_depuis_derniere", "categorie_dominante", "scat_dominante",
        "derniere_livraison_statut", "methode_paiement", "mis_a_jour_le"
    ])
    for p in profils:
        writer.writerow([
            p.client_id, p.nb_commandes, float(p.montant_total or 0),
            p.nb_produits, p.jours_depuis_derniere,
            p.categorie_dominante_fr, p.scat_dominante_fr,
            p.derniere_livraison_statut, p.methode_paiement,
            p.mis_a_jour_le,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=profil_clients_ml.csv"}
    )


@router.get("/sessions-stats")
def sessions_stats(
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    """Statistiques des sessions d'achat par catégorie (admin)."""
    rows = db.execute(text("""
        SELECT
            categorie_fr,
            COUNT(*)                        AS nb_sessions,
            AVG(temps_secondes)::int        AS temps_moyen_sec,
            SUM(nb_achats)                  AS total_achats,
            SUM(montant_total)::float       AS ca_total
        FROM sessions_achat
        GROUP BY categorie_fr
        ORDER BY ca_total DESC
    """)).fetchall()

    return [
        {
            "categorie": r[0],
            "nb_sessions": r[1],
            "temps_moyen_sec": r[2],
            "total_achats": r[3],
            "ca_total": round(r[4] or 0, 2),
        }
        for r in rows
    ]
