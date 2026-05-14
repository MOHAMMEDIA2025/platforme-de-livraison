from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import admin_only, livreur_only, get_current_user
from app.models.livreur import Livreur
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.user import User
from app.models.notification import Notification
from app.models.avis import Avis
from app.models.livraison_detail import LivraisonDetail   # ✅ AJOUT pour synchro nom_livreur
from datetime import datetime, timedelta

router = APIRouter(prefix="/livreurs", tags=["Livreurs"])

COMMISSION_RATE = 0.10       # 10% du total de la commande = gain livreur


# ── ADMIN : liste tous les livreurs ──────────────────────────────────────────
@router.get("/")
def get_livreurs(db: Session = Depends(get_db), current_user=Depends(admin_only)):
    livreurs = db.query(Livreur).all()
    result = []
    for l in livreurs:
        nb_commandes = db.query(Commande).filter(Commande.livreur_id == l.id).count()
        result.append({
            "id": l.id,
            "nom": l.nom,
            "telephone": l.telephone,
            "statut": l.statut,
            "vehicule": l.vehicule,
            "zone": l.zone,
            "note_moyenne": l.note_moyenne,
            "nb_livraisons": l.nb_livraisons,
            "is_online": l.is_online,
            "nb_commandes_total": nb_commandes,
        })
    return result


# ── ADMIN : livreurs disponibles ─────────────────────────────────────────────
@router.get("/disponibles")
def get_livreurs_disponibles(db: Session = Depends(get_db), current_user=Depends(admin_only)):
    livreurs = db.query(Livreur).filter(
        Livreur.statut == "disponible",
        Livreur.is_online == True
    ).all()
    return [{"id": l.id, "nom": l.nom, "telephone": l.telephone, "vehicule": l.vehicule} for l in livreurs]


# ── LIVREUR : commandes disponibles à prendre ────────────────────────────────
@router.get("/commandes-disponibles")
def commandes_disponibles(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Profil livreur introuvable")
    if not livreur.is_online:
        raise HTTPException(status_code=403, detail="Vous devez être en ligne pour voir les commandes disponibles")

    commandes = db.query(Commande).filter(
        Commande.statut == "en_preparation",
        Commande.livreur_id == None
    ).order_by(Commande.created_at.asc()).all()

    result = []
    for cmd in commandes:
        client = db.query(User).filter(User.id == cmd.user_id).first()
        lignes = db.query(LigneCommande).filter(LigneCommande.commande_id == cmd.id).all()
        result.append({
            "id": cmd.id,
            "adresse": cmd.adresse,
            "total": cmd.total,
            "frais_livraison": cmd.frais_livraison,
            "note_client": cmd.note_client,
            "nb_articles": sum(l.quantite for l in lignes),
            "client_nom": client.nom if client else "—",
            "client_tel": client.telephone if client else "—",
            "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
            "lignes": [
                {
                    "produit": l.nom_produit or f"Produit #{l.produit_id}",
                    "quantite": l.quantite,
                    "prix_unitaire": l.prix_unitaire or 0,
                }
                for l in lignes
            ]
        })
    return result


# ── LIVREUR : accepter une commande ──────────────────────────────────────────
@router.post("/commandes-disponibles/{commande_id}/accepter")
def accepter_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Profil livreur introuvable")
    if livreur.statut != "disponible":
        raise HTTPException(status_code=400, detail=f"Vous n'êtes pas disponible (statut: {livreur.statut})")

    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.statut == "en_preparation",
        Commande.livreur_id == None
    ).first()

    if not commande:
        raise HTTPException(
            status_code=404,
            detail="Cette commande n'est plus disponible (déjà prise ou introuvable)"
        )

    commande.livreur_id = user_id
    commande.statut = "en_route"
    livreur.statut = "occupé"
    db.commit()

    # ✅ BUG #2 CORRIGÉ : mettre à jour nom_livreur dans livraisons_detail
    # Recherche par adresse + nom_client (même logique que admin assigner-livreur)
    try:
        client = db.query(User).filter(User.id == commande.user_id).first()
        nom_client = (client.nom or "").strip() if client else ""
        if not nom_client:
            nom_client = f"Client #{commande.user_id}"

        livraison = db.query(LivraisonDetail).filter(
            LivraisonDetail.localisation_client == commande.adresse,
            LivraisonDetail.nom_client == nom_client,
        ).order_by(LivraisonDetail.id_livraison.desc()).first()

        if livraison:
            livraison.nom_livreur = livreur.nom
            livraison.statut = "En cours"
            db.commit()
    except Exception as e:
        # Ne pas bloquer l'acceptation si la synchro échoue
        print(f"[WARN] Synchro livraisons_detail (accepter_commande) : {e}")

    notif = Notification(
        user_id=commande.user_id,
        titre="Livreur en route 🛵",
        message=f"Votre commande #{commande_id} a été prise en charge par {livreur.nom} et est en route !",
        type="success",
        icon="🛵",
        lien=f"/tracking/{commande_id}"
    )
    db.add(notif)
    db.commit()

    return {
        "message": f"Commande #{commande_id} acceptée. Bonne livraison !",
        "commande_id": commande_id,
        "statut": commande.statut,
    }


