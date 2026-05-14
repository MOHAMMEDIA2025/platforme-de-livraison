# app/routes/commande.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.core.dependencies import get_current_user, admin_only, livreur_only
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.produit import Produit
from app.models.panier import PanierItem
from app.models.livreur import Livreur
from app.models.notification import Notification
from app.models.user import User
from app.models.promotion import Promotion
from app.models.commande_catalogue import CommandeCatalogue, LigneCommandeCatalogue
from app.models.livraison_detail import LivraisonDetail
from app.models.paiement import Paiement
from app.models.fidelite import PointFidelite, TransactionPoints   # ← AJOUT
from app.schemas.schemas import CommandeCreate

router = APIRouter(prefix="/commandes", tags=["Commandes"])

STATUTS_VALIDES = ["pending", "en_preparation", "en_route", "livre", "annule"]
FRAIS_LIVRAISON = 15.0
COMMISSION_RATE = 0.10
POINTS_PAR_DH   = 1   # cohérent avec app/routes/fidelite.py


# ── Helpers fidélité ──────────────────────────────────────────────────────────

def _get_niveau(points: int) -> dict:
    NIVEAUX = [
        {"nom": "Bronze",  "min": 0},
        {"nom": "Argent",  "min": 500},
        {"nom": "Or",      "min": 1500},
        {"nom": "Platine", "min": 5000},
    ]
    niveau_actuel = NIVEAUX[0]
    for n in NIVEAUX:
        if points >= n["min"]:
            niveau_actuel = n
    return niveau_actuel


def _crediter_points(db: Session, user_id: int, commande_id: int, total: float):
    """Crédite les points de fidélité après livraison. Idempotent."""
    # Vérifier qu'on n'a pas déjà crédité cette commande
    existant = db.query(TransactionPoints).filter(
        TransactionPoints.commande_id == commande_id,
        TransactionPoints.type == "gain"
    ).first()
    if existant:
        return  # déjà crédité, on ne fait rien

    points_gagnes = int(total * POINTS_PAR_DH)
    if points_gagnes <= 0:
        return

    # Récupérer ou créer le solde fidélité du client
    fidelite = db.query(PointFidelite).filter(PointFidelite.user_id == user_id).first()
    if not fidelite:
        fidelite = PointFidelite(user_id=user_id, points=0, niveau="Bronze")
        db.add(fidelite)
        db.flush()

    fidelite.points += points_gagnes
    fidelite.niveau = _get_niveau(fidelite.points)["nom"]

    transaction = TransactionPoints(
        user_id=user_id,
        commande_id=commande_id,
        delta=points_gagnes,
        type="gain",
        description=f"Commande #{commande_id} — {total} DH"
    )
    db.add(transaction)

    # Notification au client
    notif = Notification(
        user_id=user_id,
        titre="Points fidélité crédités ⭐",
        message=f"+{points_gagnes} points ajoutés à votre compte fidélité (commande #{commande_id}). Total : {fidelite.points} pts.",
        type="success",
        icon="⭐",
        lien="/fidelite"
    )
    db.add(notif)


# ── CLIENT : récupérer ses propres commandes ──────────────────────────────────
@router.get("/me")
def get_mes_commandes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])

    commandes = (
        db.query(Commande)
        .filter(Commande.user_id == user_id)
        .order_by(Commande.created_at.desc())
        .all()
    )

    result = []
    for cmd in commandes:
        lignes = db.query(LigneCommande).filter(LigneCommande.commande_id == cmd.id).all()

        paiement = db.query(Paiement).filter(Paiement.commande_id == cmd.id).first()
        statut_paiement = paiement.statut if paiement else "en_attente"

        result.append({
            "id": cmd.id,
            "statut": cmd.statut,
            "adresse": cmd.adresse,
            "total": cmd.total,
            "frais_livraison": cmd.frais_livraison,
            "reduction": cmd.reduction,
            "code_promo": cmd.code_promo,
            "note_client": cmd.note_client,
            "is_rated": cmd.is_rated,
            "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
            "paiement": statut_paiement,
            "nb_articles": sum(l.quantite for l in lignes),
            "lignes": [
                {
                    "produit": l.nom_produit,
                    "quantite": l.quantite,
                    "prix_unitaire": l.prix_unitaire,
                }
                for l in lignes
            ],
        })

    return result


