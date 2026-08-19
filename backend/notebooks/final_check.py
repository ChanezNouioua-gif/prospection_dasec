import sqlite3

conn = sqlite3.connect("data/dasec_prospection.db")
conn.row_factory = sqlite3.Row

cursor = conn.execute("""
    SELECT id, nom, wilaya_name, critic_valide
    FROM entreprises
    WHERE sous_secteur = "cabinet d'avocat"
      AND (critic_valide IS NULL OR critic_valide = 0)
""")

lignes = cursor.fetchall()

ids = [row["id"] for row in lignes]

print(f"{len(ids)} établissements ycabinet d'avocat avec critic_valide non validé.")
print(ids)