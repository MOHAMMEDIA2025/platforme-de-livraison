"""
app/routes/produit.py — VERSION AVEC GALERIE img_yanda
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pathlib import Path

from app.database import get_db
from app.core.dependencies import admin_only, get_current_user
from app.models.produit import Produit
from app.schemas.produit import ProduitCreate, ProduitUpdate, ProduitOut

router = APIRouter(prefix="/produits", tags=["Produits"])

IMG_YANDA_DIR = Path("img_yanda")
SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".bmp"]


def _get_image_url(produit: Produit) -> str | None:
    if produit.image_folder:
        return f"/img/{produit.image_folder}/1"
    return produit.image_url

def _get_image_urls(produit: Produit) -> list:
    if produit.image_folder:
        return [f"/img/{produit.image_folder}/{i}" for i in [1, 2, 3]]
    if produit.image_url:
        return [produit.image_url]
    return []

def _produit_to_dict(p: Produit) -> dict:
    return {
        "id": p.id,
        "nom": p.nom or "",
        "nom_eng": p.nom_eng,
        "prix": p.prix or 0.0,
        "quantite": p.quantite or 0,
        "categorie": p.categorie or "Général",
        "categorie_eng": p.categorie_eng,
        "category_plus": p.category_plus,
        "category_plus_eng": p.category_plus_eng,
        "promotion": p.promotion,
        "stock": p.stock or 0,
        "description": p.description or "",
        "description_eng": p.description_eng,
        "caracteristique": p.caracteristique,
        "caracteristique_eng": p.caracteristique_eng,
        "date_ajout": p.date_ajout,
        "est_disponible": p.est_disponible,
        "est_promo": p.est_promo,
        "prix_promo": p.prix_promo,
        "note_moyenne": p.note_moyenne or 0.0,
        "nb_avis": p.nb_avis or 0,
        "image_folder": p.image_folder,
        "image_url": _get_image_url(p),
        "image_urls": _get_image_urls(p),
    }


# ── Catalogue public ──────────────────────────────────────────────────────────
@router.get("/", response_model=List[ProduitOut])
def get_produits(
    search: Optional[str] = Query(None),
    categorie: Optional[str] = Query(None),
    promo_only: bool = Query(False),
    sort_by: Optional[str] = Query("nom"),
    db: Session = Depends(get_db)
):
    q = db.query(Produit).filter(
        or_(Produit.stock > 0, Produit.stock == None)
    )

    if search:
        q = q.filter(Produit.nom.ilike(f"%{search}%"))

    if categorie:
        q = q.filter(Produit.categorie == categorie)

    if promo_only:
        q = q.filter(Produit.promotion > 0)

    if sort_by == "prix":
        q = q.order_by(Produit.prix)
    else:
        q = q.order_by(Produit.nom)

    produits = q.all()
    return [_produit_to_dict(p) for p in produits]


# ── Catégories disponibles ────────────────────────────────────────────────────
@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    rows = db.query(Produit.categorie).filter(
        or_(Produit.stock > 0, Produit.stock == None)
    ).distinct().all()
    return [r[0] for r in rows if r[0]]


# ── Produits en promotion ─────────────────────────────────────────────────────
@router.get("/promotions", response_model=List[ProduitOut])
def get_promotions(db: Session = Depends(get_db)):
    produits = db.query(Produit).filter(
        Produit.promotion > 0,
        or_(Produit.stock > 0, Produit.stock == None)
    ).all()
    return [_produit_to_dict(p) for p in produits]


# ── Détail produit ────────────────────────────────────────────────────────────
@router.get("/{produit_id}", response_model=ProduitOut)
def get_produit(produit_id: int, db: Session = Depends(get_db)):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return _produit_to_dict(produit)


# ── Admin : créer un produit ──────────────────────────────────────────────────
@router.post("/", response_model=ProduitOut)
def create_produit(
    data: ProduitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = Produit(
        nom=data.nom,
        nom_eng=data.nom_eng,
        prix=data.prix,
        quantite=data.quantite,
        categorie=data.categorie,
        categorie_eng=data.categorie_eng,
        category_plus=data.category_plus,
        category_plus_eng=data.category_plus_eng,
        promotion=data.promotion,
        stock=data.stock,
        description=data.description,
        description_eng=data.description_eng,
        caracteristique=data.caracteristique,
        caracteristique_eng=data.caracteristique_eng,
        date_ajout=data.date_ajout,
        image_folder=data.image_folder,
        image_url=data.image_url,
        est_disponible=True,
        note_moyenne=0.0,
        nb_avis=0,
        est_promo=data.est_promo or False,
        prix_promo=data.prix_promo,
    )
    db.add(produit)
    db.commit()
    db.refresh(produit)
    return _produit_to_dict(produit)


# ── Admin : modifier un produit ───────────────────────────────────────────────
@router.put("/{produit_id}", response_model=ProduitOut)
def update_produit(
    produit_id: int,
    data: ProduitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(produit, field, value)

    db.commit()
    db.refresh(produit)
    return _produit_to_dict(produit)


# ── Admin : désactiver un produit ─────────────────────────────────────────────
@router.delete("/{produit_id}")
def delete_produit(
    produit_id: int,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    if hard_delete:
        db.delete(produit)
    else:
        produit.stock = 0

    db.commit()
    return {"message": "Produit supprimé"}


# ── Admin : réapprovisionner ──────────────────────────────────────────────────
@router.patch("/{produit_id}/stock")
def update_stock(
    produit_id: int,
    quantite: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    produit.stock = quantite
    db.commit()
    return {"id": produit_id, "stock": produit.stock}


# ── API : lister les dossiers img_yanda disponibles ───────────────────────────
@router.get("/img-folders/list")
def list_img_folders(current_user=Depends(admin_only)):
    if not IMG_YANDA_DIR.exists():
        return {"folders": [], "message": "Dossier img_yanda introuvable"}

    folders = sorted([
        d.name for d in IMG_YANDA_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    return {"folders": folders, "count": len(folders)}
