"""
Script de migration — à exécuter UNE SEULE FOIS pour corriger le type de la colonne stock :
    python fix_stock_type.py

Ce script convertit la colonne 'stock' de BOOLEAN → INTEGER dans la table produits,
et ajoute les colonnes manquantes (est_disponible, note_moyenne, nb_avis, image_url, prix_promo, est_promo)
si elles n'existent pas encore.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5433/livraison_db"

engine = create_engine(DATABASE_URL)

migrations = [
    # ── Étape 1 : Convertir stock BOOLEAN → INTEGER ───────────────────────────
    # On crée une colonne temporaire, on copie les données, on drop l'ancienne, on renomme
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS stock_new INTEGER DEFAULT 0;",

    # Convertit True → 1, False/NULL → 0
    "UPDATE produits SET stock_new = CASE WHEN stock::text = 'true' THEN 10 ELSE 0 END;",

    # Supprime l'ancienne colonne boolean
    "ALTER TABLE produits DROP COLUMN IF EXISTS stock;",

    # Renomme la nouvelle colonne
    "ALTER TABLE produits RENAME COLUMN stock_new TO stock;",

    # ── Étape 2 : Ajouter les colonnes manquantes ─────────────────────────────
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_disponible BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS note_moyenne FLOAT DEFAULT 0.0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS nb_avis INTEGER DEFAULT 0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS prix_promo FLOAT;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_promo BOOLEAN DEFAULT FALSE;",

    # ── Étape 3 : Nettoyage des NULLs ────────────────────────────────────────
    "UPDATE produits SET stock = 0 WHERE stock IS NULL;",
    "UPDATE produits SET est_disponible = TRUE WHERE est_disponible IS NULL;",
    "UPDATE produits SET note_moyenne = 0.0 WHERE note_moyenne IS NULL;",
    "UPDATE produits SET nb_avis = 0 WHERE nb_avis IS NULL;",
    "UPDATE produits SET est_promo = FALSE WHERE est_promo IS NULL;",

    # Met est_disponible = TRUE si stock > 0, FALSE sinon
    "UPDATE produits SET est_disponible = CASE WHEN stock > 0 THEN TRUE ELSE FALSE END;",
]

print("🔧 Migration stock BOOLEAN → INTEGER en cours...\n")

with engine.connect() as conn:
    for sql in migrations:
        try:
            result = conn.execute(text(sql))
            print(f"  ✅  {sql.strip()}")
        except Exception as e:
            print(f"  ⚠️   {sql.strip()}\n      → {e}")
    conn.commit()

print("\n✅ Migration terminée !")
print("👉 Redémarre le serveur : uvicorn app.main:app --reload")