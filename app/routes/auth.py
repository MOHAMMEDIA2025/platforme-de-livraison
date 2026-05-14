from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.core.security import create_access_token, verify_password, hash_password
from app.schemas.auth import RegisterSchema

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        email=data.email,
        password=hash_password(data.password),
        nom=data.nom,
        telephone=data.telephone,
        role="client"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Notification de bienvenue
    notif = Notification(
        user_id=user.id,
        titre="Bienvenue ! 🎉",
        message=f"Bonjour {data.nom}, votre compte a été créé avec succès.",
        type="success",
        icon="🎉"
    )
    db.add(notif)
    db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "nom": user.nom or ""
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "nom": user.nom
    }


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé. Contactez l'administrateur.")

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "nom": user.nom or ""
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "nom": user.nom
    }


@router.get("/me")
def get_me(db: Session = Depends(get_db),
           current_user=Depends(__import__('app.core.dependencies', fromlist=['get_current_user']).get_current_user)):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "nom": user.nom,
        "telephone": user.telephone,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "created_at": user.created_at
    }