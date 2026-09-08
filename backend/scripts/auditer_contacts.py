"""
Audit (lecture seule, aucune modification en base, aucun appel réseau) des
décideurs déjà enregistrés. Deux vérifications :

1. POLLUTION CROISÉE : un contact_nom qui revient sur plusieurs entreprises
   de secteurs différents et/ou sans lien entre elles est presque toujours
   le symptôme d'une recherche trop large (_rechercher_decideur) qui a
   remonté une personnalité visible en ligne (RSSI/avocat/notaire connu)
   plutôt que le vrai décideur de CET établissement précis.

2. COHÉRENCE NOM <-> COORDONNÉES : pour chaque contact_linkedin_personnel
   et contact_email_personnel déjà en base, on revérifie qu'ils correspondent
   bien au contact_nom stocké, avec la même logique déterministe que
   ProfileAgent (_slug_correspond_au_nom, fragment du nom dans la partie
   locale de l'email). Un email/LinkedIn qui ne matche plus le nom est soit
   un résidu d'un mauvais rattachement, soit un nom mal extrait alors que
   la coordonnée, elle, était correcte — les deux sont à vérifier à la main.

Rien n'est modifié : le script écrit un rapport CSV avec un motif ("raison")
par ligne suspecte, pour audit / nettoyage ciblé ensuite.

Usage :
    python scripts/auditer_decideurs.py
    python scripts/auditer_decideurs.py --seuil-pollution 3
    python scripts/auditer_decideurs.py --sortie mon_audit.csv
"""

import argparse
import csv
import re
import sys
import os
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_PATH
from database.connection import obtenir_connexion

TITRES_A_IGNORER = {"dr", "mr", "mme", "me", "pr", "m.", "mlle"}


def _normaliser_ascii(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return texte.lower()


def _normaliser_nom(nom: str) -> str:
    """Normalise pour le regroupement : ascii, minuscule, sans titres,
    fragments triés (pour matcher 'BOUBETRA, Mohamed Cherif' et
    'Mohamed Cherif Boubetra' comme la même personne)."""
    ascii_nom = _normaliser_ascii(nom).replace(",", " ").replace(".", " ")
    fragments = [f for f in ascii_nom.split() if f not in TITRES_A_IGNORER and len(f) >= 2]
    return " ".join(sorted(fragments))


def _slug_correspond_au_nom(url_linkedin: str, nom_decideur: str) -> bool:
    """Copie de la règle utilisée par ProfileAgent (même logique, pour ne
    pas dépendre d'un import de agents/profile.py depuis un script)."""
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


def _email_correspond_au_nom(email: str, nom_decideur: str) -> bool:
    """Même logique que _extraire_email_nominatif côté ProfileAgent, mais
    appliquée en vérification (l'email est déjà en base) plutôt qu'en
    extraction depuis un texte."""
    if not email or not nom_decideur:
        return False
    partie_locale = _normaliser_ascii(email.split("@")[0])
    fragments_nom = [
        f for f in _normaliser_ascii(nom_decideur).replace("-", " ").split()
        if len(f) >= 3
    ]
    return any(fragment in partie_locale for fragment in fragments_nom)


def main():
    parser = argparse.ArgumentParser(description="Audit des décideurs : pollution croisée + cohérence nom/coordonnées.")
    parser.add_argument("--seuil-pollution", type=int, default=3,
                         help="Nombre minimum d'entreprises distinctes pour signaler un contact_nom comme pollué (défaut : 3).")
    parser.add_argument("--sortie", default="audit_decideurs.csv",
                         help="Nom du fichier CSV de rapport (défaut : audit_decideurs.csv)")
    args = parser.parse_args()

    with obtenir_connexion(DB_PATH) as connexion:
        colonnes_table = {row[1] for row in connexion.execute("PRAGMA table_info(entreprises)").fetchall()}
        colonnes = ["id", "nom", "sous_secteur", "wilaya_name", "contact_nom",
                    "contact_fonction", "contact_email_personnel", "contact_linkedin_personnel"]
        colonnes = [c for c in colonnes if c in colonnes_table]

        rows = connexion.execute(
            f"SELECT {', '.join(colonnes)} FROM entreprises WHERE contact_nom IS NOT NULL AND contact_nom != ''"
        ).fetchall()
        rows = [dict(r) for r in rows]

    # ---------- 1. Pollution croisée ----------
    groupes = defaultdict(list)
    for r in rows:
        cle = _normaliser_nom(r["contact_nom"])
        if cle:
            groupes[cle].append(r)

    lignes_polluees = []
    for cle, membres in groupes.items():
        entreprises_distinctes = {m["id"] for m in membres}
        secteurs_distincts = {m.get("sous_secteur") for m in membres}
        if len(entreprises_distinctes) >= args.seuil_pollution and len(secteurs_distincts) > 1:
            for m in membres:
                lignes_polluees.append({
                    **m,
                    "raison": f"contact_nom sur {len(entreprises_distinctes)} entreprises, "
                              f"{len(secteurs_distincts)} secteurs différents : {sorted(secteurs_distincts)}",
                })

    # ---------- 2. Cohérence nom <-> coordonnées ----------
    lignes_incoherentes = []
    for r in rows:
        nom = r["contact_nom"]
        linkedin = r.get("contact_linkedin_personnel")
        email = r.get("contact_email_personnel")

        if linkedin and not _slug_correspond_au_nom(linkedin, nom):
            lignes_incoherentes.append({
                **r,
                "raison": f"contact_linkedin_personnel ne correspond pas à contact_nom={nom!r}",
            })
        if email and not _email_correspond_au_nom(email, nom):
            lignes_incoherentes.append({
                **r,
                "raison": f"contact_email_personnel ne correspond pas à contact_nom={nom!r}",
            })

    # ---------- Rapport ----------
    toutes_les_lignes = lignes_polluees + lignes_incoherentes
    colonnes_rapport = colonnes + ["raison"]

    with open(args.sortie, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colonnes_rapport)
        writer.writeheader()
        for ligne in toutes_les_lignes:
            writer.writerow({c: ligne.get(c, "") for c in colonnes_rapport})

    print(f"{len(rows)} entreprises avec un contact_nom au total.")
    print(f"\n=== Pollution croisée (seuil {args.seuil_pollution} entreprises, secteurs multiples) ===")
    noms_pollues = {_normaliser_nom(l['contact_nom']) for l in lignes_polluees}
    print(f"{len(noms_pollues)} nom(s) suspect(s), {len(lignes_polluees)} ligne(s) concernée(s) :")
    vus = set()
    for cle in noms_pollues:
        exemple = next(l for l in lignes_polluees if _normaliser_nom(l['contact_nom']) == cle)
        print(f"  — {exemple['contact_nom']!r} : {exemple['raison']}")

    print(f"\n=== Incohérence nom <-> coordonnées ===")
    print(f"{len(lignes_incoherentes)} ligne(s) où LinkedIn/email ne correspond pas au contact_nom :")
    for l in lignes_incoherentes:
        print(f"  — {l['nom']} : {l['raison']}")

    print(f"\nRapport complet ({len(toutes_les_lignes)} lignes, doublons possibles entre les 2 catégories) : {args.sortie}")
    print("Aucune modification en base — ce script ne fait que lire et rapporter.")


if __name__ == "__main__":
    main()