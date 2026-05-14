"""
app/routes/support.py
Chat de support client ↔ admin
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.database import get_db
from app.core.dependencies import get_current_user, admin_only
from app.models.support import MessageSupport
from app.models.user import User
from app.models.notification import Notification

router = APIRouter(prefix="/support", tags=["Support"])


class MessageCreate(BaseModel):
    contenu: str


# ── CLIENT : envoyer un message ──────────────────────────────────────────────
@router.post("/")
def envoyer_message(
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    msg = MessageSupport(
        user_id=user_id,
        contenu=data.contenu,
        est_admin=False
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message": "Message envoyé ✅", "id": msg.id}


# ── CLIENT : voir sa conversation ────────────────────────────────────────────
@router.get("/ma-conversation")
def ma_conversation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    messages = db.query(MessageSupport).filter(
        MessageSupport.user_id == user_id
    ).order_by(MessageSupport.created_at.asc()).all()

    # Marquer les messages admin comme lus
    for m in messages:
        if m.est_admin and not m.est_lu:
            m.est_lu = True
    db.commit()

    return [
        {
            "id": m.id,
            "contenu": m.contenu,
            "est_admin": m.est_admin,
            "est_lu": m.est_lu,
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]


# ── CLIENT : nb messages non lus (admin → client) ────────────────────────────
@router.get("/nb-non-lus")
def nb_non_lus(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    count = db.query(MessageSupport).filter(
        MessageSupport.user_id == user_id,
        MessageSupport.est_admin == True,
        MessageSupport.est_lu == False
    ).count()
    return {"nb": count}


# ── ADMIN : voir toutes les conversations ─────────────────────────────────────
@router.get("/admin/conversations")
def toutes_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    # Grouper par user
    users_avec_msgs = db.query(MessageSupport.user_id).distinct().all()
    result = []
    for (uid,) in users_avec_msgs:
        user = db.query(User).filter(User.id == uid).first()
        dernier_msg = db.query(MessageSupport).filter(
            MessageSupport.user_id == uid
        ).order_by(MessageSupport.created_at.desc()).first()

        nb_non_lu = db.query(MessageSupport).filter(
            MessageSupport.user_id == uid,
            MessageSupport.est_admin == False,
            MessageSupport.est_lu == False
        ).count()

        result.append({
            "user_id": uid,
            "nom": user.nom if user else "—",
            "email": user.email if user else "—",
            "dernier_message": dernier_msg.contenu if dernier_msg else "",
            "derniere_activite": dernier_msg.created_at.isoformat() if dernier_msg else "",
            "nb_non_lu": nb_non_lu
        })

    result.sort(key=lambda x: x["derniere_activite"], reverse=True)
    return result


# ── ADMIN : voir + répondre à une conversation ───────────────────────────────
@router.get("/admin/conversation/{user_id}")
def conversation_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    messages = db.query(MessageSupport).filter(
        MessageSupport.user_id == user_id
    ).order_by(MessageSupport.created_at.asc()).all()

    # Marquer les messages client comme lus
    for m in messages:
        if not m.est_admin and not m.est_lu:
            m.est_lu = True
    db.commit()

    return [
        {
            "id": m.id,
            "contenu": m.contenu,
            "est_admin": m.est_admin,
            "est_lu": m.est_lu,
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]


@router.post("/admin/repondre/{user_id}")
def repondre_client(
    user_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only)
):
    msg = MessageSupport(
        user_id=user_id,
        contenu=data.contenu,
        est_admin=True
    )
    db.add(msg)

    # Notifier le client
    notif = Notification(
        user_id=user_id,
        titre="Réponse du support 💬",
        message="L'équipe support vous a répondu.",
        type="info",
        icon="💬",
        lien="/support"
    )
    db.add(notif)
    db.commit()
    return {"message": "Réponse envoyée ✅"}