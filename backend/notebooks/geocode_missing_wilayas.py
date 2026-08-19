#!/usr/bin/env python3
"""
ÉTAPE 2 : utilise algeria_wilayas.geojson (généré par fetch_wilaya_boundaries.py)
pour assigner wilaya_name aux lignes de `entreprises` qui ont des coordonnées
lat/lon mais pas de wilaya_name, via point-in-polygon (shapely).

Comme d'habitude : d'abord un DRY RUN sur un petit batch pour valider, puis
le run complet une fois que le mapping te semble correct.

Installation requise (dans ton venv) :
    pip install shapely

Usage:
    python geocode_missing_wilayas.py --dry-run          # teste sur 30 lignes, n'écrit rien
    python geocode_missing_wilayas.py --apply             # écrit en DB pour de vrai
"""

import sqlite3
import json
import argparse
from shapely.geometry import shape, Point
from shapely.prepared import prep

DB_PATH = "data/dasec_prospection.db"
GEOJSON_PATH = "algeria_wilayas.geojson"


def load_wilaya_polygons():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    polygons = []
    for feature in geojson["features"]:
        tags = feature.get("properties", {}).get("tags", {})
        name = tags.get("name:fr") or tags.get("name")
        if not name:
            continue
        try:
            geom = shape(feature["geometry"])
        except Exception as e:
            print(f"  Skip {name}: géométrie invalide ({e})")
            continue
        polygons.append((name, geom, prep(geom)))  # prep() accélère les tests répétés

    print(f"{len(polygons)} polygones de wilayas chargés.")
    return polygons


def find_wilaya(lat, lon, polygons):
    point = Point(lon, lat)  # attention: shapely = (x=lon, y=lat)
    for name, geom, prepared in polygons:
        if prepared.contains(point):
            return name
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Teste sur 30 lignes sans écrire en DB")
    parser.add_argument("--apply", action="store_true", help="Applique pour de vrai en DB")
    parser.add_argument("--limit", type=int, default=30, help="Nombre de lignes pour le dry-run (défaut 30)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Précise --dry-run (test) ou --apply (écriture réelle).")
        return

    polygons = load_wilaya_polygons()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    where_clause = """
        (wilaya_name IS NULL OR wilaya_name = '')
        AND latitude IS NOT NULL AND longitude IS NOT NULL
    """

    if args.dry_run:
        cur.execute(f"SELECT id, nom, latitude, longitude FROM entreprises WHERE {where_clause} LIMIT {args.limit}")
        rows = cur.fetchall()
        print(f"\n=== DRY RUN sur {len(rows)} lignes (rien n'est écrit en DB) ===\n")
        found, not_found = 0, 0
        for id_, nom, lat, lon in rows:
            wilaya = find_wilaya(lat, lon, polygons)
            status = wilaya if wilaya else "❌ AUCUNE WILAYA TROUVÉE"
            print(f"  id={id_:6} | {nom[:40]:40} | ({lat:.4f}, {lon:.4f}) -> {status}")
            if wilaya:
                found += 1
            else:
                not_found += 1
        print(f"\nRésultat: {found}/{len(rows)} résolues, {not_found} non résolues.")
        print("Si ça te semble correct, relance avec --apply pour traiter toutes les lignes.")

    elif args.apply:
        cur.execute(f"SELECT COUNT(*) FROM entreprises WHERE {where_clause}")
        total = cur.fetchone()[0]
        print(f"\n=== APPLY sur {total} lignes ===\n")

        cur.execute(f"SELECT id, latitude, longitude FROM entreprises WHERE {where_clause}")
        rows = cur.fetchall()

        updated, skipped = 0, 0
        for i, (id_, lat, lon) in enumerate(rows, 1):
            wilaya = find_wilaya(lat, lon, polygons)
            if wilaya:
                cur.execute("UPDATE entreprises SET wilaya_name = ? WHERE id = ?", (wilaya, id_))
                updated += 1
            else:
                skipped += 1

            if i % 500 == 0:
                print(f"  ... {i}/{total} traitées ({updated} résolues, {skipped} échouées)")
                conn.commit()  # commit périodique pour ne pas tout perdre en cas d'interruption

        conn.commit()
        print(f"\nTerminé: {updated} lignes mises à jour, {skipped} non résolues (hors polygones, ex: mer/frontière).")

    conn.close()


if __name__ == "__main__":
    main()