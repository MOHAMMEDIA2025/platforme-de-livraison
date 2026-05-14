"""
app/main.py — VERSION AVEC GALERIE img_yanda
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
import os
from pathlib import Path

# ── Modèles ───────────────────────────────────────────────────────────────────
from app.models.user import User
from app.models.produit import Produit
from app.models.commande import Commande
from app.models.commande_item import LigneCommande
from app.models.panier import PanierItem
from app.models.livreur import Livreur
from app.models.avis import Avis
from app.models.notification import Notification
from app.models.code_promo import CodePromo
from app.models.promotion import Promotion
from app.models.support import MessageSupport
from app.models.favori import Favori
from app.models.fidelite import PointFidelite, TransactionPoints
from app.models.paiement import Paiement
from app.models.commande_catalogue import CommandeCatalogue, LigneCommandeCatalogue
from app.models.livraison_detail import LivraisonDetail
from app.models.chat_history import ChatHistory
from app.models.ml_data import SessionAchat, ProfilClient

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routes import (
    auth, commande, panier, produit, livreur,
    phone_auth, google_auth, tracking, admin,
    avis, notifications, profil, code_promo,
    promotions, support, favoris, fidelite, paiement, commande_catalogue,
)
from app.routes import chatbot
from app.routes import images
from app.routes import analytics

# ── Dossiers statiques ────────────────────────────────────────────────────────
os.makedirs("static/images/produits", exist_ok=True)
Path("img_yanda").mkdir(exist_ok=True)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="DeliveryApp API",
    description="API complète pour application de livraison — FastAPI + PostgreSQL (Neon)",
    version="3.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Fichiers statiques ────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/img_yanda", StaticFiles(directory="img_yanda"), name="img_yanda")

# ── Création des tables manquantes (ne modifie pas les tables existantes) ─────
Base.metadata.create_all(bind=engine)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(commande.router)
app.include_router(panier.router)
app.include_router(produit.router)
app.include_router(livreur.router)
app.include_router(avis.router)
app.include_router(notifications.router)
app.include_router(profil.router)
app.include_router(google_auth.router)
app.include_router(phone_auth.router)
app.include_router(tracking.router)
app.include_router(admin.router)
app.include_router(code_promo.router)
app.include_router(promotions.router)
app.include_router(support.router)
app.include_router(favoris.router)
app.include_router(fidelite.router)
app.include_router(paiement.router)
app.include_router(commande_catalogue.router)
app.include_router(chatbot.router)
app.include_router(images.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "message": "DeliveryApp API v3.5",
        "docs":    "/docs",
        "status":  "running",
        "features": ["galerie img_yanda", "upload images", "chatbot"],
    }