# ── LIVREUR : voir son propre profil ─────────────────────────────────────────
@router.get("/mon-profil")
def mon_profil_livreur(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])
    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Profil livreur introuvable")

    commandes_livrees = db.query(Commande).filter(
        Commande.livreur_id == user_id,
        Commande.statut == "livre"
    ).count()

    commandes_obj = db.query(Commande).filter(
        Commande.livreur_id == user_id,
        Commande.statut == "livre"
    ).all()

    ca_total = sum(c.total for c in commandes_obj)
    gains_total = round(ca_total * COMMISSION_RATE, 2)

    return {
        "id": livreur.id,
        "nom": livreur.nom,
        "telephone": livreur.telephone,
        "statut": livreur.statut,
        "vehicule": livreur.vehicule,
        "zone": livreur.zone,
        "note_moyenne": livreur.note_moyenne,
        "nb_livraisons": livreur.nb_livraisons,
        "is_online": livreur.is_online,
        "commandes_livrees": commandes_livrees,
        "ca_total": round(ca_total, 2),
        "gains_total": gains_total,
    }


# ── LIVREUR : toggle en ligne / hors ligne ────────────────────────────────────
@router.patch("/toggle-online")
def toggle_online(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])
    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    livreur.is_online = not livreur.is_online
    if not livreur.is_online:
        livreur.statut = "hors_ligne"
    elif livreur.statut == "hors_ligne":
        livreur.statut = "disponible"

    db.commit()
    return {
        "is_online": livreur.is_online,
        "statut": livreur.statut,
        "message": "En ligne ✅" if livreur.is_online else "Hors ligne 🔴"
    }


# ── LIVREUR : mettre à jour sa position GPS ───────────────────────────────────
@router.patch("/position")
def update_position(
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])
    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    livreur.lat = lat
    livreur.lng = lng
    db.commit()
    return {"lat": lat, "lng": lng}


# ── LIVREUR : mettre à jour son profil ───────────────────────────────────────
@router.put("/mon-profil")
def update_profil_livreur(
    nom: str = None,
    telephone: str = None,
    vehicule: str = None,
    zone: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])
    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    if nom:        livreur.nom = nom
    if telephone:  livreur.telephone = telephone
    if vehicule:   livreur.vehicule = vehicule
    if zone:       livreur.zone = zone

    db.commit()
    db.refresh(livreur)
    return {"message": "Profil mis à jour"}


# ── LIVREUR : gains journaliers sur 30 jours ─────────────────────────────────
@router.get("/mes-gains")
def mes_gains(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    result = []
    total_gains = 0.0
    total_livraisons = 0

    for i in range(29, -1, -1):
        jour = datetime.utcnow().date() - timedelta(days=i)
        debut = datetime.combine(jour, datetime.min.time())
        fin   = debut + timedelta(days=1)

        commandes_du_jour = db.query(Commande).filter(
            Commande.livreur_id == user_id,
            Commande.statut == "livre",
            Commande.created_at >= debut,
            Commande.created_at < fin
        ).all()

        ca_jour = sum(c.total for c in commandes_du_jour)
        gains_jour = round(ca_jour * COMMISSION_RATE, 2)
        nb_jour = len(commandes_du_jour)

        total_gains += gains_jour
        total_livraisons += nb_jour

        result.append({
            "jour": jour.strftime("%d/%m"),
            "date": jour.isoformat(),
            "nb_livraisons": nb_jour,
            "ca": round(ca_jour, 2),
            "gains": gains_jour,
        })

    return {
        "jours": result,
        "total_gains": round(total_gains, 2),
        "total_livraisons": total_livraisons,
        "commission_rate": COMMISSION_RATE,
    }


# ── LIVREUR : historique des livraisons effectuées ───────────────────────────
@router.get("/historique")
def mon_historique(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    commandes = db.query(Commande).filter(
        Commande.livreur_id == user_id,
        Commande.statut == "livre"
    ).order_by(Commande.created_at.desc()).all()

    result = []
    for cmd in commandes:
        lignes = db.query(LigneCommande).filter(LigneCommande.commande_id == cmd.id).all()
        result.append({
            "id": cmd.id,
            "adresse": cmd.adresse,
            "total": cmd.total,
            "gains": round((cmd.total or 0) * COMMISSION_RATE, 2),
            "nb_articles": sum(l.quantite for l in lignes),
            "note_livreur": cmd.note_livreur,
            "commentaire": cmd.commentaire,
            "livree_le": cmd.updated_at.isoformat() if cmd.updated_at else None,
        })

    return {"livraisons": result}


# ── LIVREUR : ses avis reçus ─────────────────────────────────────────────────
@router.get("/mes-avis")
def mes_avis(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    avis_list = db.query(Avis).filter(
        Avis.livreur_id == user_id,
        Avis.est_valide == True
    ).order_by(Avis.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "note": a.note_livreur,
            "commentaire": a.commentaire,
            "date": a.created_at.isoformat() if a.created_at else None,
        }
        for a in avis_list
    ]


# ── ADMIN : supprimer un livreur ──────────────────────────────────────────────
@router.delete("/{livreur_id}")
def delete_livreur(
    livreur_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    livreur = db.query(Livreur).filter(Livreur.id == livreur_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Livreur introuvable")

    user = db.query(User).filter(User.id == livreur_id).first()
    if user:
        user.role = "client"

    db.delete(livreur)
    db.commit()
    return {"message": "Livreur supprimé"}