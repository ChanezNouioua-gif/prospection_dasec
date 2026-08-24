"""
Rattrapage ciblé : ajoute une coordonnée personnelle (email nominatif,
téléphone direct, LinkedIn) aux prospects qui ont déjà un nom de décideur
mais aucun moyen de le/la contacter — sans repasser par Discovery ni par
le scoring, pour limiter la consommation Serper/LLM au strict nécessaire.

Usage :
    python scripts/enrichir_decideurs_existants.py --max 50
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import time

from config import DB_PATH, BUDGET_MAX_APPELS_SERPER_PAR_RUN
from database.connection import obtenir_connexion
from database.repository import EntrepriseRepository
from models.schemas import Entreprise, ProfileData
from tools.llm_client import get_llm_client
from tools.rate_limiter import BudgetGuard
from tools.discovery_tools import RechercheGratuiteTool, RecherchePayanteTool,RechercheTavilyTool
from agents.profile import ProfileAgent
from agents.discovery import DiscoveryAgent

HEADERS_HTTP = {"User-Agent": "dasec-prospection/1.0 (contact: TON_EMAIL@exemple.com)"}


def main():
    parser = argparse.ArgumentParser(description="Enrichissement ciblé des contacts personnels décideurs.")
    parser.add_argument("--max", type=int, default=50)
    parser.add_argument("--delai", type=float, default=4.5,
                         help="Pause en secondes entre chaque entreprise (limite Gemini gratuit : 15 req/min)")
    args = parser.parse_args()

    with obtenir_connexion(DB_PATH) as connexion:
        repo = EntrepriseRepository(connexion)
        repo.s_assurer_schema_a_jour()

        candidats = repo.get_candidats_contact_personnel(args.max)
        print(f"{len(candidats)} entreprises avec un nom mais sans coordonnée personnelle.")
        if not candidats:
            print("Rien à traiter.")
            return

        budget_guard = BudgetGuard(BUDGET_MAX_APPELS_SERPER_PAR_RUN)
        llm_client = get_llm_client()
        discovery_agent = DiscoveryAgent(llm_client, budget_guard, HEADERS_HTTP)
        profile_agent = ProfileAgent(
          llm_client, HEADERS_HTTP,
          discovery_agent.tools["recherche_gratuite"],
          discovery_agent.tools["recherche_payante"],
          RechercheTavilyTool(),
          budget_guard,
        )

        traites, trouves = 0, 0
        for row in candidats:
            entreprise = Entreprise.from_row(row)
            profil = ProfileData(contact_nom=row.get("contact_nom"), contact_fonction=row.get("contact_fonction"))

            try:
                profile_agent.enrichir_contact_personnel(entreprise, profil)
            except Exception as e:
                print(f"  [erreur] {entreprise.nom} : {type(e).__name__}: {e}")
                continue

            trouve = profil.contact_email_personnel or profil.contact_telephone_personnel or profil.contact_linkedin_personnel
            if trouve:
                trouves += 1
                print(f"  ✓ {entreprise.nom} -> email={profil.contact_email_personnel!r} "
                      f"tel={profil.contact_telephone_personnel!r} linkedin={profil.contact_linkedin_personnel!r}")
            else:
                print(f"  — {entreprise.nom} : rien trouvé")

            repo.maj_contact_personnel(entreprise.id, profil)
            traites += 1
            time.sleep(args.delai)

        print(f"\nTerminé : {traites} traités, {trouves} avec au moins une coordonnée trouvée.")
        print(f"Appels Serper utilisés : {budget_guard.appels_effectues}/{budget_guard.plafond_appels}")


if __name__ == "__main__":
    main()