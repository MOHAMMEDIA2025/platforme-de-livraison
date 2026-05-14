import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, client_only
from app.models.paiement import Paiement, StatutPaiement, MethodePaiement
from app.models.commande import Commande
from app.models.notification import Notification
from app.schemas.paiement import PaiementCreate, PaiementOut, StripeSessionOut

router = APIRouter(prefix="/paiement", tags=["Paiement"])
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ── Créer une session Stripe Checkout ─────────────────────────────────────────
@router.post("/stripe/create-session", response_model=StripeSessionOut)
def create_stripe_session(
    data: PaiementCreate,
    db: Session = Depends(get_db),
    user=Depends(client_only)
):
    user_id = int(user["sub"])  # le JWT stocke l'ID sous "sub"

    commande = db.query(Commande).filter(
        Commande.id      == data.commande_id,
        Commande.user_id == user_id
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    if commande.statut_paiement == "payee":
        raise HTTPException(status_code=400, detail="Commande déjà payée")

    montant_centimes = int(
        (commande.total + commande.frais_livraison - commande.reduction) * 100
    )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mad",
                "product_data": {"name": f"Commande #{commande.id} - DeliveryApp"},
                "unit_amount": montant_centimes,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=(
            f"{os.getenv('FRONTEND_URL')}/paiement/success"
            f"?session_id={{CHECKOUT_SESSION_ID}}&commande_id={commande.id}"
        ),
        cancel_url=(
            f"{os.getenv('FRONTEND_URL')}/paiement/cancel"
            f"?commande_id={commande.id}"
        ),
        metadata={
            "commande_id": str(commande.id),
            "user_id":     str(user_id)
        }
    )

    paiement = Paiement(
        commande_id    = commande.id,
        user_id        = user_id,
        montant        = commande.total + commande.frais_livraison - commande.reduction,
        methode        = MethodePaiement.stripe,
        statut         = StatutPaiement.en_attente,
        transaction_id = session.id
    )
    db.add(paiement)
    db.commit()

    return {"checkout_url": session.url, "session_id": session.id}


# ── Webhook Stripe ────────────────────────────────────────────────────────────
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload invalide")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature invalide")

    if event["type"] == "checkout.session.completed":
        session     = event["data"]["object"]
        commande_id = int(session["metadata"]["commande_id"])
        user_id     = int(session["metadata"]["user_id"])

        paiement = db.query(Paiement).filter(
            Paiement.transaction_id == session["id"]
        ).first()
        if paiement:
            paiement.statut = StatutPaiement.complete

        commande = db.query(Commande).filter(Commande.id == commande_id).first()
        if commande:
            commande.statut_paiement = "payee"

        notif = Notification(
            user_id = user_id,
            titre   = "Paiement confirmé ✅",
            message = f"Votre paiement pour la commande #{commande_id} a été accepté.",
            type    = "success",
            icon    = "💳",
            lien    = f"/tracking/{commande_id}"
        )
        db.add(notif)
        db.commit()

    elif event["type"] == "checkout.session.expired":
        session  = event["data"]["object"]
        paiement = db.query(Paiement).filter(
            Paiement.transaction_id == session["id"]
        ).first()
        if paiement:
            paiement.statut = StatutPaiement.echoue
            db.commit()

    return {"status": "ok"}


# ── Paiement Cash ─────────────────────────────────────────────────────────────
@router.post("/cash", response_model=PaiementOut)
def paiement_cash(
    data: PaiementCreate,
    db: Session = Depends(get_db),
    user=Depends(client_only)
):
    user_id = int(user["sub"])

    commande = db.query(Commande).filter(
        Commande.id      == data.commande_id,
        Commande.user_id == user_id
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    commande.statut_paiement = "cash_en_attente"

    paiement = Paiement(
        commande_id = commande.id,
        user_id     = user_id,
        montant     = commande.total + commande.frais_livraison - commande.reduction,
        methode     = MethodePaiement.cash,
        statut      = StatutPaiement.en_attente
    )
    db.add(paiement)
    db.commit()
    db.refresh(paiement)
    return paiement


# ── Paiement Virement ─────────────────────────────────────────────────────────
@router.post("/virement", response_model=PaiementOut)
def paiement_virement(
    data: PaiementCreate,
    db: Session = Depends(get_db),
    user=Depends(client_only)
):
    user_id = int(user["sub"])

    commande = db.query(Commande).filter(
        Commande.id      == data.commande_id,
        Commande.user_id == user_id
    ).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    commande.statut_paiement = "virement_en_attente"

    paiement = Paiement(
        commande_id = commande.id,
        user_id     = user_id,
        montant     = commande.total + commande.frais_livraison - commande.reduction,
        methode     = MethodePaiement.virement,
        statut      = StatutPaiement.en_attente
    )
    db.add(paiement)
    db.commit()
    db.refresh(paiement)
    return paiement


# ── Consulter le paiement d'une commande ─────────────────────────────────────
@router.get("/commande/{commande_id}", response_model=PaiementOut)
def get_paiement(
    commande_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    paiement = db.query(Paiement).filter(
        Paiement.commande_id == commande_id
    ).first()
    if not paiement:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    return paiement