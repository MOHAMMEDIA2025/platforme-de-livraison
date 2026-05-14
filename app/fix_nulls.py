"""
Script de nettoyage des valeurs NULL — à exécuter UNE SEULE FOIS après migrate.py :
    python fix_nulls.py
"""

from sqlalchemy import create_engine, text

# ✅ CORRECTION : port corrigé de 5432 → 5433 (même que database.py)
DATABASE_URL = "postgresql://postgres:admin@localhost:5433/livraison_db"

engine = create_engine(DATABASE_URL)

fixes = [
    # ── TABLE produits ────────────────────────────────────────────────────────
    "UPDATE produits SET stock          = 0         WHERE stock          IS NULL;",
    "UPDATE produits SET note_moyenne   = 0.0       WHERE note_moyenne   IS NULL;",
    "UPDATE produits SET nb_avis        = 0         WHERE nb_avis        IS NULL;",
    "UPDATE produits SET categorie      = 'Général' WHERE categorie      IS NULL;",
    "UPDATE produits SET est_disponible = TRUE      WHERE est_disponible IS NULL;",
    "UPDATE produits SET est_promo      = FALSE     WHERE est_promo      IS NULL;",

    # ── TABLE users ───────────────────────────────────────────────────────────
    "UPDATE users SET is_active   = TRUE  WHERE is_active   IS NULL;",
    "UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL;",

    # ── TABLE livreurs ────────────────────────────────────────────────────────
    "UPDATE livreurs SET note_moyenne  = 5.0         WHERE note_moyenne  IS NULL;",
    "UPDATE livreurs SET nb_livraisons = 0           WHERE nb_livraisons IS NULL;",
    "UPDATE livreurs SET vehicule      = 'moto'      WHERE vehicule      IS NULL;",
    "UPDATE livreurs SET is_online     = FALSE       WHERE is_online     IS NULL;",
    "UPDATE livreurs SET statut        = 'disponible' WHERE statut       IS NULL;",

    # ── TABLE commandes ───────────────────────────────────────────────────────
    "UPDATE commandes SET reduction       = 0.0   WHERE reduction       IS NULL;",
    "UPDATE commandes SET frais_livraison = 15.0  WHERE frais_livraison IS NULL;",
    "UPDATE commandes SET is_rated        = FALSE WHERE is_rated        IS NULL;",
    "UPDATE commandes SET total           = 0.0   WHERE total           IS NULL;",
    # note_livreur et commentaire restent NULL volontairement (optionnels)
]

print("🧹 Nettoyage des valeurs NULL...\n")

with engine.connect() as conn:
    for sql in fixes:
        try:
            result = conn.execute(text(sql))
            print(f"  ✅  {sql.strip()}  ({result.rowcount} ligne(s) mise(s) à jour)")
        except Exception as e:
            print(f"  ❌  {sql.strip()}\n      → {e}")
    conn.commit()

print("\n✅ Nettoyage terminé !")
print("👉 Redémarre le serveur : uvicorn app.main:app --reload")