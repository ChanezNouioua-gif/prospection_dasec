"""
Nettoyage ciblé, basé sur l'audit confirmé le {date de la session} :
- Djallal Bouabdallah : 22 lignes, pollution croisée sur 7 secteurs différents
- BOUCHAREB Ahmed : 3 lignes, pollution croisée (avocat + notaire)
- M. DRIDI : 7 lignes, CNAS Béjaïa — vérifié faux : le vrai directeur actuel
  de la CNAS Béjaïa est Belkacem Maâfa, pas DRIDI (source : presse 2024-2025)
- Toute ligne où contact_nom contient un '@' : bug d'extraction où un email
  a été stocké comme s'il s'agissait d'un nom (cas trouvé : Biopure SPA)

Volontairement PAS touché (vérifiés légitimes) : Yahia Rassoul, Réda Moussi,
Nadir Kouadria — responsables CNAS réels, confirmés par la presse.

Pour chaque ligne nettoyée, vide contact_nom, contact_fonction,
contact_telephone_personnel, contact_email_personnel,
contact_linkedin_personnel — pas seulement le nom : ses coordonnées
"personnelles" associées sont par construction rattachées à la mauvaise
personne, donc invalides aussi.

Ne fait AUCUN appel réseau.

Usage :
    python scripts/nettoyer_decideurs_pollues.py                    # dry-run
    python scripts/nettoyer_decideurs_pollues.py --appliquer
    python scripts/nettoyer_decideurs_pollues.py --appliquer --reset-tente
"""

import argparse
import re
import sys
import os
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_PATH
from database.connection import obtenir_connexion

# Noms confirmés comme faux positifs (cf. audit + vérification externe).
# Comparaison normalisée (ascii, minuscule, sans titres) pour absorber les
# variantes d'écriture ("M. DRIDI" vs "DRIDI", "Djallal Bouabdallah" vs
# "M. Djallal Bouabdallah").
NOMS_CIBLES = [
    "Djallal Bouabdallah",
    "BOUCHAREB Ahmed",
    "DRIDI",
]

TITRES_A_IGNORER = {"dr", "mr", "mme", "me", "pr", "m.", "m", "mlle"}


def _normaliser_ascii(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return texte.lower()


def _normaliser_nom(nom: str) -> str:
    ascii_nom = _normaliser_ascii(nom).replace(",", " ").replace(".", " ")
    fragments = [f for f in ascii_nom.split() if f not in TITRES_A_IGNORER and len(f) >= 2]
    return " ".join(sorted(fragments))


def _est_un_email(texte: str) -> bool:
    return bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texte or ""))


def main():
    parser = argparse.ArgumentParser(description="Nettoyage ciblé des décideurs confirmés faux positifs.")
    parser.add_argument("--appliquer", action="store_true",
                         help="Sans ce flag : dry-run, affiche seulement ce qui serait nettoyé.")
    parser.add_argument("--reset-tente", action="store_true",
                         help="Remet aussi contact_personnel_tente à 0 pour les lignes nettoyées.")
    args = parser.parse_args()

    cibles_normalisees = {_normaliser_nom(n) for n in NOMS_CIBLES}

    with obtenir_connexion(DB_PATH) as connexion:
        rows = connexion.execute("""
            SELECT id, nom, sous_secteur, contact_nom, contact_fonction,
                   contact_telephone_personnel, contact_email_personnel, contact_linkedin_personnel
            FROM entreprises
            WHERE contact_nom IS NOT NULL AND contact_nom != ''
        """).fetchall()
        rows = [dict(r) for r in rows]

        a_nettoyer = []
        for r in rows:
            nom_norm = _normaliser_nom(r["contact_nom"])
            raison = None
            if _est_un_email(r["contact_nom"]):
                raison = "contact_nom contient un email (erreur d'extraction)"
            elif nom_norm in cibles_normalisees:
                raison = f"nom confirmé pollution croisée : {r['contact_nom']!r}"
            if raison:
                a_nettoyer.append({**r, "raison": raison})

        print(f"{len(rows)} entreprises avec un contact_nom au total.")
        print(f"{len(a_nettoyer)} ligne(s) à nettoyer :\n")
        for d in a_nettoyer:
            print(f"  — [{d['id']}] {d['nom']} ({d['sous_secteur']}) : "
                  f"contact_nom={d['contact_nom']!r} — {d['raison']}")

        if not args.appliquer:
            print("\nDry-run : rien n'a été modifié. Relance avec --appliquer pour nettoyer pour de vrai.")
            return

        for d in a_nettoyer:
            champs = [
                "contact_nom = NULL",
                "contact_fonction = NULL",
                "contact_telephone_personnel = NULL",
                "contact_email_personnel = NULL",
                "contact_linkedin_personnel = NULL",
            ]
            if args.reset_tente:
                champs.append("contact_personnel_tente = 0")
            connexion.execute(
                f"UPDATE entreprises SET {', '.join(champs)} WHERE id = ?",
                (d["id"],),
            )
        connexion.commit()
        print(f"\n{len(a_nettoyer)} lignes nettoyées (contact_nom + toutes ses coordonnées associées).")
        if args.reset_tente:
            print("contact_personnel_tente remis à 0 : elles seront retraitées au prochain enrichissement.")


if __name__ == "__main__":
    main()