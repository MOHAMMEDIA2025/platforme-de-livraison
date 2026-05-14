"""
app/routes/commande_catalogue.py

Routes pour :
  - /catalogue/commandes     → gestion des commandes multi-produits (analytique)
  - /catalogue/livraisons    → gestion des livraisons enrichies
  - /catalogue/stats/*       → statistiques admin

Toutes les routes de modification (POST/PUT/DELETE) sont réservées aux admins.
Les GET sont accessibles aux admins et aux livreurs.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import admin_only, get_current_user

from app.schemas.commande_catalogue import (
    CommandeCatalogueCreate,
    CommandeCatalogueOut,
    CommandeCatalogueListOut,
    LivraisonDetailCreate,
    LivraisonDetailUpdate,
    LivraisonDetailOut,
)
from app.crud.commande_catalogue import (
    get_commandes_catalogue,
    get_commande_catalogue,
    create_commande_catalogue,
    delete_commande_catalogue,
    get_stats_catalogue,
    get_livraisons_detail,
    get_livraison_detail,
    create_livraison_detail,
    update_livraison_detail,
    delete_livraison_detail,
    get_stats_livraisons,
)

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

# ✅ FIX : response_model=List[CommandeCatalogueListOut] pour correspondre
#          au dict custom retourné (nb_lignes, total_avant_promo, total_apres_promo)
@router.get(
    "/commandes",
    response_model=List[CommandeCatalogueListOut],
    summary="Liste des commandes catalogue (multi-produits)"
)
def list_commandes_catalogue(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    commandes = get_commandes_catalogue(db, skip=skip, limit=limit)
    result = []
    for c in commandes:
        total_avant = sum(float(l.prix_ligne_avant_promo) for l in c.lignes)
        total_apres = sum(float(l.prix_ligne_apres_promo) for l in c.lignes)
        result.append({
            "id": c.id,
            "nom_client": c.nom_client,
            "date_commande": c.date_commande,
            "code_promo": c.code_promo,
            "remise_appliquee": float(c.remise_appliquee),
            "nb_lignes": len(c.lignes),
            "total_avant_promo": round(total_avant, 2),
            "total_apres_promo": round(total_apres, 2),
        })
    return result


@router.get(
    "/commandes/{commande_id}",
    response_model=CommandeCatalogueOut,
    summary="Détail d'une commande catalogue"
)
def detail_commande_catalogue(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return get_commande_catalogue(db, commande_id)


@router.post(
    "/commandes",
    response_model=CommandeCatalogueOut,
    status_code=201,
    summary="Créer une commande catalogue avec ses lignes"
)
def create_commande(
    data: CommandeCatalogueCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return create_commande_catalogue(db, data)


@router.delete("/commandes/{commande_id}", summary="Supprimer une commande catalogue")
def delete_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return delete_commande_catalogue(db, commande_id)


# ✅ FIX : URL correcte /stats/commandes (le frontend appelait /catalogue/stats)
@router.get("/stats/commandes", summary="Statistiques commandes catalogue (admin)")
def stats_commandes_catalogue(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return get_stats_catalogue(db)


# ══════════════════════════════════════════════════════════════════════════════
#  LIVRAISONS DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/livraisons",
    response_model=List[LivraisonDetailOut],
    summary="Liste des livraisons enrichies"
)
def list_livraisons(
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    nom_livreur: Optional[str] = Query(None, description="Filtrer par nom livreur"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Admins voient tout ; les livreurs voient seulement leurs livraisons
    role = current_user.get("role")
    if role == "livreur":
        nom_livreur = current_user.get("nom") or nom_livreur

    return get_livraisons_detail(db, statut=statut, nom_livreur=nom_livreur, skip=skip, limit=limit)


@router.get(
    "/livraisons/{livraison_id}",
    response_model=LivraisonDetailOut,
    summary="Détail d'une livraison"
)
def detail_livraison(
    livraison_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_livraison_detail(db, livraison_id)


@router.post(
    "/livraisons",
    response_model=LivraisonDetailOut,
    status_code=201,
    summary="Créer une livraison (admin)"
)
def create_livraison(
    data: LivraisonDetailCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return create_livraison_detail(db, data)


@router.put(
    "/livraisons/{livraison_id}",
    response_model=LivraisonDetailOut,
    summary="Modifier une livraison (statut, livreur, notes…)"
)
def update_livraison(
    livraison_id: int,
    data: LivraisonDetailUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return update_livraison_detail(db, livraison_id, data)


@router.delete("/livraisons/{livraison_id}", summary="Supprimer une livraison (admin)")
def delete_livraison(
    livraison_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return delete_livraison_detail(db, livraison_id)


@router.get("/stats/livraisons", summary="Statistiques livraisons (admin)")
def stats_livraisons(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    return get_stats_livraisons(db)