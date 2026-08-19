#!/usr/bin/env python3
"""
Diagnostic avant geocoding offline (point-in-polygon) des wilayas.
Lance ce script à la racine de ton projet, là où se trouve ta DB.

Usage:
    python check_setup.py [chemin_vers_ta_db.sqlite]

Si aucun chemin n'est donné, il cherche automatiquement les .db/.sqlite
dans le dossier courant et sous-dossiers.
"""

import sqlite3
import sys
import os
import glob
import json

def find_db_files():
    patterns = ["**/*.db", "**/*.sqlite", "**/*.sqlite3"]
    found = []
    for p in patterns:
        found.extend(glob.glob(p, recursive=True))
    # Exclut les trucs évidents à ignorer
    return [f for f in found if "node_modules" not in f and ".venv" not in f]


def inspect_db(db_path):
    print(f"\n{'='*70}")
    print(f"DB: {db_path}")
    print(f"{'='*70}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Liste des tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nTables trouvées ({len(tables)}): {tables}")

    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        col_names = [c[1] for c in cols]

        # On ne détaille que les tables qui ressemblent à des établissements
        lat_like = [c for c in col_names if "lat" in c.lower()]
        lon_like = [c for c in col_names if "lon" in c.lower() or "lng" in c.lower()]
        wilaya_like = [c for c in col_names if "wilaya" in c.lower()]

        if lat_like or lon_like or wilaya_like:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total = cur.fetchone()[0]
            print(f"\n--- Table: {table} ({total} lignes) ---")
            print(f"  Colonnes: {col_names}")
            print(f"  Colonnes lat détectées: {lat_like}")
            print(f"  Colonnes lon détectées: {lon_like}")
            print(f"  Colonnes wilaya détectées: {wilaya_like}")

            if lat_like and lon_like:
                latc, lonc = lat_like[0], lon_like[0]
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {latc} IS NOT NULL AND {lonc} IS NOT NULL")
                with_coords = cur.fetchone()[0]
                print(f"  Lignes avec coordonnées valides: {with_coords}/{total}")

                cur.execute(f"SELECT {latc}, {lonc} FROM {table} WHERE {latc} IS NOT NULL LIMIT 3")
                samples = cur.fetchall()
                print(f"  Échantillon coords: {samples}")

            if wilaya_like:
                wc = wilaya_like[0]
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {wc} IS NULL OR {wc} = ''")
                missing = cur.fetchone()[0]
                print(f"  Lignes SANS wilaya ({wc}): {missing}/{total}")

                cur.execute(f"SELECT DISTINCT {wc} FROM {table} WHERE {wc} IS NOT NULL LIMIT 10")
                distinct_vals = [r[0] for r in cur.fetchall()]
                print(f"  Exemples de valeurs wilaya existantes: {distinct_vals}")

    conn.close()


def check_boundary_files():
    print(f"\n{'='*70}")
    print("Recherche de fichiers de limites administratives (GeoJSON/shapefile)")
    print(f"{'='*70}")
    patterns = ["**/*.geojson", "**/*wilaya*", "**/*.shp", "**/*admin*level*"]
    found = set()
    for p in patterns:
        for f in glob.glob(p, recursive=True):
            if "node_modules" not in f and ".venv" not in f:
                found.add(f)
    if found:
        print(f"Fichiers potentiellement utiles trouvés: {sorted(found)}")
    else:
        print("Aucun fichier de limites de wilayas trouvé localement.")
        print("-> Il faudra soit en extraire un depuis algeria-latest.osm.pbf")
        print("   (admin_level=4 via osmium/ogr2ogr), soit en récupérer un")
        print("   depuis une source publique (ex: GADM, HDX, OSM Algeria).")


def check_libs():
    print(f"\n{'='*70}")
    print("Vérification des librairies Python nécessaires")
    print(f"{'='*70}")
    for lib in ["geopandas", "shapely", "fiona", "pyproj"]:
        try:
            __import__(lib)
            print(f"  ✓ {lib} installé")
        except ImportError:
            print(f"  ✗ {lib} MANQUANT -> pip install {lib}")


def check_pbf():
    print(f"\n{'='*70}")
    print("Recherche du fichier algeria-latest.osm.pbf")
    print(f"{'='*70}")
    found = glob.glob("**/algeria-latest.osm.pbf", recursive=True)
    if found:
        for f in found:
            size_mb = os.path.getsize(f) / 1e6
            print(f"  Trouvé: {f} ({size_mb:.1f} MB)")
    else:
        print("  Non trouvé dans le dossier courant.")

    # Vérifie si osmium est dispo (utile pour extraire les boundaries)
    osmium_ok = os.system("which osmium > /dev/null 2>&1") == 0
    ogr2ogr_ok = os.system("which ogr2ogr > /dev/null 2>&1") == 0
    print(f"  osmium installé: {'✓' if osmium_ok else '✗ (sudo apt install osmium-tool)'}")
    print(f"  ogr2ogr installé: {'✓' if ogr2ogr_ok else '✗ (sudo apt install gdal-bin)'}")


if __name__ == "__main__":
    print(f"Dossier courant (cwd): {os.getcwd()}\n")

    # Filtre les arguments type Jupyter (-f=...kernel.json) qui ne sont pas un vrai chemin DB
    real_args = [a for a in sys.argv[1:] if not a.startswith("-") and os.path.splitext(a)[1] in (".db", ".sqlite", ".sqlite3")]

    if real_args:
        db_paths = real_args
    else:
        db_paths = find_db_files()
        if not db_paths:
            print("Aucune DB trouvée automatiquement dans ce dossier.")
            print("-> Assure-toi de lancer ce script depuis la racine de ton projet")
            print("   (là où se trouve ta base .db/.sqlite), avec: python check_setup.py")
            print("-> Ou lance avec le chemin explicite: python check_setup.py chemin\\vers\\ta.db")
        else:
            print(f"DB(s) trouvée(s) automatiquement: {db_paths}")

    for db_path in db_paths:
        try:
            inspect_db(db_path)
        except Exception as e:
            print(f"Erreur en inspectant {db_path}: {e}")

    check_boundary_files()
    check_pbf()
    check_libs()

    print(f"\n{'='*70}")
    print("RÉSUMÉ - envoie-moi juste la sortie de ce script")
    print(f"{'='*70}")