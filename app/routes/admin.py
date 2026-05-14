from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.core.dependencies import admin_only
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.produit import Produit
from app.models.livreur import Livreur
from app.models.user import User
from app.models.notification import Notification
from app.models.livraison_detail import LivraisonDetail
from app.models.paiement import Paiement
from app.models.ml_data import ProfilClient
from app.schemas.produit import ProduitCreate, ProduitUpdate, ProduitOut
from datetime import datetime, timedelta
from typing import List, Optional
import csv
import io
import os
import uuid
import aiofiles

router = APIRouter(prefix="/admin", tags=["Admin"])

# ─── Dossier de stockage des images produits ──────────────────────────────────
UPLOAD_DIR = "static/images/produits"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Stats globales ───────────────────────────────────────────────────────────
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    aujourd_hui = datetime.utcnow().date()
    debut = datetime.combine(aujourd_hui, datetime.min.time())

    ca_aujourd_hui = db.query(func.sum(Commande.total)).filter(
        Commande.statut == "livre",
        Commande.created_at >= debut
    ).scalar() or 0

    ca_total = db.query(func.sum(Commande.total)).filter(
        Commande.statut == "livre"
    ).scalar() or 0

    commandes_actives = db.query(Commande).filter(
        Commande.statut.in_(["pending", "en_preparation", "en_route"])
    ).count()

    commandes_aujourd_hui = db.query(Commande).filter(
        Commande.created_at >= debut
    ).count()

    livreurs_disponibles = db.query(Livreur).filter(
        Livreur.statut == "disponible",
        Livreur.is_online == True
    ).count()

    total_livreurs = db.query(Livreur).count()
    total_clients = db.query(User).filter(User.role == "client").count()
    total_produits = db.query(Produit).filter(Produit.est_disponible == True).count()

    return {
        "ca_aujourd_hui": round(float(ca_aujourd_hui), 2),
        "ca_total": round(float(ca_total), 2),
        "commandes_actives": commandes_actives,
        "commandes_aujourd_hui": commandes_aujourd_hui,
        "livreurs_disponibles": livreurs_disponibles,
        "total_livreurs": total_livreurs,
        "total_clients": total_clients,
        "total_produits": total_produits,
    }


