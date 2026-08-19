import sqlite3
from backend.database.repository import EntrepriseRepository

conn = sqlite3.connect("data/dasec_prospection.db")
repo = EntrepriseRepository(conn)
repo.s_assurer_schema_a_jour()
print("Schéma à jour.")