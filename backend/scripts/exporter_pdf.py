"""
Export de tous les décideurs + leurs contacts (base actuelle), pour analyse
externe (repérer les faux positifs à l'oeil / partager pour audit).

Ne fait AUCUN appel réseau, AUCUNE modification en base — lecture seule.

Usage :
    python scripts/exporter_decideurs.py
    python scripts/exporter_decideurs.py --sortie mon_export.csv
    python scripts/exporter_decideurs.py --uniquement-avec-nom
"""

import argparse
import csv
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_PATH
from database.connection import obtenir_connexion

COLONNES = [
    "id", "nom", "sous_secteur", "commune_name", "wilaya_name",
    "telephone", "email",
    "contact_nom", "contact_fonction",
    "contact_telephone_personnel", "contact_email_personnel", "contact_linkedin_personnel",
    "contact_personnel_tente",
]


def main():
    parser = argparse.ArgumentParser(description="Export des décideurs et de leurs contacts en CSV.")
    parser.add_argument("--sortie", default="export_decideurs.csv",
                         help="Nom du fichier CSV de sortie (défaut : export_decideurs.csv)")
    parser.add_argument("--uniquement-avec-nom", action="store_true",
                         help="N'exporte que les lignes où contact_nom est renseigné.")
    args = parser.parse_args()

    colonnes_disponibles = None
    with obtenir_connexion(DB_PATH) as connexion:
        colonnes_table = {row[1] for row in connexion.execute("PRAGMA table_info(entreprises)").fetchall()}
        colonnes_disponibles = [c for c in COLONNES if c in colonnes_table]
        manquantes = [c for c in COLONNES if c not in colonnes_table]
        if manquantes:
            print(f"[avertissement] colonnes absentes de la table, ignorées : {manquantes}")

        clause_where = "WHERE contact_nom IS NOT NULL AND contact_nom != ''" if args.uniquement_avec_nom else ""
        requete = f"SELECT {', '.join(colonnes_disponibles)} FROM entreprises {clause_where} ORDER BY nom"
        rows = connexion.execute(requete).fetchall()

    with open(args.sortie, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(colonnes_disponibles)
        for row in rows:
            writer.writerow([row[c] for c in colonnes_disponibles])

    print(f"{len(rows)} lignes exportées vers {args.sortie}")
    avec_nom = sum(1 for row in rows if row["contact_nom"])
    avec_contact_perso = sum(
        1 for row in rows
        if row["contact_telephone_personnel"] or row["contact_email_personnel"] or row["contact_linkedin_personnel"]
    )
    print(f"  dont {avec_nom} avec un contact_nom")
    print(f"  dont {avec_contact_perso} avec au moins une coordonnée personnelle")


if __name__ == "__main__":
    main()