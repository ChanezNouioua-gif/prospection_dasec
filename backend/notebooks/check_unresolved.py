#!/usr/bin/env python3
"""
ÉTAPE 3 (optionnelle) : inspecte les lignes toujours sans wilaya après le
point-in-polygon strict, et tente une résolution par distance (wilaya la
plus proche) pour les cas où le point est juste à côté d'une frontière
(gap de précision du polygone OSM) plutôt que réellement hors d'Algérie.

Usage:
    python check_unresolved.py                    # inspecte seulement
    python check_unresolved.py --apply-nearest 5000  # applique si <5km de la wilaya la plus proche
"""

import sqlite3
import json
import argparse
from shapely.geometry import shape, Point
from shapely.ops import nearest_points
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
        geom = shape(feature["geometry"])
        polygons.append((name, geom))
    return polygons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-nearest", type=float, default=None,
                         help="Si fourni, assigne la wilaya la plus proche pour les points à moins de N mètres (approx, en degrés*111000)")
    args = parser.parse_args()

    polygons = load_wilaya_polygons()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nom, latitude, longitude FROM entreprises
        WHERE (wilaya_name IS NULL OR wilaya_name = '')
          AND latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f"{len(rows)} lignes toujours sans wilaya.\n")

    resolved_by_distance = 0
    for id_, nom, lat, lon in rows:
        point = Point(lon, lat)
        best_name, best_dist_deg = None, float("inf")
        for name, geom in polygons:
            d = point.distance(geom)  # 0 si dedans, sinon distance en degrés
            if d < best_dist_deg:
                best_dist_deg = d
                best_name = name

        dist_m = best_dist_deg * 111_000  # approximation grossière (1° ≈ 111km)
        flag = ""
        if dist_m < 1000:
            flag = "  <- très proche (probable gap de précision du polygone)"
        elif dist_m > 50_000:
            flag = "  <- LOIN (coordonnées probablement fausses / hors Algérie)"

        print(f"  id={id_:6} | {nom[:35]:35} | ({lat:.4f}, {lon:.4f}) -> plus proche: {best_name} (~{dist_m/1000:.1f} km){flag}")

        if args.apply_nearest is not None and dist_m <= args.apply_nearest:
            cur.execute("UPDATE entreprises SET wilaya_name = ? WHERE id = ?", (best_name, id_))
            resolved_by_distance += 1

    if args.apply_nearest is not None:
        conn.commit()
        print(f"\n{resolved_by_distance} lignes résolues par proximité (<{args.apply_nearest}m) et écrites en DB.")
    else:
        print(f"\nAucune écriture (mode inspection). Relance avec --apply-nearest 3000 (ex: 3km)")
        print("pour résoudre automatiquement les cas proches d'une frontière.")

    conn.close()


if __name__ == "__main__":
    main()
    