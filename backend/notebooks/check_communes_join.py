#!/usr/bin/env python3
"""
Vérifie si les lignes sans wilaya_name peuvent être résolues via un JOIN
sur commune_id (ou fuzzy-match sur commune_brute) avant de partir sur du
point-in-polygon géographique (plus lourd).

Usage: python check_commune_join.py
(à lancer depuis backend/, ou ajuste DB_PATH ci-dessous)
"""

import sqlite3

DB_PATH = "data/dasec_prospection.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("="*70)
print("1. Lignes sans wilaya_name : combien ont un commune_id rempli ?")
print("="*70)
cur.execute("""
    SELECT COUNT(*) FROM entreprises
    WHERE (wilaya_name IS NULL OR wilaya_name = '')
""")
total_missing = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM entreprises
    WHERE (wilaya_name IS NULL OR wilaya_name = '')
      AND commune_id IS NOT NULL
""")
with_commune_id = cur.fetchone()[0]

print(f"Total sans wilaya: {total_missing}")
print(f"  -> dont avec commune_id rempli: {with_commune_id}")
print(f"  -> dont commune_id résolvable via JOIN vers communes.wilaya_name")

# Vérifie que le JOIN fonctionne réellement (commune_id valide = existe dans communes.id)
cur.execute("""
    SELECT COUNT(*) FROM entreprises e
    JOIN communes c ON e.commune_id = c.id
    WHERE (e.wilaya_name IS NULL OR e.wilaya_name = '')
""")
joinable = cur.fetchone()[0]
print(f"  -> JOIN valide (commune_id existe dans communes.id): {joinable}")

print()
print("="*70)
print("2. Pour le reste, commune_brute est-il exploitable (fuzzy match) ?")
print("="*70)
cur.execute("""
    SELECT COUNT(*) FROM entreprises e
    WHERE (e.wilaya_name IS NULL OR e.wilaya_name = '')
      AND (e.commune_id IS NULL OR NOT EXISTS (SELECT 1 FROM communes c WHERE c.id = e.commune_id))
      AND e.commune_brute IS NOT NULL AND e.commune_brute != ''
""")
with_commune_brute = cur.fetchone()[0]
print(f"Lignes restantes (sans wilaya, sans commune_id valide) avec commune_brute rempli: {with_commune_brute}")

cur.execute("""
    SELECT commune_brute FROM entreprises e
    WHERE (e.wilaya_name IS NULL OR e.wilaya_name = '')
      AND (e.commune_id IS NULL OR NOT EXISTS (SELECT 1 FROM communes c WHERE c.id = e.commune_id))
      AND e.commune_brute IS NOT NULL AND e.commune_brute != ''
    LIMIT 15
""")
samples = [r[0] for r in cur.fetchall()]
print(f"Échantillon de commune_brute: {samples}")

print()
print("="*70)
print("3. Pour ce qui reste après ça, combien ont des coordonnées lat/lon ?")
print("="*70)
cur.execute("""
    SELECT COUNT(*) FROM entreprises e
    WHERE (e.wilaya_name IS NULL OR e.wilaya_name = '')
      AND (e.commune_id IS NULL OR NOT EXISTS (SELECT 1 FROM communes c WHERE c.id = e.commune_id))
      AND (e.commune_brute IS NULL OR e.commune_brute = '')
      AND e.latitude IS NOT NULL AND e.longitude IS NOT NULL
""")
need_geo = cur.fetchone()[0]
print(f"Lignes qui nécessiteront un vrai point-in-polygon géographique: {need_geo}")

cur.execute("""
    SELECT COUNT(*) FROM entreprises e
    WHERE (e.wilaya_name IS NULL OR e.wilaya_name = '')
      AND (e.commune_id IS NULL OR NOT EXISTS (SELECT 1 FROM communes c WHERE c.id = e.commune_id))
      AND (e.commune_brute IS NULL OR e.commune_brute = '')
      AND (e.latitude IS NULL OR e.longitude IS NULL)
""")
no_hope = cur.fetchone()[0]
print(f"Lignes sans AUCUNE info exploitable (ni commune_id, ni commune_brute, ni coords): {no_hope}")

conn.close()

print()
print("="*70)
print("RÉSUMÉ - colle-moi cette sortie")
print("="*70)
print(f"Total sans wilaya:              {total_missing}")
print(f"Résolvable par JOIN commune_id: {joinable}")
print(f"Résolvable par fuzzy commune_brute (à valider): {with_commune_brute}")
print(f"Nécessite point-in-polygon:      {need_geo}")
print(f"Perdu (aucune info):             {no_hope}")