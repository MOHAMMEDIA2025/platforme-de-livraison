from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import verify_password, hash_password
from app.models.user import User

router = APIRouter(prefix="/profil", tags=["Profil"])


class ProfileUpdate(BaseModel):
    nom: Optional[str] = None
    telephone: Optional[str] = None
    avatar: Optional[str] = None


class PasswordChange(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


@router.get("/")
def get_profil(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {
        "id": user.id,
        "email": user.email,
        "nom": user.nom,
        "telephone": user.telephone,
        "avatar": user.avatar,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.put("/")
def update_profil(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if data.nom is not None:       user.nom = data.nom
    if data.telephone is not None: user.telephone = data.telephone
    if data.avatar is not None:    user.avatar = data.avatar

    db.commit()
    db.refresh(user)
    return {"message": "Profil mis à jour", "nom": user.nom}


@router.put("/password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if not user.password:
        raise HTTPException(status_code=400, detail="Compte OAuth — pas de mot de passe local")

    if not verify_password(data.ancien_mot_de_passe, user.password):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")

    if len(data.nouveau_mot_de_passe) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 6 caractères")

    user.password = hash_password(data.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe modifié avec succès"}