# ── LIVREUR : récupérer ses commandes assignées ───────────────────────────────
@router.get("/livreur/mes-livraisons")
def mes_livraisons_livreur(
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    user_id = int(current_user["sub"])

    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()
    if not livreur:
        raise HTTPException(status_code=404, detail="Profil livreur introuvable")

    commandes = (
        db.query(Commande)
        .filter(Commande.livreur_id == user_id)
        .order_by(Commande.created_at.desc())
        .limit(50)
        .all()
    )

    result = []
    for cmd in commandes:
        lignes = db.query(LigneCommande).filter(LigneCommande.commande_id == cmd.id).all()
        client = db.query(User).filter(User.id == cmd.user_id).first()

        result.append({
            "id": cmd.id,
            "statut": cmd.statut,
            "adresse": cmd.adresse,
            "total": cmd.total,
            "frais_livraison": cmd.frais_livraison,
            "reduction": cmd.reduction,
            "note_client": cmd.note_client,
            "is_rated": cmd.is_rated,
            "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
            "updated_at": cmd.updated_at.isoformat() if cmd.updated_at else None,
            "gains": round((cmd.total or 0) * COMMISSION_RATE, 2),
            "client_nom": client.nom if client else "—",
            "client_tel": client.telephone if client else "—",
            "nb_articles": sum(l.quantite for l in lignes),
            "lignes": [
                {
                    "produit": l.nom_produit or f"Produit #{l.produit_id}",
                    "quantite": l.quantite,
                    "prix_unitaire": l.prix_unitaire or 0,
                }
                for l in lignes
            ],
        })

    return result


# ── LIVREUR : mettre à jour le statut d'une commande ─────────────────────────
@router.patch("/{commande_id}/statut-livreur")
def update_statut_livreur(
    commande_id: int,
    statut: str,
    db: Session = Depends(get_db),
    current_user=Depends(livreur_only)
):
    """
    Permet au livreur de faire avancer le statut d'une commande qui lui est assignée.
    Transitions autorisées :
      en_preparation → en_route
      en_route       → livre
    """
    user_id = int(current_user["sub"])

    STATUTS_LIVREUR_AUTORISES = ["en_route", "livre"]
    if statut not in STATUTS_LIVREUR_AUTORISES:
        raise HTTPException(
            status_code=400,
            detail=f"Statut invalide. Valeurs autorisées pour un livreur : {STATUTS_LIVREUR_AUTORISES}"
        )

    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.livreur_id == user_id
    ).first()

    if not commande:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable ou non assignée à ce livreur"
        )

    if statut == "en_route" and commande.statut != "en_preparation":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de passer en 'en_route' depuis le statut '{commande.statut}'"
        )

    if statut == "livre" and commande.statut != "en_route":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de marquer 'livré' depuis le statut '{commande.statut}'"
        )

    commande.statut = statut
    commande.updated_at = datetime.utcnow()

    livreur = db.query(Livreur).filter(Livreur.id == user_id).first()

    # ── Quand la commande est livrée ─────────────────────────────────────────
    if statut == "livre":
        # Libérer le livreur et incrémenter ses stats
        if livreur:
            livreur.statut = "disponible"
            livreur.nb_livraisons = (livreur.nb_livraisons or 0) + 1

        # Synchroniser livraisons_detail
        try:
            client = db.query(User).filter(User.id == commande.user_id).first()
            nom_client = (client.nom or "").strip() if client else f"Client #{commande.user_id}"
            livraison = db.query(LivraisonDetail).filter(
                LivraisonDetail.localisation_client == commande.adresse,
                LivraisonDetail.nom_client == nom_client,
            ).order_by(LivraisonDetail.id_livraison.desc()).first()

            if livraison:
                livraison.statut = "Livré"
                livraison.date_livraison = datetime.utcnow()
                if livreur:
                    livraison.nom_livreur = livreur.nom
        except Exception as e:
            print(f"[WARN] Synchro livraisons_detail (statut-livreur livre) : {e}")

        # ── Créditer les points de fidélité ──────────────────────────────────
        try:
            _crediter_points(db, commande.user_id, commande_id, commande.total or 0)
        except Exception as e:
            print(f"[WARN] Crédit points fidélité commande #{commande_id} : {e}")

        # ── Mettre à jour profil ML client ────────────────────────────────────
        try:
            from app.models.ml_data import ProfilClient
            from app.models.commande_item import LigneCommande as LC
            from sqlalchemy import func, text as sql_text

            commandes_livrees = db.query(Commande).filter(
                Commande.user_id == commande.user_id,
                Commande.statut == "livre"
            ).order_by(Commande.created_at.desc()).all()

            nb_cmd    = len(commandes_livrees)
            montant_t = sum(c.total or 0 for c in commandes_livrees)
            nb_prod   = db.query(func.sum(LC.quantite)).join(
                Commande, LC.commande_id == Commande.id
            ).filter(
                Commande.user_id == commande.user_id,
                Commande.statut == "livre"
            ).scalar() or 0

            jours = 0  # vient de livrer, donc 0 jour

            # Catégorie dominante
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
                "nb_commandes": nb_cmd,
                "montant_total": round(float(montant_t), 2),
                "nb_produits": int(nb_prod),
                "jours_depuis_derniere": jours,
                "categorie_dominante_fr": cat_dom,
                "scat_dominante_fr": scat_dom,
                "derniere_livraison_statut": "livre",
                "methode_paiement": methode_str,
                "mis_a_jour_le": datetime.utcnow(),
            }

            if profil_ml:
                for k, v in data_ml.items():
                    setattr(profil_ml, k, v)
            else:
                profil_ml = ProfilClient(client_id=commande.user_id, **data_ml)
                db.add(profil_ml)

            db.commit()
            print(f"[INFO] profil_client mis à jour pour user #{commande.user_id}")
        except Exception as e:
            db.rollback()
            print(f"[WARN] Échec profil_client : {e}")

        # Notification client : livraison confirmée
        notif = Notification(
            user_id=commande.user_id,
            titre="Commande livrée ✅",
            message=f"Votre commande #{commande_id} a été livrée avec succès. Bon appétit !",
            type="success",
            icon="✅",
            lien=f"/mes-commandes"
        )
        db.add(notif)

    # ── Quand le livreur démarre la livraison ─────────────────────────────────
    if statut == "en_route":
        notif = Notification(
            user_id=commande.user_id,
            titre="Livreur en route 🛵",
            message=f"Votre commande #{commande_id} est en route vers vous !",
            type="info",
            icon="🛵",
            lien=f"/tracking/{commande_id}"
        )
        db.add(notif)

    db.commit()

    return {
        "message": f"Statut de la commande #{commande_id} mis à jour : {statut}",
        "commande_id": commande_id,
        "statut": statut,
        "gains": round((commande.total or 0) * COMMISSION_RATE, 2) if statut == "livre" else None,
    }


