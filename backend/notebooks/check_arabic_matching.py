#!/usr/bin/env python3
"""
Vérifie s'il existe des noms de communes en arabe dans la table `communes`
(ce qui permettrait un matching local direct), et liste les valeurs
uniques de commune_brute à résoudre pour éviter les appels redondants.

Usage: python check_arabic_matching.py
"""

import sqlite3

DB_PATH = "data/dasec_prospection.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("="*70)
print("1. La table communes a-t-elle des colonnes en arabe ?")
print("="*70)
cur.execute("PRAGMA table_info(communes)")
cols = cur.fetchall()
print("Colonnes:", [c[1] for c in cols])

cur.execute("SELECT commune_name, daira_name, wilaya_name FROM communes LIMIT 5")
for row in cur.fetchall():
    print(" ", row)

print()
print("="*70)
print("2. Valeurs uniques de commune_brute à résoudre")
print("="*70)
cur.execute("""
    SELECT commune_brute, COUNT(*) as n
    FROM entreprises
    WHERE (wilaya_name IS NULL OR wilaya_name = '')
      AND commune_brute IS NOT NULL AND commune_brute != ''
    GROUP BY commune_brute
    ORDER BY n DESC
""")
rows = cur.fetchall()
print(f"{len(rows)} valeurs UNIQUES de commune_brute (au lieu de 802 lignes brutes).")
print("\nTop 20 les plus fréquentes:")
for val, n in rows[:20]:
    print(f"  {n:3}x  {val}")

conn.close()