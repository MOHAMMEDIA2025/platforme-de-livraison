# app/routes/chatbot.py — VERSION CORRIGÉE
#
# Corrections :
#  - Admin chat → /admin/chat (non /chat)
#  - Admin voice → /admin/voice (non /voice)
#  - Historique → format {items, total} avec paires Q/R
#  - Sauvegarde Q+R dans le même enregistrement (colonne reponse)
#  - Meilleure gestion d'erreurs avec messages utiles

import json as _json
import httpx
from fastapi import (
    APIRouter, Depends, HTTPException,
    UploadFile, File, Form, Query,
)
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.dependencies import admin_only, get_current_user
from app.database import get_db
from app.models.chat_history import ChatHistory

import os

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# ── URL ngrok externe ─────────────────────────────────────────────────────────
CHATBOT_API_URL = os.getenv(
    "CHATBOT_API_URL",
    "https://proactive-thigh-headlock.ngrok-free.dev"
)

NGROK_HEADERS = {
    "accept"                    : "application/json",
    "ngrok-skip-browser-warning": "true",
}

TIMEOUT_CHAT  = 45.0
TIMEOUT_VOICE = 90.0


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _handle_error(e: Exception):
    if isinstance(e, httpx.TimeoutException):
        raise HTTPException(
            status_code=504,
            detail="Le chatbot ne répond pas (timeout). Vérifiez que le serveur IA est démarré."
        )
    if isinstance(e, httpx.ConnectError):
        raise HTTPException(
            status_code=503,
            detail="Impossible de joindre le serveur IA. Vérifiez l'URL CHATBOT_API_URL et le serveur."
        )
    if isinstance(e, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Erreur du chatbot IA : {e.response.text}",
        )
    raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")


def _save_qa(
    db: Session,
    user_id: int,
    session_id: Optional[str],
    question: str,
    reponse: str,
    type_message: str = "text",
    transcription: Optional[str] = None,
):
    """Sauvegarde une paire Q/R dans un seul enregistrement."""
    try:
        msg = ChatHistory(
            user_id=user_id,
            session_id=session_id,
            role="user",
            type_message=type_message,
            content=question,
            reponse=reponse,
            transcription=transcription,
        )
        db.add(msg)
        db.commit()
    except Exception as ex:
        print(f"[WARN] Impossible de sauvegarder l'historique : {ex}")


