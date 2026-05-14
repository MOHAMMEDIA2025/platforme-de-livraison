from fastapi import Depends, HTTPException
from jose import jwt
from app.core.security import oauth2_scheme, SECRET_KEY, ALGORITHM


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


def admin_only(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def client_only(user=Depends(get_current_user)):
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Client only")
    return user


def livreur_only(user=Depends(get_current_user)):
    if user["role"] != "livreur":
        raise HTTPException(status_code=403, detail="Livreur only")
    return user