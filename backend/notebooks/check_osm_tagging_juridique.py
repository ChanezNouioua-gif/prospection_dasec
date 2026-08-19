#!/usr/bin/env python3
"""
Diagnostic : cherche dans OSM Algérie tous les nodes/ways dont le NOM contient
des mots-clés liés à notaire/avocat/comptable, indépendamment de leur tag
"office=...", pour voir comment ils sont réellement tagués sur le terrain.

Objectif : savoir si le filtre actuel (office=notary strict) rate des
établissements parce qu'ils sont tagués autrement (office=yes, pas de tag
office du tout, shop=..., etc.) avant d'élargir match() à l'aveugle.

Usage:
    python check_osm_tagging_juridique.py
"""

import requests
import json
import time

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

HEADERS = {
    "User-Agent": "ProspectionAI-DASEC/1.0 (diagnostic tagging OSM, usage interne)"
}

# Mots-clés (FR + AR) pour chaque profession, recherchés dans le nom peu importe le tag
KEYWORDS = {
    "notaire": ["notaire", "notary", "موثق"],
    "cabinet d'avocat": ["avocat", "lawyer", "محام"],
    "cabinet comptable": ["comptable", "accountant", "محاسب", "expert-comptable", "expert comptable"],
}


def build_query(keywords: list[str]) -> str:
    regex = "|".join(keywords)
    return f"""
    [out:json][timeout:120];
    area["ISO3166-1"="DZ"][admin_level=2]->.dz;
    (
      node["name"~"{regex}", i](area.dz);
      way["name"~"{regex}", i](area.dz);
    );
    out tags;
    """


def fetch(query: str, retries=3):
    for url in OVERPASS_URLS:
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=150)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"  [{url}] échec ({e}), nouvelle tentative...")
                time.sleep(5)
    raise RuntimeError("Tous les miroirs Overpass ont échoué.")


def main():
    for profession, keywords in KEYWORDS.items():
        print("="*70)
        print(f"{profession.upper()}  (mots-clés: {keywords})")
        print("="*70)

        query = build_query(keywords)
        data = fetch(query)
        elements = data.get("elements", [])
        print(f"{len(elements)} éléments trouvés avec ce nom, peu importe leurs tags.\n")

        # Compte la distribution des tags "office"/"shop"/"amenity" trouvés
        tag_distribution = {}
        exemples_sans_office_correct = []

        for el in elements:
            tags = el.get("tags", {})
            office_val = tags.get("office")
            key = f"office={office_val}" if office_val else "(pas de tag office)"
            tag_distribution[key] = tag_distribution.get(key, 0) + 1

            if office_val not in ("notary", "lawyer", "accountant"):
                exemples_sans_office_correct.append(tags.get("name", "???"))

        print("Distribution des tags 'office' trouvés :")
        for k, v in sorted(tag_distribution.items(), key=lambda x: -x[1]):
            print(f"  {v:4}x  {k}")

        if exemples_sans_office_correct:
            print(f"\n{len(exemples_sans_office_correct)} établissements NE seraient PAS")
            print("capturés par le filtre actuel (office=notary/lawyer/accountant strict).")
            print("Exemples de noms concernés :")
            for nom in exemples_sans_office_correct[:15]:
                print(f"  - {nom}")

        print()


if __name__ == "__main__":
    main()