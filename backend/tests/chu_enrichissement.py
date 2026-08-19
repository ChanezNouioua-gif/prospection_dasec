import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlite3
from database.repository import EntrepriseRepository

conn = sqlite3.connect("data/dasec_prospection.db")
conn.row_factory = sqlite3.Row
repo = EntrepriseRepository(conn)
repo.s_assurer_schema_a_jour()
print("Schéma à jour.")

cursor = conn.execute("PRAGMA table_info(entreprises)")
colonnes = [row["name"] for row in cursor.fetchall()]
print("date_ajout_crm" in colonnes)