def _rows_to_qa(messages: list, db=None) -> list:
    """Convertit les enregistrements DB en paires Q/R pour le frontend."""
    # Charger les noms d'utilisateurs si db fourni
    user_names = {}
    if db and messages:
        from app.models.user import User
        user_ids = {m.user_id for m in messages}
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_names = {u.id: (u.nom or u.email or f"Client #{u.id}") for u in users}

    result = []
    for m in messages:
        if m.reponse:
            result.append({
                "id"           : m.id,
                "user_id"      : m.user_id,
                "user_nom"     : user_names.get(m.user_id, f"Client #{m.user_id}"),
                "session_id"   : m.session_id,
                "type_message" : m.type_message,
                "question"     : m.content,
                "reponse"      : m.reponse,
                "transcription": m.transcription,
                "created_at"   : m.created_at.isoformat() if m.created_at else None,
            })
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — CHAT TEXTE  (/admin/chat sur l'API externe)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/chat", summary="[Admin] Question texte → réponse IA")
async def admin_chat_text(
    question: str = Form(...),
    admin=Depends(admin_only),
    db: Session = Depends(get_db),
):
    user_id = int(admin["sub"])
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            # ✅ CORRECTION : /admin/chat au lieu de /chat
            r = await client.post(
                f"{CHATBOT_API_URL}/admin/chat",
                data={"question": question},
                headers=NGROK_HEADERS,
            )
            r.raise_for_status()
            data   = r.json()
            answer = data.get("answer") or data.get("response") or ""

            _save_qa(db, user_id, None, question, answer, "text")

            return {"answer": answer, "response": answer}

    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — VOICE  (/admin/voice sur l'API externe)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/voice", summary="[Admin] Audio → transcription + réponse IA")
async def admin_chat_voice(
    audio: UploadFile = File(...),
    admin=Depends(admin_only),
    db: Session = Depends(get_db),
):
    user_id     = int(admin["sub"])
    audio_bytes = await audio.read()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_VOICE) as client:
            # ✅ CORRECTION : /admin/voice au lieu de /voice
            r = await client.post(
                f"{CHATBOT_API_URL}/admin/voice",
                files={"audio": (audio.filename or "audio.webm", audio_bytes, audio.content_type or "audio/webm")},
                headers=NGROK_HEADERS,
            )
            r.raise_for_status()
            data          = r.json()
            transcription = data.get("transcription") or data.get("transcript") or ""
            answer        = data.get("answer") or data.get("response") or ""

            _save_qa(db, user_id, None, transcription or "[audio]", answer, "voice", transcription)

            return data

    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT — SESSION
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/client/session", summary="[Client] Créer une session chatbot")
async def client_create_session(current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.post(f"{CHATBOT_API_URL}/session", headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.get("/client/session/{session_id}", summary="[Client] Info session")
async def client_get_session(session_id: str, current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.get(f"{CHATBOT_API_URL}/session/{session_id}", headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.delete("/client/session/{session_id}", summary="[Client] Supprimer session")
async def client_delete_session(session_id: str, current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.delete(f"{CHATBOT_API_URL}/session/{session_id}", headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT — CHAT TEXTE
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/client/chat", summary="[Client] Question texte → réponse IA")
async def client_chat_text(
    question  : str = Form(...),
    session_id: str = Form(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=400,
            detail="session_id requis. Créez d'abord une session via POST /chatbot/client/session.",
        )

    user_id = int(current_user["sub"])
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.post(
                f"{CHATBOT_API_URL}/chat",
                data={"question": question, "session_id": session_id},
                headers=NGROK_HEADERS,
            )
            r.raise_for_status()
            data   = r.json()
            answer = data.get("answer") or data.get("response") or ""

            _save_qa(db, user_id, session_id, question, answer, "text")

            return {
                "session_id": data.get("session_id", session_id),
                "answer"    : answer,
                "response"  : answer,
            }

    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT — VOICE
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/client/voice", summary="[Client] Audio → transcription + réponse IA")
async def client_chat_voice(
    audio     : UploadFile = File(...),
    session_id: str        = Form(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id requis.")

    user_id     = int(current_user["sub"])
    audio_bytes = await audio.read()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_VOICE) as client:
            r = await client.post(
                f"{CHATBOT_API_URL}/voice",
                files={"audio": (audio.filename or "audio.webm", audio_bytes, audio.content_type or "audio/webm")},
                data ={"session_id": session_id},
                headers=NGROK_HEADERS,
            )
            r.raise_for_status()
            data          = r.json()
            transcription = data.get("transcription") or data.get("transcript") or ""
            answer        = data.get("answer") or data.get("response") or ""

            _save_qa(db, user_id, session_id, transcription or "[audio]", answer, "voice", transcription)

            return data

    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post("/client/voice/transcribe", summary="[Client] Audio → transcription seule")
async def client_transcribe(audio: UploadFile = File(...), current_user=Depends(get_current_user)):
    audio_bytes = await audio.read()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_VOICE) as client:
            r = await client.post(
                f"{CHATBOT_API_URL}/voice/transcribe",
                files={"audio": (audio.filename or "audio.webm", audio_bytes, audio.content_type or "audio/webm")},
                headers=NGROK_HEADERS,
            )
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT — PANIER
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/client/cart")
async def client_get_cart(session_id: str = Query(...), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.get(f"{CHATBOT_API_URL}/cart", params={"session_id": session_id}, headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post("/client/cart/search")
async def client_cart_search(session_id: str = Query(...), term: str = Form(...), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.post(
                f"{CHATBOT_API_URL}/cart/search",
                content=_json.dumps({"term": term, "session_id": session_id}),
                headers={**NGROK_HEADERS, "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post("/client/cart/add")
async def client_cart_add(session_id: str = Query(...), product_id: int = Form(...), qty: int = Form(default=1, ge=1), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.post(
                f"{CHATBOT_API_URL}/cart/add",
                content=_json.dumps({"product_id": product_id, "qty": qty, "session_id": session_id}),
                headers={**NGROK_HEADERS, "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.put("/client/cart/item/{product_id}")
async def client_cart_update(product_id: int, session_id: str = Query(...), qty: int = Form(..., ge=0), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.put(
                f"{CHATBOT_API_URL}/cart/item/{product_id}",
                content=_json.dumps({"qty": qty, "session_id": session_id}),
                headers={**NGROK_HEADERS, "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.delete("/client/cart/item/{product_id}")
async def client_cart_remove_item(product_id: int, session_id: str = Query(...), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.delete(f"{CHATBOT_API_URL}/cart/item/{product_id}", params={"session_id": session_id}, headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.delete("/client/cart")
async def client_cart_clear(session_id: str = Query(...), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.delete(f"{CHATBOT_API_URL}/cart", params={"session_id": session_id}, headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post("/client/cart/checkout")
async def client_cart_checkout(session_id: str = Query(...), current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.post(f"{CHATBOT_API_URL}/cart/checkout", params={"session_id": session_id}, headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT — PRODUITS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/client/products")
async def client_products(q: Optional[str] = Query(None), category: Optional[str] = Query(None), current_user=Depends(get_current_user)):
    params = {}
    if q:        params["q"]        = q
    if category: params["category"] = category
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.get(f"{CHATBOT_API_URL}/products", params=params, headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.get("/client/products/{product_id}")
async def client_product_detail(product_id: str, current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.get(f"{CHATBOT_API_URL}/products/{product_id}", headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.get("/client/categories")
async def client_categories(current_user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
            r = await client.get(f"{CHATBOT_API_URL}/categories", headers=NGROK_HEADERS)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIQUE — CLIENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history/me", summary="[Client] Mon historique de conversations")
def get_my_history(
    skip        : int           = Query(0, ge=0),
    limit       : int           = Query(50, ge=1, le=200),
    type_message: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])

    # Nouveau format : Q/R pairés (colonne reponse remplie)
    q_new = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.role    == "user",
        ChatHistory.reponse != None,
    )
    if type_message:
        q_new = q_new.filter(ChatHistory.type_message == type_message)

    total_new = q_new.count()
    new_msgs  = q_new.order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit).all()
    items     = _rows_to_qa(new_msgs)

    # Ancien format : messages user séparés (session_id groupés)
    # On les récupère si peu de données dans le nouveau format
    if total_new < 3:
        q_old = db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.role    == "user",
            ChatHistory.reponse == None,
        )
        if type_message:
            q_old = q_old.filter(ChatHistory.type_message == type_message)
        old_msgs = q_old.order_by(ChatHistory.created_at.desc()).limit(limit).all()
        for m in old_msgs:
            items.append({
                "id"           : m.id,
                "user_id"      : m.user_id,
                "session_id"   : m.session_id,
                "type_message" : m.type_message,
                "question"     : m.content,
                "reponse"      : "(ancienne conversation)",
                "transcription": m.transcription,
                "created_at"   : m.created_at.isoformat() if m.created_at else None,
            })

    return {
        "items": items,
        "total": total_new + (len(items) - len(new_msgs)),
    }


@router.delete("/history/me")
def clear_my_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = int(current_user["sub"])
    deleted = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    return {"message": f"{deleted} message(s) supprimé(s)"}


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIQUE — ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history/admin", summary="[Admin] Historique admin")
def get_admin_history(
    skip        : int           = Query(0, ge=0),
    limit       : int           = Query(50, ge=1, le=200),
    type_message: Optional[str] = Query(None),
    admin=Depends(admin_only),
    db: Session = Depends(get_db),
):
    user_id = int(admin["sub"])
    q = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.role    == "user",
        ChatHistory.reponse != None,
    )
    if type_message:
        q = q.filter(ChatHistory.type_message == type_message)

    total    = q.count()
    messages = q.order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "items": _rows_to_qa(messages, db),
        "total": total,
    }


@router.delete("/history/admin")
def clear_admin_history(admin=Depends(admin_only), db: Session = Depends(get_db)):
    user_id = int(admin["sub"])
    deleted = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    return {"message": f"{deleted} message(s) supprimé(s)"}


@router.delete("/history/{item_id}", summary="Supprimer un échange spécifique")
def delete_one_history(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    msg = db.query(ChatHistory).filter(ChatHistory.id == item_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Échange introuvable")
    # Admin peut supprimer tout, client seulement le sien
    role = current_user.get("role", "client")
    if role != "admin" and msg.user_id != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    db.delete(msg)
    db.commit()
    return {"message": "Échange supprimé"}


@router.get("/history/clients", summary="[Admin] Historique de tous les clients")
def get_clients_history(
    skip        : int           = Query(0, ge=0),
    limit       : int           = Query(50, ge=1, le=200),
    user_id     : Optional[int] = Query(None),
    type_message: Optional[str] = Query(None),
    admin=Depends(admin_only),
    db: Session = Depends(get_db),
):
    q = db.query(ChatHistory).filter(
        ChatHistory.role    == "user",
        ChatHistory.reponse != None,
    )
    if user_id:
        q = q.filter(ChatHistory.user_id == user_id)
    if type_message:
        q = q.filter(ChatHistory.type_message == type_message)

    total    = q.count()
    messages = q.order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "items": _rows_to_qa(messages, db),
        "total": total,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{CHATBOT_API_URL}/health", headers=NGROK_HEADERS)
            r.raise_for_status()
            data = r.json()
            return {**data, "proxy_url": CHATBOT_API_URL, "status": "connected"}
    except Exception as e:
        return {
            "status"   : "disconnected",
            "proxy_url": CHATBOT_API_URL,
            "error"    : str(e),
        }
