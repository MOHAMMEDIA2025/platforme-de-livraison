# app/routes/tracking.py — VERSION AMÉLIORÉE
# Envoie : statut + adresse + infos livreur + position GPS initiale au moment de la connexion

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.commande import Commande
from app.models.livreur import Livreur
from app.websocket.manager import manager
from app.core.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
import json

router = APIRouter(tags=["WebSocket Tracking"])


def get_user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


# ─── CLIENT : suit sa commande ───────────────────────────────────────────────
@router.websocket("/ws/commande/{commande_id}")
async def track_commande(
    websocket: WebSocket,
    commande_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        user = get_user_from_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande or str(commande.user_id) != user["sub"]:
        await websocket.close(code=1008)
        return

    await manager.connect_client(websocket, commande_id)

    # ── Construire les infos livreur si assigné ───────────────────────────────
    livreur_data = None
    if commande.livreur_id:
        livreur = db.query(Livreur).filter(Livreur.id == commande.livreur_id).first()
        if livreur:
            livreur_data = {
                "id":            livreur.id,
                "nom":           livreur.nom,
                "telephone":     livreur.telephone,
                "vehicule":      livreur.vehicule,
                "note_moyenne":  livreur.note_moyenne,
                "nb_livraisons": livreur.nb_livraisons,
            }

    # ── Envoyer état initial complet à la connexion ───────────────────────────
    await websocket.send_json({
        "type":        "statut",
        "statut":      commande.statut,
        "adresse":     commande.adresse,
        "commande_id": commande_id,
        "livreur":     livreur_data,
    })

    # ── Si livreur a déjà une position GPS → l'envoyer immédiatement ─────────
    if commande.livreur_id:
        livreur = db.query(Livreur).filter(Livreur.id == commande.livreur_id).first()
        if livreur and livreur.lat is not None and livreur.lng is not None:
            await websocket.send_json({
                "type":       "position",
                "lat":        livreur.lat,
                "lng":        livreur.lng,
                "livreur_id": livreur.id,
            })

    try:
        while True:
            data = await websocket.receive_text()
            # On ignore les messages (ping, etc.)
    except WebSocketDisconnect:
        manager.disconnect_client(websocket, commande_id)


# ─── LIVREUR : envoie sa position GPS ────────────────────────────────────────
@router.websocket("/ws/livreur/{livreur_id}")
async def livreur_position(
    websocket: WebSocket,
    livreur_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    try:
        user = get_user_from_token(token)
        if user["role"] != "livreur":
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect_livreur(websocket, livreur_id)

    try:
        while True:
            raw = await websocket.receive_text()

            if not raw or not raw.strip():
                continue

            if raw.strip().lower() == "ping":
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # data = { "lat": 32.123, "lng": -6.456, "commande_id": 5 }
            commande_id = data.get("commande_id")
            lat = data.get("lat")
            lng = data.get("lng")

            if commande_id and lat is not None and lng is not None:
                # ── Mettre à jour la position en base ────────────────────────
                livreur = db.query(Livreur).filter(Livreur.id == livreur_id).first()
                if livreur:
                    livreur.lat = lat
                    livreur.lng = lng
                    db.commit()

                # ── Broadcast aux clients qui suivent cette commande ─────────
                await manager.broadcast_to_commande(commande_id, {
                    "type":       "position",
                    "lat":        lat,
                    "lng":        lng,
                    "livreur_id": livreur_id,
                })

    except WebSocketDisconnect:
        manager.disconnect_livreur(livreur_id)


# ─── REST : changer le statut + broadcast WebSocket ──────────────────────────
@router.put("/commandes/{commande_id}/statut")
async def update_statut(
    commande_id: int,
    statut: str,
    db: Session = Depends(get_db)
):
    STATUTS_VALIDES = ["pending", "en_preparation", "en_route", "livre", "annule"]
    if statut not in STATUTS_VALIDES:
        raise HTTPException(status_code=400, detail="Statut invalide")

    commande = db.query(Commande).filter(Commande.id == commande_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    commande.statut = statut
    db.commit()

    # ── Construire infos livreur pour le broadcast ────────────────────────────
    livreur_data = None
    if commande.livreur_id:
        livreur = db.query(Livreur).filter(Livreur.id == commande.livreur_id).first()
        if livreur:
            livreur_data = {
                "id":            livreur.id,
                "nom":           livreur.nom,
                "telephone":     livreur.telephone,
                "vehicule":      livreur.vehicule,
                "note_moyenne":  livreur.note_moyenne,
                "nb_livraisons": livreur.nb_livraisons,
            }

    # ── Broadcast statut + infos livreur ─────────────────────────────────────
    await manager.broadcast_to_commande(commande_id, {
        "type":        "statut",
        "statut":      statut,
        "adresse":     commande.adresse,
        "commande_id": commande_id,
        "livreur":     livreur_data,
    })

    return {"ok": True, "statut": statut}