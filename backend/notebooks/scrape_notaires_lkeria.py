#!/usr/bin/env python3
"""
Scrape l'annuaire des notaires de lkeria.com (48 wilayas, plusieurs pages
chacune) et insère les nouveaux notaires dans `entreprises`.

Structure confirmée par inspection HTML :
  - Une fiche = <article class="hentry"> avec <h3>Notaire NOM</h3>,
    un lien vers Notaire-NOM-ID.html, et 4 <li> : téléphone (fa-phone),
    fax (fa-tablet), email (fa-envelope), adresse ("@ :...").
  - Pagination : notaire-{slug}-{code}.html (page 1), puis
    notaire-{slug}-{code}-{N}.html pour les pages suivantes (2, 3, ...).
  - Page d'index (Notaire-Algerie.html) donne la liste des 48 wilayas,
    leur slug, code, et nombre total de notaires.

Usage:
    python scrape_notaires_lkeria.py --dry-run             # teste sur 2 wilayas, n'écrit rien
    python scrape_notaires_lkeria.py --apply                # scrape tout et insère en DB
"""

import re
import time
import sqlite3
import argparse
import requests
from bs4 import BeautifulSoup

DB_PATH = "data/dasec_prospection.db"
INDEX_URL = "https://www.lkeria.com/Notaire-Algerie.html"
BASE = "https://www.lkeria.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DELAI_ENTRE_REQUETES_SEC = 1.0  # politesse envers le serveur


def recuperer_liste_wilayas() -> list[dict]:
    """Parse la page d'index pour extraire (slug, code, nom, total) par wilaya."""
    r = requests.get(INDEX_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    wilayas = []
    for a in soup.find_all("a", href=re.compile(r"^notaire-[a-z0-9\-]+-\d{2}\.html$")):
        href = a["href"]
        m = re.match(r"notaire-([a-z0-9\-]+)-(\d{2})\.html", href)
        if not m:
            continue
        slug, code = m.group(1), m.group(2)
        texte = a.get_text(strip=True)  # ex: "Adrar (1)"
        m2 = re.match(r"(.+?)\s*\((\d+)\)", texte)
        nom_wilaya = m2.group(1) if m2 else texte
        total = int(m2.group(2)) if m2 else None
        wilayas.append({"slug": slug, "code": code, "nom": nom_wilaya, "total": total, "url_page1": BASE + href})

    return wilayas


def extraire_fiches(html: str) -> list[dict]:
    """Extrait toutes les fiches notaires d'une page (structure confirmée)."""
    soup = BeautifulSoup(html, "html.parser")
    fiches = []

    for article in soup.find_all("article", class_="hentry"):
        h3 = article.find("h3")
        nom = h3.get_text(strip=True).replace("Notaire", "", 1).strip() if h3 else None

        lien = article.find("a", class_="content-thumb")
        source_id = None
        if lien and lien.get("href"):
            m = re.search(r"-(\d+)\.html$", lien["href"])
            source_id = f"lkeria/{m.group(1)}" if m else None

        telephone = fax = email = adresse = None
        for li in article.find_all("li"):
            icone = li.find("i")
            classe = icone.get("class", []) if icone else []
            texte = li.get_text(strip=True)
            texte = texte.lstrip("@").lstrip(":").strip()
            if "fa-phone" in classe:
                telephone = texte or None
            elif "fa-tablet" in classe:
                fax = texte or None
            elif "fa-envelope" in classe:
                email = texte or None
            elif texte and not classe:
                adresse = texte or None

        if telephone == "-":
            telephone = None
        if fax == "-":
            fax = None

        if nom:
            fiches.append({
                "source_id": source_id,
                "nom": nom,
                "telephone": telephone,
                "telephone2": fax,
                "email": email,
                "adresse": adresse,
            })

    return fiches


def url_page(wilaya: dict, numero_page: int) -> str:
    if numero_page == 1:
        return wilaya["url_page1"]
    return f"{BASE}notaire-{wilaya['slug']}-{wilaya['code']}-{numero_page}.html"


def scraper_wilaya(wilaya: dict) -> list[dict]:
    toutes_fiches = []
    page = 1
    while True:
        url = url_page(wilaya, page)
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"    page {page} : erreur réseau ({e}), arrêt pour cette wilaya")
            break

        if r.status_code != 200:
            break

        fiches = extraire_fiches(r.text)
        if not fiches:
            break

        toutes_fiches.extend(fiches)
        print(f"    page {page} : {len(fiches)} fiches (total cumulé : {len(toutes_fiches)})")

        if wilaya["total"] and len(toutes_fiches) >= wilaya["total"]:
            break

        page += 1
        time.sleep(DELAI_ENTRE_REQUETES_SEC)

        if page > 20:
            print("    garde-fou : plus de 20 pages, arrêt forcé (vérifier manuellement)")
            break

    return toutes_fiches


def inserer_en_db(wilaya_nom: str, fiches: list[dict], conn) -> tuple[int, int]:
    cur = conn.cursor()
    inseres, doublons = 0, 0

    for f in fiches:
        cur.execute("SELECT id FROM entreprises WHERE source = 'lkeria' AND source_id = ?", (f["source_id"],))
        if cur.fetchone():
            doublons += 1
            continue

        cur.execute("""
            INSERT INTO entreprises
                (nom, secteur, sous_secteur, telephone, telephone2, email, adresse,
                 wilaya_name, source, source_id, statut)
            VALUES (?, 'juridique', 'notaire', ?, ?, ?, ?, ?, 'lkeria', ?, 'collecte')
        """, (f["nom"], f["telephone"], f["telephone2"], f["email"], f["adresse"],
              wilaya_nom, f["source_id"]))
        inseres += 1

    conn.commit()
    return inseres, doublons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Teste sur 2 petites wilayas, n'écrit rien en DB")
    parser.add_argument("--apply", action="store_true", help="Scrape tout et insère en DB")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Précise --dry-run ou --apply.")
        return

    print("Récupération de la liste des wilayas...")
    wilayas = recuperer_liste_wilayas()
    print(f"{len(wilayas)} wilayas trouvées (total annoncé : {sum(w['total'] or 0 for w in wilayas)} notaires)\n")

    if args.dry_run:
        wilayas_test = sorted(wilayas, key=lambda w: w["total"] or 0)[:2]
        print(f"DRY RUN sur : {[w['nom'] for w in wilayas_test]}\n")
        for w in wilayas_test:
            print(f"  {w['nom']} (code {w['code']}, {w['total']} attendus) :")
            fiches = scraper_wilaya(w)
            print(f"    -> {len(fiches)} fiches récupérées au total")
            for f in fiches[:3]:
                print(f"       {f}")
            print()
        print("Si les données semblent correctes, relance avec --apply pour tout scraper.")
        return

    if args.apply:
        conn = sqlite3.connect(DB_PATH)
        total_inseres, total_doublons = 0, 0

        for i, w in enumerate(wilayas, 1):
            print(f"[{i}/{len(wilayas)}] {w['nom']} (attendu : {w['total']})...")
            fiches = scraper_wilaya(w)
            inseres, doublons = inserer_en_db(w["nom"], fiches, conn)
            total_inseres += inseres
            total_doublons += doublons
            print(f"    -> {inseres} insérés, {doublons} doublons ignorés\n")
            time.sleep(DELAI_ENTRE_REQUETES_SEC)

        conn.close()
        print(f"\nTerminé : {total_inseres} notaires insérés, {total_doublons} doublons ignorés.")


if __name__ == "__main__":
    main()