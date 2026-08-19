#!/usr/bin/env python3
"""
ÉTAPE 1 : télécharge les limites administratives des wilayas d'Algérie
(admin_level=4 dans OSM) depuis l'API Overpass, et les sauvegarde en
GeoJSON local pour le point-in-polygon.

Pourquoi Overpass plutôt qu'un fichier tiers ?
- Les GeoJSON publics trouvés (fr33dz, geoBoundaries) datent d'avant le
  redécoupage de 2019 et ne couvrent que 48/58 wilayas.
- Overpass interroge directement la donnée OSM à jour, la même source
  que ton algeria-latest.osm.pbf.

Installation requise (dans ton venv) :
    pip install requests osm2geojson shapely

Usage:
    python fetch_wilaya_boundaries.py
"""

import requests
import json
import time

# Plusieurs miroirs en cas de 406 / surcharge sur le serveur principal
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

QUERY = """
[out:json][timeout:180];
area["ISO3166-1"="DZ"][admin_level=2]->.dz;
relation(area.dz)["boundary"="administrative"]["admin_level"="4"];
out geom;
"""

OUTPUT_FILE = "algeria_wilayas.geojson"

# Overpass renvoie souvent 406 si aucun User-Agent n'est fourni
HEADERS = {
    "User-Agent": "ProspectionAI-DASEC/1.0 (script de geocoding wilayas, usage interne)"
}


def fetch_overpass_data(retries=3):
    for url in OVERPASS_URLS:
        for attempt in range(1, retries + 1):
            print(f"[{url}] Tentative {attempt}/{retries}...")
            try:
                resp = requests.post(url, data={"data": QUERY}, headers=HEADERS, timeout=200)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"  Échec: {e}")
                if attempt < retries:
                    print("  Nouvelle tentative dans 10s...")
                    time.sleep(10)
        print(f"  Abandon de ce miroir, on essaie le suivant...\n")
    raise RuntimeError("Impossible de récupérer les données depuis Overpass API (tous les miroirs ont échoué).")


def main():
    try:
        import osm2geojson
    except ImportError:
        print("ERREUR: le package 'osm2geojson' n'est pas installé.")
        print("Lance: pip install osm2geojson")
        return

    data = fetch_overpass_data()

    n_relations = len(data.get("elements", []))
    print(f"\n{n_relations} relations admin_level=4 récupérées depuis OSM.")

    print("Conversion en GeoJSON (assemblage des polygones)...")
    geojson = osm2geojson.json2geojson(data)

    all_features = geojson.get("features", [])
    print(f"{len(all_features)} polygones bruts assemblés.")

    # OSM Algérie mélange admin_level=4 entre vraies wilayas et certaines daïras.
    # Pire : des contributeurs OSM ont tagué des daïras (Aflou, Barika, Messaad,
    # Bir El Ater, etc.) avec des codes ISO3166-2 factices DZ-59 à DZ-69, qui
    # n'existent pas dans la norme officielle (elle s'arrête à DZ-58, les 58
    # wilayas actuelles). On restreint donc strictement à DZ-01..DZ-58.
    import re
    iso_pattern = re.compile(r"^DZ-(\d{2})$")

    filtered = []
    rejected = []
    for f in all_features:
        tags = f.get("properties", {}).get("tags", {})
        iso = tags.get("ISO3166-2", "")
        name = tags.get("name:fr") or tags.get("name") or "???"
        m = iso_pattern.match(iso)
        if m and 1 <= int(m.group(1)) <= 58:
            filtered.append(f)
        else:
            rejected.append((name, iso))

    print(f"\n{len(filtered)} polygones avec un tag ISO3166-2 valide (DZ-XX).")
    if rejected:
        print(f"{len(rejected)} rejetés (probablement des daïras, pas des wilayas):")
        for name, iso in rejected:
            print(f"  - {name} (ISO3166-2={iso or 'absent'})")

    # Si le filtre ISO3166-2 donne un résultat crédible, on l'utilise. Sinon
    # on garde tout et on prévient — mieux vaut trop de données à trier
    # manuellement que d'en perdre silencieusement.
    if 50 <= len(filtered) <= 58:
        features = filtered
        print(f"\n✓ Utilisation des {len(features)} polygones filtrés par ISO3166-2.")
    else:
        features = all_features
        print(f"\n⚠️  Le filtre ISO3166-2 donne {len(filtered)} résultats (attendu ~58).")
        print("   On garde TOUS les polygones bruts pour ne rien perdre — il faudra")
        print("   dédupliquer/filtrer manuellement avant le geocoding. Regarde la")
        print("   liste des noms ci-dessous.")

    # Affiche les noms retenus pour vérification rapide
    names = []
    for f in features:
        tags = f.get("properties", {}).get("tags", {})
        name = tags.get("name:fr") or tags.get("name") or "???"
        iso = tags.get("ISO3166-2", "?")
        names.append(f"{name} ({iso})")
    print("\nWilayas retenues:")
    for n in sorted(names):
        print(f"  - {n}")

    if len(features) < 58:
        print(f"\n⚠️  ATTENTION: seulement {len(features)}/58 wilayas trouvées.")
        print("   Certaines wilayas du Sud (créées en 2019) pourraient manquer")
        print("   dans OSM. Vérifie la liste ci-dessus par rapport aux 58 wilayas")
        print("   officielles avant de continuer.")
    else:
        print(f"\n✓ {len(features)}/58 wilayas trouvées, c'est bon.")

    output_geojson = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_geojson, f, ensure_ascii=False)

    print(f"\nSauvegardé dans: {OUTPUT_FILE}")
    print("Étape suivante: lance geocode_missing_wilayas.py")


if __name__ == "__main__":
    main()