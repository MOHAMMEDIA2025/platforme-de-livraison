"""
app/routes/google_auth.py  — VERSION FIREBASE
La connexion Google est maintenant gérée CÔTÉ FRONTEND via Firebase Authentication.

Flux :
  1. Le frontend utilise signInWithPopup(auth, googleProvider) de Firebase.
  2. Firebase retourne un idToken.
  3. Le frontend envoie l'idToken à POST /auth/google/verify.
  4. Le backend vérifie le token et retourne notre JWT applicatif.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.core.security import create_access_token
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Google Auth"])

# ── Initialisation Firebase Admin (partagée avec phone_auth) ─────────────────
_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "serviceAccountKey.json")
    if not os.path.exists(key_path):
        raise RuntimeError(
            f"Firebase service account key introuvable : {key_path}"
        )
    # Ne pas réinitialiser si déjà fait par phone_auth
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass  # App déjà initialisée
    _firebase_initialized = True


# ── Schéma ───────────────────────────────────────────────────────────────────

class GoogleTokenRequest(BaseModel):
    id_token: str   # idToken Firebase renvoyé après signInWithPopup Google


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/google/verify")
def verify_google(payload: GoogleTokenRequest, db: Session = Depends(get_db)):
    """
    Vérifie le token Firebase Google et retourne notre JWT applicatif.
    """
    _init_firebase()

    try:
        decoded = firebase_auth.verify_id_token(payload.id_token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token Google expiré.")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token Google invalide.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erreur Firebase : {str(e)}")

    email   = decoded.get("email")
    nom     = decoded.get("name", "")
    avatar  = decoded.get("picture", None)

    if not email:
        raise HTTPException(status_code=400, detail="Email absent du token Google.")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            password="google_firebase_oauth",
            role="client",
            nom=nom,
            avatar=avatar,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if not user.nom and nom:
            user.nom = nom
            changed = True
        if not user.avatar and avatar:
            user.avatar = avatar
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    jwt_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "nom": user.nom or "",
    })

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "nom": user.nom or "",
        "message": "Connexion Google réussie ✅",
    }
