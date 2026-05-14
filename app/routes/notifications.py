from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def get_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()

    return [
        {
            "id": n.id,
            "titre": n.titre,
            "message": n.message,
            "type": n.type,
            "icon": n.icon,
            "lien": n.lien,
            "est_lue": n.est_lue,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/nb-non-lues")
def nb_non_lues(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.est_lue == False
    ).count()
    return {"nb": count}


@router.patch("/{notif_id}/lue")
def marquer_lue(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == user_id
    ).first()
    if notif:
        notif.est_lue = True
        db.commit()
    return {"ok": True}


@router.patch("/lire-tout")
def marquer_toutes_lues(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.est_lue == False
    ).update({"est_lue": True})
    db.commit()
    return {"ok": True}


@router.delete("/{notif_id}")
def supprimer_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = int(current_user["sub"])
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == user_id
    ).first()
    if notif:
        db.delete(notif)
        db.commit()
    return {"ok": True}