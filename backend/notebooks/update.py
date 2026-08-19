import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


DB_PATH = "data/dasec_prospection.db"


def s_assurer_schema_a_jour():
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute("PRAGMA table_info(entreprises)")
    colonnes_existantes = {row[1] for row in cursor.fetchall()}

    nouvelles_colonnes = {
        "contact_email_personnel": "TEXT",
        "contact_telephone_personnel": "TEXT",
        "contact_linkedin_personnel": "TEXT",
    }

    for colonne, type_colonne in nouvelles_colonnes.items():
        if colonne not in colonnes_existantes:
            conn.execute(
                f"ALTER TABLE entreprises ADD COLUMN {colonne} {type_colonne}"
            )
            print(f"✅ Colonne ajoutée : {colonne}")
        else:
            print(f"ℹ️ Colonne déjà présente : {colonne}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    s_assurer_schema_a_jour()