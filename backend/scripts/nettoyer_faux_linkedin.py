"""
Nettoyage rétroactif : revérifie tous les contact_linkedin_personnel déjà
en base avec la version RENFORCÉE de _slug_correspond_au_nom (2 fragments
si le nom en a au moins 2, sinon 1 fragment d'au moins 5 lettres).

Ne fait AUCUN appel réseau — relit juste ce qui est déjà stocké et vide
les champs qui ne passeraient plus le filtre actuel. Les entreprises
concernées repasseront comme candidates au prochain
enrichir_decideurs_existants.py, puisque contact_linkedin_personnel
redeviendra NULL (mais contact_personnel_tente reste à 1, donc il
faudra aussi le remettre à 0 pour qu'elles soient retraitées — voir
option --reset-tente).

Usage :
    python scripts/nettoyer_faux_linkedin.py            # dry-run, affiche seulement
    python scripts/nettoyer_faux_linkedin.py --appliquer  # nettoie pour de vrai
    python scripts/nettoyer_faux_linkedin.py --appliquer --reset-tente
"""

import argparse
import sys
import os
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_PATH
from database.connection import obtenir_connexion


def _normaliser_ascii(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return texte.lower()


def _slug_correspond_au_nom(url_linkedin: str, nom_decideur: str) -> bool:
    if not nom_decideur or not url_linkedin:
        return False
    slug = url_linkedin.rstrip("/").rsplit("/in/", 1)[-1]
    slug_normalise = _normaliser_ascii(slug).replace("-", " ")

    fragments_nom = [
        f for f in _normaliser_ascii(nom_decideur).replace("-", " ").split()
        if len(f) >= 3 and f not in ("dr", "mr", "mme")
    ]
    if not fragments_nom:
        return False

    matches = [f for f in fragments_nom if f in slug_normalise]
    if len(fragments_nom) >= 2:
        return len(matches) >= 2
    return len(matches) >= 1 and len(fragments_nom[0]) >= 5


def main():
    parser = argparse.ArgumentParser(description="Nettoyage rétroactif des faux LinkedIn.")
    parser.add_argument("--appliquer", action="store_true",
                         help="Sans ce flag : dry-run, affiche seulement ce qui serait nettoyé.")
    parser.add_argument("--reset-tente", action="store_true",
                         help="Remet aussi contact_personnel_tente à 0 pour les lignes nettoyées, "
                              "pour qu'elles soient retraitées au prochain enrichissement.")
    args = parser.parse_args()

    with obtenir_connexion(DB_PATH) as connexion:
        rows = connexion.execute("""
            SELECT id, nom, contact_nom, contact_linkedin_personnel
            FROM entreprises
            WHERE contact_linkedin_personnel IS NOT NULL
        """).fetchall()

        a_nettoyer = []
        for row in rows:
            d = dict(row)
            if not _slug_correspond_au_nom(d["contact_linkedin_personnel"], d["contact_nom"]):
                a_nettoyer.append(d)

        print(f"{len(rows)} entreprises avec un LinkedIn en base, {len(a_nettoyer)} ne passent plus le filtre renforcé :\n")
        for d in a_nettoyer:
            print(f"  — {d['nom']} : contact_nom={d['contact_nom']!r} linkedin={d['contact_linkedin_personnel']!r}")

        if not args.appliquer:
            print("\nDry-run : rien n'a été modifié. Relance avec --appliquer pour nettoyer pour de vrai.")
            return

        for d in a_nettoyer:
            if args.reset_tente:
                connexion.execute(
                    "UPDATE entreprises SET contact_linkedin_personnel = NULL, contact_personnel_tente = 0 WHERE id = ?",
                    (d["id"],),
                )
            else:
                connexion.execute(
                    "UPDATE entreprises SET contact_linkedin_personnel = NULL WHERE id = ?",
                    (d["id"],),
                )
        connexion.commit()
        print(f"\n{len(a_nettoyer)} lignes nettoyées.")
        if args.reset_tente:
            print("contact_personnel_tente remis à 0 pour ces lignes : elles seront retraitées au prochain run.")


if __name__ == "__main__":
    main()