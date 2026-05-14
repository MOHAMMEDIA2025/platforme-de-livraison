"""
app/routes/images.py

Route pour servir les images depuis le dossier img_yanda.
Chaque produit a un dossier avec 3 images nommées 1, 2, 3
(extensions: png, jpg, jpeg, webp, avif, gif)
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/img", tags=["Images"])

# Dossier racine des images produits
IMG_YANDA_DIR = Path("img_yanda")

SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".bmp"]


def find_image(folder: str, num: int) -> Path | None:
    """
    Cherche l'image numéro `num` dans le dossier `folder`.
    Retourne le chemin si trouvé, None sinon.
    """
    folder_path = IMG_YANDA_DIR / folder
    if not folder_path.exists() or not folder_path.is_dir():
        return None

    for ext in SUPPORTED_EXTENSIONS:
        candidate = folder_path / f"{num}{ext}"
        if candidate.exists():
            return candidate

    return None


def get_product_images(folder: str) -> list[str]:
    """
    Retourne la liste des URLs des images disponibles pour un produit.
    """
    urls = []
    for num in [1, 2, 3]:
        img = find_image(folder, num)
        if img:
            urls.append(f"/img/{folder}/{num}")
    return urls


@router.get("/{folder}/{num}")
def serve_product_image(folder: str, num: int):
    """
    Sert l'image num (1, 2 ou 3) du dossier produit.
    """
    if num not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Numéro d'image invalide (1, 2 ou 3)")

    img_path = find_image(folder, num)
    if not img_path:
        raise HTTPException(status_code=404, detail=f"Image {num} introuvable dans {folder}")

    # Déterminer le media_type
    ext = img_path.suffix.lower()
    media_types = {
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".gif":  "image/gif",
        ".bmp":  "image/bmp",
    }
    media_type = media_types.get(ext, "image/jpeg")

    return FileResponse(str(img_path), media_type=media_type)


@router.get("/list/{folder}")
def list_product_images(folder: str):
    """
    Liste les URLs des images disponibles pour un produit.
    """
    urls = get_product_images(folder)
    if not urls:
        raise HTTPException(status_code=404, detail=f"Aucune image trouvée dans {folder}")
    return {"folder": folder, "images": urls, "count": len(urls)}


@router.get("/folders")
def list_all_folders():
    """
    Liste tous les dossiers disponibles dans img_yanda.
    """
    if not IMG_YANDA_DIR.exists():
        return {"folders": [], "message": "Dossier img_yanda introuvable"}

    folders = [
        d.name for d in IMG_YANDA_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    folders.sort()
    return {"folders": folders, "count": len(folders)}