from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5433/livraison_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS statut_paiement VARCHAR DEFAULT 'en_attente';"
        ))
        conn.commit()
        print("✅ Colonne statut_paiement ajoutée avec succès !")
    except Exception as e:
        print(f"❌ Erreur : {e}")