# ─── CA sur 7 jours ───────────────────────────────────────────────────────────
@router.get("/ventes-semaine")
def ventes_semaine(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    result = []
    for i in range(6, -1, -1):
        jour = datetime.utcnow().date() - timedelta(days=i)
        debut = datetime.combine(jour, datetime.min.time())
        fin   = debut + timedelta(days=1)

        ca = db.query(func.sum(Commande.total)).filter(
            Commande.statut == "livre",
            Commande.created_at >= debut,
            Commande.created_at < fin
        ).scalar() or 0

        nb = db.query(Commande).filter(
            Commande.created_at >= debut,
            Commande.created_at < fin
        ).count()

        result.append({
            "jour": jour.strftime("%d/%m"),
            "ca": round(float(ca), 2),
            "commandes": nb
        })
    return result


# ─── Top produits ─────────────────────────────────────────────────────────────
@router.get("/top-produits")
def top_produits(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    rows = db.query(
        LigneCommande.nom_produit,
        func.sum(LigneCommande.quantite).label("total_vendu"),
        func.sum(LigneCommande.prix_unitaire * LigneCommande.quantite).label("ca")
    ).group_by(LigneCommande.nom_produit).order_by(
        func.sum(LigneCommande.quantite).desc()
    ).limit(5).all()

    return [{"nom": r.nom_produit, "total_vendu": r.total_vendu, "ca": round(float(r.ca or 0), 2)} for r in rows]


# ─── Répartition des statuts ──────────────────────────────────────────────────
@router.get("/repartition-statuts")
def repartition_statuts(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    statuts = ["pending", "en_preparation", "en_route", "livre", "annule"]
    result = []
    for s in statuts:
        count = db.query(Commande).filter(Commande.statut == s).count()
        result.append({"statut": s, "count": count})
    return result


# ─── Liste toutes les commandes ───────────────────────────────────────────────
@router.get("/commandes")
def get_commandes(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    commandes = db.query(Commande).order_by(Commande.created_at.desc()).limit(200).all()
    result = []
    for cmd in commandes:
        client  = db.query(User).filter(User.id == cmd.user_id).first()
        livreur = db.query(Livreur).filter(Livreur.id == cmd.livreur_id).first() if cmd.livreur_id else None
        result.append({
            "id": cmd.id,
            "client_email": client.email if client else "—",
            "client_nom": client.nom if client else "—",
            "adresse": cmd.adresse,
            "total": cmd.total,
            "statut": cmd.statut,
            "reduction": cmd.reduction,
            "code_promo": cmd.code_promo,
            "frais_livraison": cmd.frais_livraison,
            "livreur_id": cmd.livreur_id,
            "livreur_nom": livreur.nom if livreur else None,
            "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
        })
    return result


# ─── Détails d'une commande ───────────────────────────────────────────────────
@router.get("/commandes/{commande_id}")
def get_commande_detail(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    client  = db.query(User).filter(User.id == commande.user_id).first()
    livreur = db.query(Livreur).filter(Livreur.id == commande.livreur_id).first() if commande.livreur_id else None
    lignes  = db.query(LigneCommande).filter(LigneCommande.commande_id == commande_id).all()

    return {
        "id": commande.id,
        "statut": commande.statut,
        "adresse": commande.adresse,
        "note_client": commande.note_client,
        "total": commande.total,
        "frais_livraison": commande.frais_livraison,
        "reduction": commande.reduction,
        "code_promo": commande.code_promo,
        "is_rated": commande.is_rated,
        "created_at": commande.created_at.isoformat() if commande.created_at else None,
        "client": {
            "id": client.id if client else None,
            "email": client.email if client else "—",
            "nom": client.nom if client else "—",
            "telephone": client.telephone if client else "—",
        },
        "livreur": {
            "id": livreur.id if livreur else None,
            "nom": livreur.nom if livreur else None,
            "telephone": livreur.telephone if livreur else None,
        } if livreur else None,
        "lignes": [
            {
                "produit": l.nom_produit or f"Produit #{l.produit_id}",
                "quantite": l.quantite,
                "prix_unitaire": l.prix_unitaire or 0,
                "sous_total": round((l.prix_unitaire or 0) * l.quantite, 2)
            }
            for l in lignes
        ]
    }


# ─── Modifier le statut d'une commande ───────────────────────────────────────
@router.put("/commandes/{commande_id}/statut")
def update_statut_commande(
    commande_id: int,
    statut: str,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    STATUTS = ["pending", "en_preparation", "en_route", "livre", "annule"]
    if statut not in STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide")

    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    commande.statut = statut
    db.commit()

    # ── Quand admin marque "livre" : créditer points + mettre à jour profil ML ─
    if statut == "livre":
        try:
            from app.routes.commande import _crediter_points
            _crediter_points(db, commande.user_id, commande_id, commande.total or 0)
            db.commit()
        except Exception as e:
            print(f"[WARN] points fidélité admin livre : {e}")

        try:
            from app.models.ml_data import ProfilClient
            from app.models.commande_item import LigneCommande as LC
            from sqlalchemy import func, text as sql_text

            commandes_livrees = db.query(Commande).filter(
                Commande.user_id == commande.user_id,
                Commande.statut  == "livre"
            ).all()

            nb_cmd    = len(commandes_livrees)
            montant_t = sum(c.total or 0 for c in commandes_livrees)
            nb_prod   = db.query(func.sum(LC.quantite)).join(
                Commande, LC.commande_id == Commande.id
            ).filter(
                Commande.user_id == commande.user_id,
                Commande.statut  == "livre"
            ).scalar() or 0

            cat_row = db.execute(sql_text("""
                SELECT p.categorie, SUM(lc.prix_unitaire * lc.quantite) AS t
                FROM lignes_commande lc
                JOIN produits p ON p.id = lc.produit_id
                JOIN commandes c ON c.id = lc.commande_id
                WHERE c.user_id = :uid AND c.statut = 'livre'
                GROUP BY p.categorie ORDER BY t DESC LIMIT 1
            """), {"uid": commande.user_id}).fetchone()
            cat_dom = cat_row[0] if cat_row else None

            scat_row = db.execute(sql_text("""
                SELECT p.category_plus, SUM(lc.prix_unitaire * lc.quantite) AS t
                FROM lignes_commande lc
                JOIN produits p ON p.id = lc.produit_id
                JOIN commandes c ON c.id = lc.commande_id
                WHERE c.user_id = :uid AND c.statut = 'livre'
                  AND p.category_plus IS NOT NULL
                GROUP BY p.category_plus ORDER BY t DESC LIMIT 1
            """), {"uid": commande.user_id}).fetchone()
            scat_dom = scat_row[0] if scat_row else None

            paiement_obj = db.query(Paiement).filter(
                Paiement.commande_id == commande_id
            ).first()
            methode_str = str(paiement_obj.methode) if paiement_obj else None

            profil_ml = db.query(ProfilClient).filter(
                ProfilClient.client_id == commande.user_id
            ).first()

            data_ml = {
                "nb_commandes":             nb_cmd,
                "montant_total":            round(float(montant_t), 2),
                "nb_produits":              int(nb_prod),
                "jours_depuis_derniere":    0,
                "categorie_dominante_fr":   cat_dom,
                "scat_dominante_fr":        scat_dom,
                "derniere_livraison_statut":"livre",
                "methode_paiement":         methode_str,
                "mis_a_jour_le":            datetime.utcnow(),
            }

            if profil_ml:
                for k, v in data_ml.items():
                    setattr(profil_ml, k, v)
            else:
                profil_ml = ProfilClient(client_id=commande.user_id, **data_ml)
                db.add(profil_ml)

            db.commit()
            print(f"[ML] profil_client mis à jour (admin) pour user #{commande.user_id}")
        except Exception as e:
            db.rollback()
            print(f"[WARN] profil_client admin : {e}")

    notif_msgs = {
        "en_preparation": ("En préparation 👨‍🍳", f"Votre commande #{commande_id} est en cours de préparation.", "info"),
        "en_route":       ("En route 🛵",          f"Votre commande #{commande_id} est en route !",               "success"),
        "livre":          ("Livrée ! 🎉",          f"Votre commande #{commande_id} a été livrée.",                "success"),
        "annule":         ("Commande annulée ❌",   f"Votre commande #{commande_id} a été annulée.",               "error"),
    }

    if statut in notif_msgs:
        titre, message, type_ = notif_msgs[statut]
        notif = Notification(
            user_id=commande.user_id,
            titre=titre,
            message=message,
            type=type_,
            lien=f"/tracking/{commande_id}"
        )
        db.add(notif)
        db.commit()

    return {"message": f"Statut mis à jour : {statut}"}


# ─── Assigner un livreur ──────────────────────────────────────────────────────
@router.post("/commandes/{commande_id}/assigner-livreur")
def assigner_livreur(
    commande_id: int,
    livreur_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    livreur = db.query(Livreur).filter(Livreur.id == livreur_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    if livreur.statut not in ("disponible",):
        raise HTTPException(status_code=400, detail=f"Livreur non disponible (statut: {livreur.statut})")

    commande.livreur_id = livreur_id
    if commande.statut == "pending":
        commande.statut = "en_preparation"

    livreur.statut = "occupé"
    db.commit()

    try:
        client = db.query(User).filter(User.id == commande.user_id).first()
        nom_client = (client.nom or "").strip() if client else f"Client #{commande.user_id}"

        livraison = db.query(LivraisonDetail).filter(
            LivraisonDetail.localisation_client == commande.adresse,
            LivraisonDetail.nom_client == nom_client,
        ).order_by(LivraisonDetail.id_livraison.desc()).first()

        if livraison:
            livraison.nom_livreur = livreur.nom
            db.commit()
    except Exception as e:
        print(f"[WARN] Synchro livraisons_detail (assigner-livreur) : {e}")

    notif = Notification(
        user_id=commande.user_id,
        titre="Livreur assigné 🛵",
        message=f"Votre commande #{commande_id} est prise en charge par {livreur.nom}.",
        type="info",
        icon="🛵",
        lien=f"/tracking/{commande_id}"
    )
    db.add(notif)
    db.commit()

    return {"message": f"Livreur {livreur.nom} assigné à la commande #{commande_id}"}


# ─── Export CSV ───────────────────────────────────────────────────────────────
@router.get("/export/commandes")
def export_commandes_csv(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    commandes = db.query(Commande).order_by(Commande.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Client Email", "Client Nom", "Adresse", "Total (DH)", "Réduction (DH)", "Code Promo", "Statut", "Livreur", "Date"])

    for cmd in commandes:
        client  = db.query(User).filter(User.id == cmd.user_id).first()
        livreur = db.query(Livreur).filter(Livreur.id == cmd.livreur_id).first() if cmd.livreur_id else None
        writer.writerow([
            cmd.id,
            client.email if client else "—",
            client.nom if client else "—",
            cmd.adresse,
            cmd.total,
            cmd.reduction,
            cmd.code_promo or "—",
            cmd.statut,
            livreur.nom if livreur else "—",
            cmd.created_at.strftime("%d/%m/%Y %H:%M") if cmd.created_at else "—"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commandes_export.csv"}
    )


# ─── Liste livreurs avec détails ──────────────────────────────────────────────
@router.get("/livreurs")
def get_livreurs_detail(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    livreurs = db.query(Livreur).all()
    result = []
    for l in livreurs:
        user = db.query(User).filter(User.id == l.id).first()
        nb_commandes = db.query(Commande).filter(Commande.livreur_id == l.id).count()
        result.append({
            "id": l.id,
            "nom": l.nom,
            "email": user.email if user else "—",
            "telephone": l.telephone,
            "statut": l.statut,
            "vehicule": l.vehicule,
            "zone": l.zone,
            "note_moyenne": l.note_moyenne,
            "nb_livraisons": l.nb_livraisons,
            "is_online": l.is_online,
            "nb_commandes": nb_commandes,
        })
    return result


# ─── Changer statut livreur ───────────────────────────────────────────────────
@router.put("/livreurs/{livreur_id}/statut")
def update_statut_livreur(
    livreur_id: int,
    statut: str,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    STATUTS = ["disponible", "occupé", "hors_ligne"]
    if statut not in STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide")

    livreur = db.query(Livreur).filter(Livreur.id == livreur_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    livreur.statut = statut
    db.commit()
    return {"message": f"Statut livreur mis à jour : {statut}"}


# ─── Liste tous les utilisateurs ─────────────────────────────────────────────
@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    users = db.query(User).order_by(User.id.desc()).all()
    result = []
    for u in users:
        nb_commandes = db.query(Commande).filter(Commande.user_id == u.id).count()
        livreur = db.query(Livreur).filter(Livreur.id == u.id).first()
        result.append({
            "id": u.id,
            "email": u.email,
            "nom": u.nom,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "nb_commandes": nb_commandes,
            "livreur_nom": livreur.nom if livreur else None,
            "livreur_telephone": livreur.telephone if livreur else None,
        })
    return result


# ─── Ban / Unban utilisateur ──────────────────────────────────────────────────
@router.put("/users/{user_id}/toggle-actif")
def toggle_actif_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Impossible de désactiver un administrateur")

    user.is_active = not user.is_active
    db.commit()

    action = "réactivé" if user.is_active else "suspendu"
    return {
        "message": f"Compte {action} avec succès",
        "is_active": user.is_active,
        "user_id": user_id
    }


# ─── Changer le rôle d'un utilisateur ────────────────────────────────────────
@router.put("/users/{user_id}/role")
def changer_role(
    user_id: int,
    role: str,
    nom: str = None,
    telephone: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    ROLES_VALIDES = ["client", "livreur", "admin"]
    if role not in ROLES_VALIDES:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if user.role == "admin" and role != "admin":
        raise HTTPException(status_code=403, detail="Impossible de modifier un admin")

    ancien_role = user.role
    user.role = role
    db.commit()

    if role == "livreur" and ancien_role != "livreur":
        livreur_existant = db.query(Livreur).filter(Livreur.id == user_id).first()
        if not livreur_existant:
            nouveau_livreur = Livreur(
                id=user_id,
                nom=nom or (user.nom or user.email.split("@")[0]),
                telephone=telephone or (user.telephone or "—"),
                statut="disponible"
            )
            db.add(nouveau_livreur)
            db.commit()

    if ancien_role == "livreur" and role != "livreur":
        livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
        if livreur:
            db.delete(livreur)
            db.commit()

    return {
        "message": f"Rôle de {user.email} changé : {ancien_role} → {role}",
        "user_id": user_id,
        "nouveau_role": role,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ─── Gestion produits (Admin) ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/produits")
def get_produits_admin(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    """Liste TOUS les produits (y compris indisponibles) pour l'admin."""
    produits = db.query(Produit).order_by(Produit.id.desc()).all()
    return [
        {
            "id": p.id,
            "nom": p.nom,
            "description": p.description,
            "prix": p.prix,
            "prix_promo": p.prix_promo,
            "est_promo": p.est_promo,
            "stock": p.stock,
            "categorie": p.categorie,
            "est_disponible": p.est_disponible,
            "image_url": p.image_url,
            "note_moyenne": p.note_moyenne,
            "nb_avis": p.nb_avis,
        }
        for p in produits
    ]


@router.post("/produits")
def create_produit_admin(
    data: ProduitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = Produit(
        nom=data.nom,
        nom_eng=data.nom_eng,
        prix=data.prix,
        quantite=data.quantite or 0,
        categorie=data.categorie or "Général",
        categorie_eng=data.categorie_eng,
        category_plus=data.category_plus,
        category_plus_eng=data.category_plus_eng,
        promotion=data.promotion,
        stock=data.stock if data.stock is not None else (data.quantite or 0),
        description=data.description,
        description_eng=data.description_eng,
        caracteristique=data.caracteristique,
        caracteristique_eng=data.caracteristique_eng,
        date_ajout=data.date_ajout,
    )
    produit.est_disponible = True
    produit.note_moyenne = 0.0
    produit.nb_avis = 0
    produit.image_url = data.image_url
    produit.est_promo = data.est_promo or False
    produit.prix_promo = data.prix_promo

    db.add(produit)
    db.commit()
    db.refresh(produit)

    return {
        "id": produit.id,
        "nom": produit.nom,
        "prix": produit.prix,
        "stock": produit.stock,
        "categorie": produit.categorie,
        "est_disponible": produit.est_disponible,
        "est_promo": produit.est_promo,
        "prix_promo": produit.prix_promo,
        "image_url": produit.image_url,
        "note_moyenne": produit.note_moyenne,
        "nb_avis": produit.nb_avis,
    }


@router.put("/produits/{produit_id}")
def update_produit_admin(
    produit_id: int,
    data: ProduitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    mapping = {
        "nom": "nom",
        "nom_eng": "nom_eng",
        "prix": "prix",
        "quantite": "quantite",
        "categorie": "categorie",
        "categorie_eng": "categorie_eng",
        "category_plus": "category_plus",
        "category_plus_eng": "category_plus_eng",
        "promotion": "promotion",
        "stock": "stock",
        "description": "description",
        "description_eng": "description_eng",
        "caracteristique": "caracteristique",
        "caracteristique_eng": "caracteristique_eng",
        "image_url": "image_url",
        "est_promo": "est_promo",
        "prix_promo": "prix_promo",
    }

    for field, value in data.dict(exclude_unset=True).items():
        attr = mapping.get(field, field)
        setattr(produit, attr, value)

    db.commit()
    db.refresh(produit)

    return {
        "id": produit.id,
        "nom": produit.nom,
        "prix": produit.prix,
        "stock": produit.stock,
        "categorie": produit.categorie,
        "est_disponible": produit.est_disponible,
        "est_promo": produit.est_promo,
        "prix_promo": produit.prix_promo,
        "image_url": produit.image_url,
        "note_moyenne": produit.note_moyenne,
        "nb_avis": produit.nb_avis,
    }


# ─── ✅ NOUVEAU : Upload image produit ────────────────────────────────────────
@router.post("/produits/{produit_id}/upload-image")
async def upload_image_produit(
    produit_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    """Upload une image pour un produit existant. Retourne la nouvelle image_url."""

    # 1. Vérifier que c'est bien une image
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image (jpg, png, webp, gif)")

    # 2. Lire le contenu et vérifier la taille (max 5 MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop grande (max 5 MB)")

    # 3. Vérifier l'extension
    filename_parts = (file.filename or "image.jpg").rsplit(".", 1)
    ext = filename_parts[-1].lower() if len(filename_parts) > 1 else "jpg"
    if ext not in ["jpg", "jpeg", "png", "webp", "gif"]:
        raise HTTPException(status_code=400, detail="Format non supporté. Utilisez jpg, png, webp ou gif")

    # 4. Générer un nom de fichier unique
    unique_filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)

    # 5. Vérifier que le produit existe
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    # 6. Supprimer l'ancienne image locale si elle existe
    if produit.image_url and produit.image_url.startswith("/static/"):
        old_path = produit.image_url.lstrip("/")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass  # Ne pas bloquer si la suppression échoue

    # 7. Sauvegarder le nouveau fichier
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(contents)

    # 8. Mettre à jour la base de données
    produit.image_url = f"/static/images/produits/{unique_filename}"
    db.commit()
    db.refresh(produit)

    return {
        "image_url": produit.image_url,
        "message": "Image uploadée avec succès ✅"
    }


# ─── Upload galerie img_yanda (3 images) ──────────────────────────────────────
@router.post("/produits/{produit_id}/upload-gallery")
async def upload_gallery_produit(
    produit_id: int,
    image1: Optional[UploadFile] = File(None),
    image2: Optional[UploadFile] = File(None),
    image3: Optional[UploadFile] = File(None),
    folder_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    """Upload jusqu'à 3 images dans img_yanda/{folder_name}/ (1.ext, 2.ext, 3.ext)."""
    from pathlib import Path

    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    # Déterminer le nom du dossier
    folder = (folder_name or produit.nom or f"produit_{produit_id}").strip()
    folder_path = Path("img_yanda") / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for idx, upload_file in enumerate([image1, image2, image3], start=1):
        if not upload_file:
            continue
        contents = await upload_file.read()
        if len(contents) > 8 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Image {idx} trop grande (max 8 MB)")

        filename = upload_file.filename or f"image.jpg"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        if ext not in ["jpg", "jpeg", "png", "webp", "avif", "gif", "bmp"]:
            ext = "jpg"

        dest = folder_path / f"{idx}.{ext}"
        dest.write_bytes(contents)
        uploaded.append(str(idx))

    if not uploaded:
        raise HTTPException(status_code=400, detail="Aucune image reçue")

    # Mettre à jour image_folder dans la DB
    produit.image_folder = folder
    db.commit()

    return {
        "message"     : f"{len(uploaded)} image(s) uploadée(s) dans img_yanda/{folder}/",
        "image_folder": folder,
        "images"      : [f"/img/{folder}/{i}" for i in uploaded],
    }


@router.delete("/produits/{produit_id}")
def delete_produit_admin(
    produit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    produit.est_disponible = False   # soft delete
    db.commit()
    return {"message": "Produit désactivé"}


# ─── Toggle promotion ─────────────────────────────────────────────────────────
@router.patch("/produits/{produit_id}/toggle-promo")
def toggle_promo_produit(
    produit_id: int,
    prix_promo: Optional[float] = Query(None, description="Prix promo en DH (optionnel)"),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    nouvel_etat = not produit.est_promo
    produit.est_promo = nouvel_etat

    if nouvel_etat:
        if prix_promo is not None:
            produit.prix_promo = prix_promo
        elif produit.prix:
            produit.prix_promo = round(produit.prix * 0.8, 2)
    else:
        produit.prix_promo = None

    db.commit()
    db.refresh(produit)

    return {
        "id": produit.id,
        "est_promo": produit.est_promo,
        "prix_promo": produit.prix_promo,
        "message": "Promotion activée ✅" if nouvel_etat else "Promotion désactivée ⛔"
    }


# ─── Toggle disponibilité ─────────────────────────────────────────────────────
@router.patch("/produits/{produit_id}/toggle-disponible")
def toggle_disponible_produit(
    produit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    produit = db.query(Produit).filter(Produit.id == produit_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    produit.est_disponible = not (produit.est_disponible if produit.est_disponible is not None else True)
    db.commit()
    db.refresh(produit)

    return {
        "id": produit.id,
        "est_disponible": produit.est_disponible,
        "message": "Produit disponible ✅" if produit.est_disponible else "Produit masqué ⛔"
    }