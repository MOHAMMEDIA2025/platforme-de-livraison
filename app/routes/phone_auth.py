"""
app/routes/phone_auth.py
Authentification par numéro de téléphone via Firebase.

Flux :
  1. Le frontend utilise Firebase SDK pour envoyer le SMS et vérifier le code OTP.
  2. Firebase retourne un idToken (JWT signé par Firebase).
  3. Le frontend envoie cet idToken à ce endpoint.
  4. Le backend vérifie le token avec firebase-admin et crée / récupère l'utilisateur.
  5. On retourne notre propre JWT applicatif.

Dépendances :
    pip install firebase-admin
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

router = APIRouter(prefix="/auth", tags=["Phone Auth"])

# ── Initialisation Firebase Admin (une seule fois) ───────────────────────────
# Place ton fichier serviceAccountKey.json dans le dossier racine du projet.
# Ou utilise la variable d'env FIREBASE_SERVICE_ACCOUNT_KEY (chemin vers le fichier).

_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "serviceAccountKey.json")
    if not os.path.exists(key_path):
        raise RuntimeError(
            f"Firebase service account key introuvable : {key_path}\n"
            "Télécharge-le depuis Firebase Console → Paramètres du projet → Comptes de service."
        )
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


# ── Schéma de requête ─────────────────────────────────────────────────────────

class PhoneTokenRequest(BaseModel):
    id_token: str   # idToken renvoyé par Firebase après vérification OTP


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/phone/verify")
def verify_phone(payload: PhoneTokenRequest, db: Session = Depends(get_db)):
    """
    Reçoit l'idToken Firebase (obtenu côté frontend après confirmationResult.confirm(code)).
    Vérifie le token, puis crée ou récupère l'utilisateur en base.
    Retourne notre JWT applicatif.
    """
    _init_firebase()

    # 1. Vérifier le token Firebase
    try:
        decoded = firebase_auth.verify_id_token(payload.id_token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token Firebase expiré. Recommencez la vérification.")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token Firebase invalide.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erreur de vérification Firebase : {str(e)}")

    phone_number = decoded.get("phone_number")
    firebase_uid = decoded.get("uid")

    if not phone_number:
        raise HTTPException(status_code=400, detail="Numéro de téléphone absent du token Firebase.")

    # 2. Chercher l'utilisateur par téléphone ou firebase_uid
    user = db.query(User).filter(User.telephone == phone_number).first()

    if not user:
        # Créer un nouveau compte
        user = User(
            email=f"{firebase_uid}@phone.local",   # email fictif unique
            password="firebase_phone_oauth",
            telephone=phone_number,
            role="client",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Générer notre JWT applicatif
    jwt_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "nom": user.nom or "",
        "telephone": user.telephone or "",
    })

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "nom": user.nom or "",
        "telephone": user.telephone,
        "message": "Connexion par téléphone réussie ✅",
    }