# ── CLIENT : annuler une commande en attente ──────────────────────────────────
@router.patch("/{commande_id}/annuler")
def annuler_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    commande = db.query(Commande).filter(
        Commande.id == commande_id,
        Commande.user_id == user_id
    ).first()

    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if commande.statut != "pending":
        raise HTTPException(status_code=400, detail="Seules les commandes en attente peuvent être annulées")

    commande.statut = "annule"
    db.commit()
    return {"message": f"Commande #{commande_id} annulée"}


# ── CLIENT : passer une commande depuis le panier ─────────────────────────────
@router.post("/from-panier")
def commander(
    data: CommandeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    panier_items = db.query(PanierItem).filter(PanierItem.user_id == user_id).all()

    if not panier_items:
        raise HTTPException(status_code=400, detail="Votre panier est vide")

    # ── Calculer le sous-total articles ──────────────────────────────────────
    sous_total = 0.0
    for item in panier_items:
        produit = db.query(Produit).filter(Produit.id == item.produit_id).first()
        if not produit:
            raise HTTPException(status_code=400, detail=f"Produit ID {item.produit_id} introuvable")
        if produit.stock < item.quantite:
            raise HTTPException(status_code=400, detail=f"Stock insuffisant pour {produit.nom}")
        prix = produit.prix_promo if produit.est_promo and produit.prix_promo else produit.prix
        sous_total += prix * item.quantite

    # ── Validation et calcul du code promo ───────────────────────────────────
    montant_pour_promo = round(sous_total + FRAIS_LIVRAISON, 2)

    reduction = 0.0
    code_promo_applique = None

    if data.code_promo:
        promo = db.query(Promotion).filter(
            Promotion.code == data.code_promo.strip().upper()
        ).first()

        if not promo:
            raise HTTPException(status_code=400, detail="Code promo inconnu")
        if not promo.est_active:
            raise HTTPException(status_code=400, detail="Code promo désactivé")
        if promo.est_expiree():
            raise HTTPException(status_code=400, detail="Code promo expiré")
        if promo.usage_max is not None and promo.usage_count >= promo.usage_max:
            raise HTTPException(status_code=400, detail="Quota d'utilisations atteint")
        if montant_pour_promo < promo.minimum_commande:
            raise HTTPException(
                status_code=400,
                detail=f"Montant minimum requis : {promo.minimum_commande} DH"
            )

        if promo.type == "pourcentage":
            reduction = round(montant_pour_promo * promo.valeur / 100, 2)
        elif promo.type == "montant_fixe":
            reduction = round(min(promo.valeur, montant_pour_promo), 2)
        elif promo.type == "livraison_gratuite":
            reduction = FRAIS_LIVRAISON
        else:
            reduction = 0.0

        code_promo_applique = promo.code
        promo.usage_count += 1

    # ── Créer la commande ─────────────────────────────────────────────────────
    commande = Commande(
        user_id=user_id,
        adresse=data.adresse,
        note_client=data.note_client,
        code_promo=code_promo_applique,
        reduction=reduction,
        frais_livraison=FRAIS_LIVRAISON
    )
    db.add(commande)
    db.commit()
    db.refresh(commande)

    # ── Créer les lignes et décrémenter le stock ──────────────────────────────
    total_articles = 0.0
    lignes_creees = []

    for item in panier_items:
        produit = db.query(Produit).filter(Produit.id == item.produit_id).first()
        prix = produit.prix_promo if produit.est_promo and produit.prix_promo else produit.prix
        produit.stock -= item.quantite

        ligne = LigneCommande(
            commande_id=commande.id,
            produit_id=produit.id,
            quantite=item.quantite,
            prix_unitaire=prix,
            nom_produit=produit.nom
        )
        db.add(ligne)
        total_articles += prix * item.quantite
        lignes_creees.append((ligne, produit))

    commande.total = round(total_articles + FRAIS_LIVRAISON - reduction, 2)

    db.query(PanierItem).filter(PanierItem.user_id == user_id).delete()
    db.commit()
    db.refresh(commande)

    # ── Notification de confirmation ──────────────────────────────────────────
    msg_notif = f"Commande #{commande.id} confirmée. Total : {commande.total} DH"
    if reduction > 0:
        msg_notif += f" (réduction appliquée : -{reduction} DH 🎉)"

    notif = Notification(
        user_id=user_id,
        titre="Commande confirmée 🎉",
        message=msg_notif,
        type="success",
        icon="📦",
        lien=f"/tracking/{commande.id}"
    )
    db.add(notif)
    db.commit()

    # ── Récupérer le nom du client ────────────────────────────────────────────
    user = db.query(User).filter(User.id == user_id).first()
    nom_client = (user.nom or "").strip() if user else ""
    if not nom_client:
        nom_client = f"Client #{user_id}"

    # ── Snapshot des données AVANT tout commit supplémentaire ────────────────
    # On capture toutes les valeurs nécessaires pendant que les objets sont encore
    # accessibles, pour éviter tout problème de lazy-load après commit.
    montant_avant = total_articles + FRAIS_LIVRAISON
    remise_ratio  = round(reduction / montant_avant, 4) if montant_avant > 0 and reduction > 0 else 0.0

    snapshot_lignes = []
    cat_groups: dict = {}  # pour sessions_achat

    for ligne, produit in lignes_creees:
        # Forcer le rechargement des attributs depuis la DB (évite DetachedInstanceError)
        db.refresh(ligne)
        db.refresh(produit)

        prix_u     = float(ligne.prix_unitaire or produit.prix or 0.0)
        qte        = int(ligne.quantite or 1)
        prix_avant = round(float(produit.prix or 0.0) * qte, 2)
        prix_apres = round(prix_avant * (1.0 - remise_ratio), 2)

        snapshot_lignes.append({
            "produit_fr":   produit.nom or "Produit inconnu",
            "produit_en":   produit.nom_eng or produit.nom or "Unknown",
            "categorie_fr": produit.categorie or "Général",
            "categorie_en": produit.categorie_eng or produit.categorie or "General",
            "scat_fr":      produit.category_plus or produit.categorie or "Général",
            "scat_en":      produit.category_plus_eng or produit.categorie_eng or "General",
            "prix_u":       prix_u,
            "qte":          qte,
            "prix_avant":   prix_avant,
            "prix_apres":   prix_apres,
        })

        # Grouper par catégorie pour sessions_achat (avec EN)
        cat_fr  = produit.categorie or "Général"
        cat_en  = produit.categorie_eng or ""
        scat_fr = produit.category_plus or cat_fr
        scat_en = produit.category_plus_eng or cat_en
        key = (cat_fr, cat_en, scat_fr, scat_en)
        if key not in cat_groups:
            cat_groups[key] = {"nb": 0, "montant": 0.0}
        cat_groups[key]["nb"]      += qte
        cat_groups[key]["montant"] += prix_u * qte

    # ── Alimenter commandes_catalogue ─────────────────────────────────────────
    try:
        commande_cat = CommandeCatalogue(
            nom_client=nom_client,
            date_commande=commande.created_at or datetime.utcnow(),
            code_promo=commande.code_promo,
            remise_appliquee=remise_ratio,   # ex: 0.15 = 15%
        )
        db.add(commande_cat)
        db.flush()   # obtenir commande_cat.id avant d'insérer les lignes

        for snap in snapshot_lignes:
            db.add(LigneCommandeCatalogue(
                commande_id           = commande_cat.id,
                produit_achete_fr     = snap["produit_fr"],
                produit_achete_en     = snap["produit_en"],
                categorie_fr          = snap["categorie_fr"],
                categorie_en          = snap["categorie_en"],
                sous_categorie_fr     = snap["scat_fr"],
                sous_categorie_en     = snap["scat_en"],
                prix_unitaire         = snap["prix_u"],
                quantite              = snap["qte"],
                prix_ligne_avant_promo= snap["prix_avant"],
                prix_ligne_apres_promo= snap["prix_apres"],
            ))

        db.commit()
        print(f"[ML] commandes_catalogue #{commande_cat.id} ← commande #{commande.id} "
              f"| {len(snapshot_lignes)} ligne(s) | remise={remise_ratio*100:.1f}%")

    except Exception as e:
        db.rollback()
        print(f"[ERREUR] commandes_catalogue : {e}")

    # ── Alimenter sessions_achat ──────────────────────────────────────────────
    try:
        from app.models.ml_data import SessionAchat as SA
        for (cat_fr, cat_en, scat_fr, scat_en), vals in cat_groups.items():
            db.add(SA(
                client_nom        = nom_client,
                categorie_fr      = cat_fr,
                sous_categorie_fr = scat_fr,
                categorie_en      = cat_en,
                sous_categorie_en = scat_en or None,
                nb_achats         = vals["nb"],
                montant_total     = round(vals["montant"], 2),
                temps_secondes    = 0,  # temps de navigation non disponible ici
            ))
        db.commit()
        print(f"[ML] sessions_achat : {len(cat_groups)} catégorie(s) pour commande #{commande.id}")
    except Exception as e:
        db.rollback()
        print(f"[ERREUR] sessions_achat : {e}")

    # ── Alimenter livraisons_detail ───────────────────────────────────────────
    try:
        produits_str = ", ".join(
            f"{produit.nom or 'Produit'} (x{ligne.quantite})"
            for ligne, produit in lignes_creees
        )
        quantite_totale = sum(ligne.quantite for ligne, _ in lignes_creees)

        methode_raw = (getattr(data, "methode_paiement", None) or "cash").strip().lower()
        methode_map = {
            "stripe":     "Carte Visa",
            "card":       "Carte Visa",
            "visa":       "Carte Visa",
            "mastercard": "Carte Mastercard",
            "cash":       "Paiement à la livraison",
            "virement":   "Virement bancaire (RIB)",
        }
        methode_paiement = methode_map.get(methode_raw, "Paiement à la livraison")

        livraison_detail = LivraisonDetail(
            nom_client=nom_client,
            nom_livreur="Non assigné",
            date_livraison=datetime.utcnow(),
            produits=produits_str,
            quantite_totale=quantite_totale,
            prix_total_livraison=commande.total,
            methode_paiement=methode_paiement,
            localisation_client=commande.adresse,
            localisation_livreur="Entrepôt Central",
            notes_client=commande.note_client,
            statut="En attente",
        )
        db.add(livraison_detail)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[WARN] Échec insertion livraisons_detail : {e}")

    return {
        "id": commande.id,
        "total": commande.total,
        "statut": commande.statut,
        "adresse": commande.adresse,
        "frais_livraison": commande.frais_livraison,
        "reduction": commande.reduction,
        "code_promo": commande.code_promo,
        "message": "Commande créée avec succès !"
    }