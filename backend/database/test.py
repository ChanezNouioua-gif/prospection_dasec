import sqlite3
from repository import EntrepriseRepository

conn = sqlite3.connect("data/dasec_prospection.db")
conn.row_factory = sqlite3.Row
repo = EntrepriseRepository(conn)
repo.s_assurer_schema_a_jour()
print("Schéma à jour.")