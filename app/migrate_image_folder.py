"""
app/migrate_image_folder.py

Script de migration pour :
1. Ajouter la colonne image_folder dans la table produits
2. Tenter de mapper automatiquement les produits aux dossiers img_yanda
   en comparant les noms

Exécution :
    python -m app.migrate_image_folder

OU directement :
    python app/migrate_image_folder.py
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5433/livraison_db"
IMG_YANDA_DIR = Path("img_yanda")

engine = create_engine(DATABASE_URL)


def normalize(name: str) -> str:
    """
    Normalise un nom pour la comparaison :
    - minuscules
    - supprime accents courants
    - remplace tirets/underscores par espaces
    - supprime caractères spéciaux
    """
    import unicodedata
    name = name.lower().strip()
    # Normaliser les caractères unicode (accents)
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Remplacer séparateurs
    for char in ["-", "_", ".", "(", ")", "[", "]", ",", "/"]:
        name = name.replace(char, " ")
    # Supprimer espaces multiples
    name = " ".join(name.split())
    return name


def similarity_score(prod_name: str, folder_name: str) -> float:
    """
    Score de similarité entre le nom produit et le nom de dossier.
    Score entre 0 et 1.
    """
    pn = normalize(prod_name)
    fn = normalize(folder_name)

    if pn == fn:
        return 1.0

    # Mots communs
    pwords = set(pn.split())
    fwords = set(fn.split())

    if not pwords or not fwords:
        return 0.0

    common = pwords & fwords
    score = len(common) / max(len(pwords), len(fwords))
    return score


def find_best_folder(prod_name: str, folders: list[str]) -> tuple[str | None, float]:
    """
    Trouve le meilleur dossier correspondant au nom du produit.
    Retourne (folder_name, score).
    """
    best_folder = None
    best_score  = 0.0

    for folder in folders:
        score = similarity_score(prod_name, folder)
        if score > best_score:
            best_score  = score
            best_folder = folder

    return best_folder, best_score


def run():
    print("🚀 Migration image_folder — début\n")

    # 1. Ajouter la colonne si absente
    print("📐 Ajout colonne image_folder...")
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE produits ADD COLUMN IF NOT EXISTS image_folder VARCHAR(200);"
            ))
            conn.commit()
        print("  ✅ Colonne image_folder OK\n")
    except Exception as e:
        print(f"  ❌ Erreur colonne : {e}\n")
        return

    # 2. Lister les dossiers dans img_yanda
    if not IMG_YANDA_DIR.exists():
        print(f"  ⚠️  Dossier img_yanda introuvable à : {IMG_YANDA_DIR.absolute()}")
        print("  Créez le dossier img_yanda et ajoutez vos images.\n")
        return

    folders = sorted([
        d.name for d in IMG_YANDA_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    print(f"📁 {len(folders)} dossiers trouvés dans img_yanda :\n")
    for f in folders:
        print(f"   • {f}")
    print()

    if not folders:
        print("  ⚠️  Aucun dossier trouvé. Ajoutez des dossiers dans img_yanda/\n")
        return

    # 3. Récupérer les produits sans image_folder
    print("📦 Mapping automatique des produits...\n")
    SEUIL_SCORE = 0.5  # Score minimum pour accepter le mapping

    matched   = []
    unmatched = []

    with engine.connect() as conn:
        produits = conn.execute(text(
            "SELECT id_produit, nom_produit FROM produits WHERE image_folder IS NULL ORDER BY id_produit;"
        )).fetchall()

        for prod_id, prod_nom in produits:
            if not prod_nom:
                unmatched.append((prod_id, prod_nom, "nom vide"))
                continue

            best_folder, score = find_best_folder(prod_nom, folders)

            if score >= SEUIL_SCORE:
                matched.append((prod_id, prod_nom, best_folder, score))
            else:
                unmatched.append((prod_id, prod_nom, f"meilleur score: {score:.2f} ({best_folder})"))

        # 4. Appliquer les mappings
        if matched:
            print(f"✅ {len(matched)} produits mappés automatiquement :\n")
            for prod_id, prod_nom, folder, score in matched:
                print(f"   [{prod_id:4d}] {prod_nom[:50]:<50} → {folder}  (score: {score:.2f})")
                conn.execute(text(
                    "UPDATE produits SET image_folder = :folder WHERE id_produit = :id"
                ), {"folder": folder, "id": prod_id})
            conn.commit()
            print()

        if unmatched:
            print(f"⚠️  {len(unmatched)} produits sans correspondance :\n")
            for item in unmatched:
                prod_id, prod_nom, raison = item
                print(f"   [{prod_id:4d}] {(prod_nom or 'SANS NOM')[:50]:<50} ({raison})")
            print()

    print("✅ Migration terminée !")
    print("👉 Vérifiez les mappings dans la base et corrigez manuellement si nécessaire.")
    print("👉 Pour assigner manuellement :")
    print("   UPDATE produits SET image_folder = 'nom_du_dossier' WHERE id_produit = X;\n")


if __name__ == "__main__":
    run()