"""
Script de migration — à exécuter UNE SEULE FOIS depuis la racine du projet :
    python migrate.py
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/livraison_db"

engine = create_engine(DATABASE_URL)

migrations = [
    # ── Colonnes GPS du livreur ───────────────────────────────────────────────
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS lat FLOAT;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS lng FLOAT;",

    # ── Colonnes manquantes dans commandes ───────────────────────────────────
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS note_livreur FLOAT;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS commentaire VARCHAR;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS note_client VARCHAR;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS code_promo VARCHAR;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS reduction FLOAT DEFAULT 0.0;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS frais_livraison FLOAT DEFAULT 15.0;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS is_rated BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;",

    # ── Colonnes manquantes dans produits ─────────────────────────────────────
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS note_moyenne FLOAT DEFAULT 0.0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS nb_avis INTEGER DEFAULT 0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS categorie VARCHAR DEFAULT 'Général';",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_disponible BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_promo BOOLEAN DEFAULT FALSE;",

    # ── Colonnes manquantes dans users ────────────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS nom VARCHAR;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telephone VARCHAR;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR;",

    # ── Colonnes manquantes dans livreurs ─────────────────────────────────────
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS note_moyenne FLOAT DEFAULT 5.0;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS nb_livraisons INTEGER DEFAULT 0;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS vehicule VARCHAR DEFAULT 'moto';",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS zone VARCHAR;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;",
]

print("🚀 Migration en cours...\n")

with engine.connect() as conn:
    for sql in migrations:
        try:
            conn.execute(text(sql))
            print(f"  ✅  {sql.strip()}")
        except Exception as e:
            print(f"  ⚠️   {sql.strip()}\n      → {e}")
    conn.commit()

print("\n✅ Migration terminée !")
print("👉 Lance maintenant : python fix_nulls.py")
print("👉 Puis redémarre   : uvicorn app.main:app --reload")