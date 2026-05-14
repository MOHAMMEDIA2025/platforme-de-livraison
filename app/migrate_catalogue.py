"""
app/migrate_catalogue.py

Script de migration — à exécuter UNE SEULE FOIS :
    python -m app.migrate_catalogue

Crée les tables :
  - commandes_catalogue
  - commande_catalogue_lignes
  - livraisons_detail

Et insère les 25 commandes + 10 livraisons de démonstration.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin@localhost:5433/livraison_db"
engine = create_engine(DATABASE_URL)

# ══════════════════════════════════════════════════════════════════════════════
#  DDL — Création des tables
# ══════════════════════════════════════════════════════════════════════════════

DDL = """
-- ─────────────────────────────────────────────────────────────────────────────
--  TABLE : commandes_catalogue  (commandes multi-produits analytiques)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commandes_catalogue (
    id                  SERIAL PRIMARY KEY,
    nom_client          VARCHAR(100)    NOT NULL,
    date_commande       TIMESTAMP       NOT NULL,
    code_promo          VARCHAR(30)     DEFAULT NULL,
    remise_appliquee    NUMERIC(5,2)    NOT NULL DEFAULT 0.00
);

-- ─────────────────────────────────────────────────────────────────────────────
--  TABLE : commande_catalogue_lignes  (1 commande → N produits)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commande_catalogue_lignes (
    id                      SERIAL PRIMARY KEY,
    commande_id             INT            NOT NULL
        REFERENCES commandes_catalogue(id) ON DELETE CASCADE,
    produit_achete_fr       VARCHAR(150)   NOT NULL,
    produit_achete_en       VARCHAR(150)   NOT NULL,
    categorie_fr            VARCHAR(60)    NOT NULL,
    categorie_en            VARCHAR(60)    NOT NULL,
    sous_categorie_fr       VARCHAR(60)    NOT NULL,
    sous_categorie_en       VARCHAR(60)    NOT NULL,
    prix_unitaire           NUMERIC(10,2)  NOT NULL,
    quantite                INT            NOT NULL DEFAULT 1,
    prix_ligne_avant_promo  NUMERIC(10,2)  NOT NULL,
    prix_ligne_apres_promo  NUMERIC(10,2)  NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────────────
--  TABLE : livraisons_detail  (livraisons enrichies avec livreur + localisation)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS livraisons_detail (
    id_livraison            SERIAL PRIMARY KEY,
    nom_client              VARCHAR(100)    NOT NULL,
    nom_livreur             VARCHAR(100)    NOT NULL,
    date_livraison          TIMESTAMP       NOT NULL,
    produits                TEXT            NOT NULL,
    quantite_totale         INT             NOT NULL,
    prix_total_livraison    NUMERIC(10,2)   NOT NULL,
    methode_paiement        VARCHAR(60)     NOT NULL,
    localisation_client     VARCHAR(200)    NOT NULL,
    localisation_livreur    VARCHAR(200)    NOT NULL,
    notes_client            TEXT            DEFAULT NULL,
    statut                  VARCHAR(30)     NOT NULL DEFAULT 'En attente'
);
"""

# ══════════════════════════════════════════════════════════════════════════════
#  DML — Données : 25 commandes catalogue
# ══════════════════════════════════════════════════════════════════════════════

INSERT_COMMANDES_CATALOGUE = """
INSERT INTO commandes_catalogue (nom_client, date_commande, code_promo, remise_appliquee) VALUES
('Youssef Amrani',        '2026-01-22 09:14:32', NULL,       0.15),
('Fatima Zahra Bennani',  '2026-01-28 14:05:11', 'SUMMER10', 0.10),
('Mohamed Karim Idrissi', '2026-02-03 11:30:00', NULL,       0.00),
('Houda El Fassi',        '2026-02-05 16:22:47', NULL,       0.20),
('Anas Bouhsaini',        '2026-02-08 10:00:05', 'PROMO5',   0.05),
('Salma Oujdi',           '2026-02-10 08:55:19', NULL,       0.00),
('Rachid Tahiri',         '2026-02-14 13:41:55', NULL,       0.08),
('Zineb Chraibi',         '2026-02-18 18:07:33', 'NOEL20',   0.20),
('Omar Lahlou',           '2026-02-20 20:15:00', NULL,       0.10),
('Nadia Sekkat',          '2026-02-25 09:00:44', NULL,       0.00),
('Karim Alaoui',          '2026-02-28 17:30:22', NULL,       0.15),
('Imane Berrada',         '2026-03-01 12:12:12', 'DESK12',   0.12),
('Tariq Mansouri',        '2026-03-04 15:45:08', NULL,       0.00),
('Sanaa El Hajjami',      '2026-03-06 11:20:30', NULL,       0.10),
('Yassine Qorchi',        '2026-03-09 08:08:08', 'MODE15',   0.15),
('Hajar Moussaoui',       '2026-03-12 14:55:00', NULL,       0.00),
('Mehdi Ziani',           '2026-03-14 19:03:41', NULL,       0.05),
('Rania Tazi',            '2026-03-17 10:30:00', 'LIVRE10',  0.10),
('Badr Skouri',           '2026-03-20 21:00:17', NULL,       0.10),
('Leila Chaoui',          '2026-03-22 16:44:59', 'VIP25',    0.25),
('Ayoub El Khatib',       '2026-03-25 10:05:00', 'TECH10',   0.10),
('Nour Eddine Fassi',     '2026-03-26 13:20:00', NULL,       0.00),
('Salwa Berrada',         '2026-03-27 09:30:00', 'DESK12',   0.12),
('Hamza Qasmi',           '2026-03-28 11:45:00', 'MODE15',   0.15),
('Amina Tahiri',          '2026-03-29 17:00:00', 'LIVRE10',  0.10);
"""

INSERT_LIGNES_CATALOGUE = """
INSERT INTO commande_catalogue_lignes
    (commande_id, produit_achete_fr, produit_achete_en,
     categorie_fr, categorie_en, sous_categorie_fr, sous_categorie_en,
     prix_unitaire, quantite, prix_ligne_avant_promo, prix_ligne_apres_promo)
VALUES
(1, 'Clavier Logitech K120', 'Keyboard Logitech K120',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 100.00, 1, 100.00, 85.00),
(2, 'Smartphone Samsung Galaxy S25 Ultra', 'Smartphone Samsung Galaxy S25 Ultra',
 'Informatique', 'Computers', 'Smartphones', 'Smartphones',
 14990.00, 1, 14990.00, 13491.00),
(3, 'Souris Razer DeathAdder Essential', 'Mouse Razer DeathAdder Essential',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 249.00, 1, 249.00, 249.00),
(4, 'Clavier MSI Vigor GK20', 'Keyboard MSI Vigor GK20',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 299.00, 1, 299.00, 239.20),
(5, 'Smartphone Xiaomi 15', 'Smartphone Xiaomi 15',
 'Informatique', 'Computers', 'Smartphones', 'Smartphones',
 7490.00, 1, 7490.00, 7115.50),
(6, 'Ordinateur portable Dell XPS 15 (2025)', 'Laptop Dell XPS 15 (2025)',
 'Informatique', 'Computers', 'Ordinateurs portables', 'Laptops',
 15990.00, 1, 15990.00, 15990.00),
(7, 'Ordinateur portable Lenovo ThinkPad X1 Carbon Gen 13',
    'Laptop Lenovo ThinkPad X1 Carbon Gen 13',
 'Informatique', 'Computers', 'Ordinateurs portables', 'Laptops',
 14490.00, 1, 14490.00, 13330.80),
(8, 'Montre connectée Apple Watch Series 10 (42mm)',
    'Smartwatch Apple Watch Series 10 (42mm)',
 'Informatique', 'Computers', 'Montres connectées', 'Smartwatches',
 3990.00, 1, 3990.00, 3192.00),
(9, 'Montre connectée Xiaomi Band 9 Pro', 'Smartwatch Xiaomi Band 9 Pro',
 'Informatique', 'Computers', 'Montres connectées', 'Smartwatches',
 890.00, 1, 890.00, 801.00),
(10, 'Chaise de bureau Ergohuman ME7ERG', 'Office Chair Ergohuman ME7ERG',
 'Maison et bureau', 'Home and Office', 'Chaises de bureau', 'Office Chairs',
 5490.00, 1, 5490.00, 5490.00),
(11, 'Chaise de bureau Secretlab Titan Evo 2022 (Regular)',
     'Gaming Chair Secretlab Titan Evo 2022 (Regular)',
 'Maison et bureau', 'Home and Office', 'Chaises de bureau', 'Office Chairs',
 3990.00, 1, 3990.00, 3391.50),
(12, 'Bureau électrique réglable FlexiSpot E7', 'Standing Desk FlexiSpot E7',
 'Maison et bureau', 'Home and Office', 'Bureaux', 'Desks',
 4990.00, 1, 4990.00, 4391.20),
(13, 'Chaussures Nike Air Max 270', 'Shoes Nike Air Max 270',
 'Mode et accessoires', 'Fashion and Accessories', 'Chaussures', 'Shoes',
 1290.00, 1, 1290.00, 1290.00),
(14, 'Chaussures Adidas Ultraboost 22', 'Shoes Adidas Ultraboost 22',
 'Mode et accessoires', 'Fashion and Accessories', 'Chaussures', 'Shoes',
 1490.00, 1, 1490.00, 1341.00),
(15, 'Sac à dos Fjällräven Kånken', 'Backpack Fjällräven Kånken',
 'Mode et accessoires', 'Fashion and Accessories', 'Sacs à dos', 'Backpacks',
 1190.00, 1, 1190.00, 1011.50),
(16, 'Parfum Dior Sauvage EDP (100ml)', 'Perfume Dior Sauvage EDP (100ml)',
 'Autres produits', 'Other Products', 'Parfums', 'Perfumes',
 1590.00, 1, 1590.00, 1590.00),
(17, 'T-shirt graphique Levi''s Batwing Logo', 'Graphic T-shirt Levi''s Batwing Logo',
 'Mode et accessoires', 'Fashion and Accessories', 'T-shirts', 'T-shirts',
 350.00, 2, 700.00, 665.00),
(18, 'Livre Deep Learning - Ian Goodfellow', 'Book Deep Learning - Ian Goodfellow',
 'Autres produits', 'Other Products', 'Livres', 'Books',
 590.00, 1, 590.00, 531.00),
(19, 'Lampe LED Hue Play Philips (pack x2)', 'LED Philips Hue Play (2-pack)',
 'Maison et bureau', 'Home and Office', 'Lampes LED', 'LED Lamps',
 1490.00, 2, 2980.00, 2682.00),
(20, 'Ordinateur portable Apple MacBook Pro 14 M4',
     'Laptop Apple MacBook Pro 14 M4',
 'Informatique', 'Computers', 'Ordinateurs portables', 'Laptops',
 19990.00, 1, 19990.00, 14992.50),
-- Commande 21 (multi)
(21, 'Ordinateur portable ASUS ROG Zephyrus G16 (2025)',
     'Laptop ASUS ROG Zephyrus G16 (2025)',
 'Informatique', 'Computers', 'Ordinateurs portables', 'Laptops',
 18990.00, 1, 18990.00, 17091.00),
(21, 'Souris MSI FORGE GM100', 'Mouse MSI FORGE GM100',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 129.00, 1, 129.00, 116.10),
(21, 'Clavier MSI Vigor GK20', 'Keyboard MSI Vigor GK20',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 299.00, 1, 299.00, 269.10),
(21, 'Casque Redragon H231 Scream', 'Headset Redragon H231 Scream',
 'Informatique', 'Computers', 'Périphériques d''entrée', 'Input Device',
 149.00, 1, 149.00, 134.10),
-- Commande 22 (multi)
(22, 'Parfum Dior Sauvage EDP (100ml)', 'Perfume Dior Sauvage EDP (100ml)',
 'Autres produits', 'Other Products', 'Parfums', 'Perfumes',
 1590.00, 1, 1590.00, 1590.00),
(22, 'Lunettes de soleil Ray-Ban Wayfarer RB2140',
     'Sunglasses Ray-Ban Wayfarer RB2140',
 'Autres produits', 'Other Products', 'Lunettes de soleil', 'Sunglasses',
 1290.00, 1, 1290.00, 1290.00),
-- Commande 23 (multi)
(23, 'Bureau d''angle IKEA Bekant', 'Corner Desk IKEA Bekant',
 'Maison et bureau', 'Home and Office', 'Bureaux', 'Desks',
 1790.00, 1, 1790.00, 1575.20),
(23, 'Chaise de bureau Hbada E3 Pro', 'Office Chair Hbada E3 Pro',
 'Maison et bureau', 'Home and Office', 'Chaises de bureau', 'Office Chairs',
 1890.00, 1, 1890.00, 1663.20),
(23, 'Lampe de bureau LED BenQ ScreenBar', 'LED Desk Lamp BenQ ScreenBar',
 'Maison et bureau', 'Home and Office', 'Lampes LED', 'LED Lamps',
 1290.00, 1, 1290.00, 1135.20),
(23, 'Tapis de gaming SteelSeries QcK Heavy XXL',
     'Gaming Desk Mat SteelSeries QcK Heavy XXL',
 'Maison et bureau', 'Home and Office', 'Tapis', 'Rugs',
 590.00, 1, 590.00, 519.20),
-- Commande 24 (multi)
(24, 'Sac à dos Nike Brasilia 9.5 (24L)', 'Backpack Nike Brasilia 9.5 (24L)',
 'Mode et accessoires', 'Fashion and Accessories', 'Sacs à dos', 'Backpacks',
 490.00, 1, 490.00, 416.50),
(24, 'Chaussures Converse Chuck Taylor All Star',
     'Shoes Converse Chuck Taylor All Star',
 'Mode et accessoires', 'Fashion and Accessories', 'Chaussures', 'Shoes',
 690.00, 1, 690.00, 586.50),
(24, 'T-shirt Nike Dri-FIT (homme)', 'T-shirt Nike Dri-FIT (men)',
 'Mode et accessoires', 'Fashion and Accessories', 'T-shirts', 'T-shirts',
 390.00, 3, 1170.00, 994.50),
-- Commande 25 (multi)
(25, 'Livre Atomic Habits - James Clear', 'Book Atomic Habits - James Clear',
 'Autres produits', 'Other Products', 'Livres', 'Books',
 290.00, 1, 290.00, 261.00),
(25, 'Livre Thinking Fast and Slow - Daniel Kahneman',
     'Book Thinking Fast and Slow - Daniel Kahneman',
 'Autres produits', 'Other Products', 'Livres', 'Books',
 250.00, 1, 250.00, 225.00),
(25, 'Cahier Leuchtturm1917 A5 (pointillé)', 'Notebook Leuchtturm1917 A5 (dotted)',
 'Autres produits', 'Other Products', 'Cahiers', 'Notebooks',
 250.00, 2, 500.00, 450.00),
(25, 'Stylo marqueur Stabilo Boss Pastel (set 6)',
     'Highlighter Stabilo Boss Pastel (set of 6)',
 'Autres produits', 'Other Products', 'Stylos', 'Pens',
 99.00, 2, 198.00, 178.20),
(25, 'Stylo roller Pilot G-2 (0.7mm, bleu)', 'Roller Pen Pilot G-2 (0.7mm, blue)',
 'Autres produits', 'Other Products', 'Stylos', 'Pens',
 29.00, 3, 87.00, 78.30);
"""

# ══════════════════════════════════════════════════════════════════════════════
#  DML — Données : 10 livraisons_detail
# ══════════════════════════════════════════════════════════════════════════════

INSERT_LIVRAISONS_DETAIL = """
INSERT INTO livraisons_detail (
    nom_client, nom_livreur, date_livraison,
    produits, quantite_totale,
    prix_total_livraison, methode_paiement,
    localisation_client, localisation_livreur,
    notes_client, statut
) VALUES
('Youssef Amrani', 'Khalid Moumen', '2026-01-23 10:30:00',
 'Clavier Logitech K120 (x1)', 1, 94.00, 'Carte Visa',
 '12 Rue Ibn Battouta, Béni Mellal 23000',
 'Entrepôt Central, Zone Industrielle Béni Mellal',
 NULL, 'Livré'),

('Fatima Zahra Bennani', 'Yassir Chraibi', '2026-01-29 14:00:00',
 'Smartphone Samsung Galaxy S25 Ultra (x1)', 1, 13541.00, 'Virement bancaire (RIB)',
 '45 Avenue Hassan II, Casablanca 20000',
 'Entrepôt Casablanca Est, Ain Sebaa',
 'Merci de sonner deux fois à l''interphone.', 'Livré'),

('Mohamed Karim Idrissi', 'Hamza Oubella', '2026-02-04 09:15:00',
 'Souris Razer DeathAdder Essential (x1)', 1, 264.00, 'Paiement à la livraison',
 '7 Rue Al Massira, Marrakech 40000',
 'Hub Logistique Marrakech, Route de Casablanca',
 NULL, 'Livré'),

('Houda El Fassi', 'Khalid Moumen', '2026-02-06 16:00:00',
 'Clavier MSI Vigor GK20 (x1)', 1, 249.20, 'Carte Mastercard',
 '3 Résidence Al Wafa, Béni Mellal 23000',
 'Entrepôt Central, Zone Industrielle Béni Mellal',
 'Laisser le colis chez le gardien si absent.', 'Livré'),

('Anas Bouhsaini', 'Saad Filali', '2026-02-08 11:00:00',
 'Smartphone Xiaomi 15 (x1)', 1, 7165.50, 'Carte Visa',
 '22 Boulevard Zerktouni, Fès 30000',
 'Entrepôt Fès, Zone Sidi Brahim',
 NULL, 'En cours'),

('Salma Oujdi', 'Yassir Chraibi', '2026-02-11 08:00:00',
 'Ordinateur portable Dell XPS 15 (2025) (x1)', 1, 16040.00, 'Virement bancaire (RIB)',
 '18 Rue Moulay Youssef, Rabat 10000',
 'Entrepôt Rabat, Route de Salé',
 'Livraison uniquement entre 9h et 12h SVP.', 'En attente'),

('Rachid Tahiri', 'Hamza Oubella', '2026-02-15 13:00:00',
 'Ordinateur portable Lenovo ThinkPad X1 Carbon Gen 13 (x1)', 1, 13380.80, 'Carte Mastercard',
 '9 Rue Ibn Rochd, Agadir 80000',
 'Hub Logistique Agadir, Quartier Industriel',
 NULL, 'Retardé'),

('Zineb Chraibi', 'Saad Filali', '2026-02-19 18:00:00',
 'Montre connectée Apple Watch Series 10 42mm (x1)', 1, 3242.00, 'Carte Visa',
 '55 Avenue Mohammed V, Tanger 90000',
 'Entrepôt Tanger, Zone Franche',
 'Annulé par le client avant expédition.', 'Annulé'),

('Ayoub El Khatib', 'Khalid Moumen', '2026-03-26 10:00:00',
 'Ordinateur portable ASUS ROG Zephyrus G16 (x1), Souris MSI FORGE GM100 (x1), Clavier MSI Vigor GK20 (x1), Casque Redragon H231 Scream (x1)',
 4, 17660.30, 'Virement bancaire (RIB)',
 '33 Quartier Hay Riad, Rabat 10100',
 'Entrepôt Rabat, Route de Salé',
 'Fragile — manipuler avec soin. Appeler avant d''arriver.', 'Livré'),

('Amina Tahiri', 'Yassir Chraibi', '2026-03-30 09:00:00',
 'Livre Atomic Habits (x1), Livre Thinking Fast and Slow (x1), Cahier Leuchtturm1917 A5 (x2), Stabilo Boss Pastel set 6 (x2), Stylo Pilot G-2 (x3)',
 9, 1242.50, 'Paiement à la livraison',
 '14 Rue Al Amal, Meknès 50000',
 'Hub Logistique Meknès, Avenue des FAR',
 'Laisser dans la boîte aux lettres si absent.', 'En cours');
"""


def run():
    print("🚀 Migration catalogue — début\n")

    with engine.connect() as conn:
        # ── 1. Créer les tables ────────────────────────────────────────────────
        print("📐 Création des tables...")
        try:
            conn.execute(text(DDL))
            conn.commit()
            print("  ✅ Tables créées (ou déjà existantes)\n")
        except Exception as e:
            print(f"  ❌ DDL error : {e}\n")
            return

        # ── 2. Insérer les commandes catalogue ─────────────────────────────────
        print("📦 Insertion des 25 commandes catalogue...")
        try:
            conn.execute(text(INSERT_COMMANDES_CATALOGUE))
            conn.commit()
            print("  ✅ 25 commandes insérées\n")
        except Exception as e:
            print(f"  ❌ Commandes error : {e}\n")

        # ── 3. Insérer les lignes commandes catalogue ──────────────────────────
        print("📋 Insertion des lignes de commandes catalogue...")
        try:
            conn.execute(text(INSERT_LIGNES_CATALOGUE))
            conn.commit()
            print("  ✅ Lignes insérées\n")
        except Exception as e:
            print(f"  ❌ Lignes error : {e}\n")

        # ── 4. Insérer les livraisons detail ───────────────────────────────────
        print("🚚 Insertion des 10 livraisons detail...")
        try:
            conn.execute(text(INSERT_LIVRAISONS_DETAIL))
            conn.commit()
            print("  ✅ 10 livraisons insérées\n")
        except Exception as e:
            print(f"  ❌ Livraisons error : {e}\n")

    print("✅ Migration terminée !")
    print("👉 Redémarre le serveur : uvicorn app.main:app --reload")


if __name__ == "__main__":
    run()