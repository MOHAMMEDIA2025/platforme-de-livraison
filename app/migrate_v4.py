"""
app/migrate_v4.py
Script de migration v4 — exécuter UNE SEULE FOIS depuis la racine:
    python migrate_v4.py
"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/livraison_db"
engine = create_engine(DATABASE_URL)

migrations = [
    # Table promotions
    """
    CREATE TABLE IF NOT EXISTS promotions (
        id SERIAL PRIMARY KEY,
        code VARCHAR UNIQUE NOT NULL,
        description VARCHAR,
        type VARCHAR DEFAULT 'pourcentage',
        valeur FLOAT DEFAULT 0.0,
        minimum_commande FLOAT DEFAULT 0.0,
        usage_max INTEGER,
        usage_count INTEGER DEFAULT 0,
        date_fin TIMESTAMP,
        est_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # Colonnes livreur manquantes
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS lat FLOAT;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS lng FLOAT;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS vehicule VARCHAR DEFAULT 'moto';",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS zone VARCHAR;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS note_moyenne FLOAT DEFAULT 5.0;",
    "ALTER TABLE livreurs ADD COLUMN IF NOT EXISTS nb_livraisons INTEGER DEFAULT 0;",

    # Colonnes commande
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS note_client VARCHAR;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS code_promo VARCHAR;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS reduction FLOAT DEFAULT 0.0;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS frais_livraison FLOAT DEFAULT 15.0;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS is_rated BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",

    # Colonnes produit
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS image_url VARCHAR;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS categorie VARCHAR DEFAULT 'Général';",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_disponible BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS est_promo BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS prix_promo FLOAT;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS note_moyenne FLOAT DEFAULT 0.0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS nb_avis INTEGER DEFAULT 0;",
    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

    # Colonnes user
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS nom VARCHAR;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telephone VARCHAR;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

    # Colonnes lignes_commande (snapshot prix)
    "ALTER TABLE lignes_commande ADD COLUMN IF NOT EXISTS prix_unitaire FLOAT;",
    "ALTER TABLE lignes_commande ADD COLUMN IF NOT EXISTS nom_produit VARCHAR;",

    # Index pour performance
    "CREATE INDEX IF NOT EXISTS idx_commandes_user_id ON commandes(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_commandes_livreur_id ON commandes(livreur_id);",
    "CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut);",
    "CREATE INDEX IF NOT EXISTS idx_commandes_created_at ON commandes(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_produits_categorie ON produits(categorie);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_code ON promotions(code);",
]

with engine.connect() as conn:
    for sql in migrations:
        sql_clean = sql.strip()
        if not sql_clean:
            continue
        try:
            conn.execute(text(sql_clean))
            label = sql_clean.split('\n')[0][:60]
            print(f"✅ OK : {label}...")
        except Exception as e:
            print(f"⚠️  SKIP : {str(e)[:80]}")
    conn.commit()

print("\n✅ Migration v4 terminée. Redémarre le serveur FastAPI.")