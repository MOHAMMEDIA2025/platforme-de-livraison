"""
app/crud/commande_catalogue.py

Fonctions CRUD pour :
  - CommandeCatalogue / LigneCommandeCatalogue
  - LivraisonDetail
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.models.commande_catalogue import CommandeCatalogue, LigneCommandeCatalogue
from app.models.livraison_detail import LivraisonDetail
from app.schemas.commande_catalogue import (
    CommandeCatalogueCreate,
    LivraisonDetailCreate,
    LivraisonDetailUpdate,
    STATUTS_LIVRAISON,
    METHODES_PAIEMENT,
)


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

def get_commandes_catalogue(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(CommandeCatalogue)
        .order_by(CommandeCatalogue.date_commande.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_commande_catalogue(db: Session, commande_id: int):
    c = db.query(CommandeCatalogue).filter(CommandeCatalogue.id == commande_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commande catalogue introuvable")
    return c


def create_commande_catalogue(db: Session, data: CommandeCatalogueCreate):
    commande = CommandeCatalogue(
        nom_client=data.nom_client,
        date_commande=data.date_commande,
        code_promo=data.code_promo,
        remise_appliquee=data.remise_appliquee,
    )
    db.add(commande)
    db.flush()   # obtenir l'id sans commit

    for ligne_data in data.lignes:
        ligne = LigneCommandeCatalogue(
            commande_id=commande.id,
            **ligne_data.dict()
        )
        db.add(ligne)

    db.commit()
    db.refresh(commande)
    return commande


def delete_commande_catalogue(db: Session, commande_id: int):
    c = get_commande_catalogue(db, commande_id)
    db.delete(c)
    db.commit()
    return {"message": f"Commande catalogue #{commande_id} supprimée"}


def get_stats_catalogue(db: Session):
    """Statistiques rapides sur les commandes catalogue."""
    total_commandes = db.query(func.count(CommandeCatalogue.id)).scalar() or 0

    total_ca_avant = db.query(
        func.sum(LigneCommandeCatalogue.prix_ligne_avant_promo)
    ).scalar() or 0

    total_ca_apres = db.query(
        func.sum(LigneCommandeCatalogue.prix_ligne_apres_promo)
    ).scalar() or 0

    top_produits = (
        db.query(
            LigneCommandeCatalogue.produit_achete_fr,
            func.sum(LigneCommandeCatalogue.quantite).label("total_vendu"),
        )
        .group_by(LigneCommandeCatalogue.produit_achete_fr)
        .order_by(func.sum(LigneCommandeCatalogue.quantite).desc())
        .limit(5)
        .all()
    )

    top_categories = (
        db.query(
            LigneCommandeCatalogue.categorie_fr,
            func.sum(LigneCommandeCatalogue.prix_ligne_apres_promo).label("ca"),
        )
        .group_by(LigneCommandeCatalogue.categorie_fr)
        .order_by(func.sum(LigneCommandeCatalogue.prix_ligne_apres_promo).desc())
        .all()
    )

    return {
        "total_commandes": total_commandes,
        "ca_avant_promo": round(float(total_ca_avant), 2),
        "ca_apres_promo": round(float(total_ca_apres), 2),
        "economie_promo": round(float(total_ca_avant) - float(total_ca_apres), 2),
        "top_produits": [
            {"produit": r.produit_achete_fr, "total_vendu": r.total_vendu}
            for r in top_produits
        ],
        "top_categories": [
            {"categorie": r.categorie_fr, "ca": round(float(r.ca), 2)}
            for r in top_categories
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  LIVRAISONS DETAIL
# ══════════════════════════════════════════════════════════════════════════════

def get_livraisons_detail(
    db: Session,
    statut: str = None,
    nom_livreur: str = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(LivraisonDetail)

    if statut:
        q = q.filter(LivraisonDetail.statut == statut)
    if nom_livreur:
        q = q.filter(LivraisonDetail.nom_livreur.ilike(f"%{nom_livreur}%"))

    return q.order_by(LivraisonDetail.date_livraison.desc()).offset(skip).limit(limit).all()


def get_livraison_detail(db: Session, livraison_id: int):
    l = db.query(LivraisonDetail).filter(LivraisonDetail.id_livraison == livraison_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Livraison introuvable")
    return l


def create_livraison_detail(db: Session, data: LivraisonDetailCreate):
    if data.statut not in STATUTS_LIVRAISON:
        raise HTTPException(
            status_code=400,
            detail=f"Statut invalide. Valeurs acceptées : {STATUTS_LIVRAISON}"
        )
    if data.methode_paiement not in METHODES_PAIEMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Méthode de paiement invalide. Valeurs acceptées : {METHODES_PAIEMENT}"
        )
    livraison = LivraisonDetail(**data.dict())
    db.add(livraison)
    db.commit()
    db.refresh(livraison)
    return livraison


def update_livraison_detail(db: Session, livraison_id: int, data: LivraisonDetailUpdate):
    livraison = get_livraison_detail(db, livraison_id)

    if data.statut is not None and data.statut not in STATUTS_LIVRAISON:
        raise HTTPException(
            status_code=400,
            detail=f"Statut invalide. Valeurs acceptées : {STATUTS_LIVRAISON}"
        )

    for field, value in data.dict(exclude_unset=True).items():
        setattr(livraison, field, value)

    db.commit()
    db.refresh(livraison)
    return livraison


def delete_livraison_detail(db: Session, livraison_id: int):
    livraison = get_livraison_detail(db, livraison_id)
    db.delete(livraison)
    db.commit()
    return {"message": f"Livraison #{livraison_id} supprimée"}


def get_stats_livraisons(db: Session):
    """Statistiques rapides sur les livraisons."""
    total = db.query(func.count(LivraisonDetail.id_livraison)).scalar() or 0

    par_statut = (
        db.query(LivraisonDetail.statut, func.count(LivraisonDetail.id_livraison).label("nb"))
        .group_by(LivraisonDetail.statut)
        .all()
    )

    par_livreur = (
        db.query(
            LivraisonDetail.nom_livreur,
            func.count(LivraisonDetail.id_livraison).label("nb_livraisons"),
            func.sum(LivraisonDetail.prix_total_livraison).label("ca"),
        )
        .group_by(LivraisonDetail.nom_livreur)
        .order_by(func.count(LivraisonDetail.id_livraison).desc())
        .all()
    )

    par_paiement = (
        db.query(
            LivraisonDetail.methode_paiement,
            func.count(LivraisonDetail.id_livraison).label("nb"),
        )
        .group_by(LivraisonDetail.methode_paiement)
        .all()
    )

    return {
        "total_livraisons": total,
        "par_statut": [{"statut": r.statut, "nb": r.nb} for r in par_statut],
        "par_livreur": [
            {
                "livreur": r.nom_livreur,
                "nb_livraisons": r.nb_livraisons,
                "ca": round(float(r.ca or 0), 2),
            }
            for r in par_livreur
        ],
        "par_methode_paiement": [
            {"methode": r.methode_paiement, "nb": r.nb} for r in par_paiement
        ],
    }