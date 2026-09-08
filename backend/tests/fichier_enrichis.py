import sqlite3
from pathlib import Path

# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "dasec_prospection.db"

print(f"DB utilisée : {DB_PATH}")

if not DB_PATH.exists():
    raise FileNotFoundError(f"Base introuvable : {DB_PATH}")


# =========================
# CONNEXION
# =========================

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


# =========================
# LISTE DES TABLES
# =========================

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")

tables = cursor.fetchall()

print("\n========== TABLES ==========")

for table in tables:
    print("-", table[0])


# =========================
# STRUCTURE DES TABLES
# =========================

for (table_name,) in tables:

    print(f"\n========== {table_name} ==========")

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    for column in columns:
        # cid, name, type, notnull, default, pk
        print(f"- {column[1]} ({column[2]})")


# =========================
# NOMBRE DE LIGNES
# =========================

print("\n========== NOMBRE DE LIGNES ==========")

for (table_name,) in tables:

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]

    print(f"{table_name}: {count}")


conn.close()