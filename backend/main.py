"""
Point d'entrée du pipeline d'enrichissement.

Usage :
    python main.py --pilote                 # échantillon de 100 (test validé avec DASEC)
    python main.py --secteur santé --limite 500
    python main.py --ids 12,45,78
"""

import argparse

from config import DB_PATH, BUDGET_MAX_APPELS_SERPER_PAR_RUN
from database.connection import obtenir_connexion
from database.repository import EntrepriseRepository
from agents.database_agent import DatabaseAgent
from agents.discovery import DiscoveryAgent
from agents.profile import ProfileAgent
from agents.scoring import ScoringAgent
from agents.coordinator import CoordinatorAgent
from tools.rate_limiter import BudgetGuard
from tools.llm_client import get_llm_client
from tools.discovery_tools import RechercheTavilyTool  

HEADERS_HTTP = {"User-Agent": "dasec-prospection/1.0 (contact: TON_EMAIL@exemple.com)"}
print(DB_PATH)



def construire_pipeline(connexion):
    repository = EntrepriseRepository(connexion)
    database_agent = DatabaseAgent(repository)

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

    densite_communes = database_agent.charger_densite_communes()
    scoring_agent = ScoringAgent(densite_communes)

    return CoordinatorAgent(database_agent, discovery_agent, profile_agent, scoring_agent), budget_guard


def selectionner_ids(connexion, args) -> list[int]:
    if args.ids:
        return [int(i) for i in args.ids.split(",")]

    condition = "WHERE critic_valide IS NULL"
    parametres = []
    if args.secteur:
        condition += " AND secteur = ?"
        parametres.append(args.secteur)

    # <-- AJOUTE CES 3 LIGNES ICI
    if args.sous_secteur:
        condition += " AND sous_secteur = ?"
        parametres.append(args.sous_secteur)

    limite = 100 if args.pilote else (args.limite or 4340)

    cursor = connexion.execute(
        f"SELECT id FROM entreprises {condition} LIMIT ?",
        (*parametres, limite)
    )

    return [row["id"] for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description="Pipeline d'enrichissement DASEC")
    parser.add_argument("--pilote", action="store_true", help="Lance uniquement sur 100 établissements")
    parser.add_argument("--secteur", type=str, default=None)
    parser.add_argument("--sous-secteur", type=str, default=None)
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--ids", type=str, default=None, help="Liste d'IDs séparés par des virgules")
    args = parser.parse_args()

    with obtenir_connexion(DB_PATH) as connexion:
        pipeline, budget_guard = construire_pipeline(connexion)
        ids = selectionner_ids(connexion, args)

        print(f"{len(ids)} établissements à traiter.")
        resume = pipeline.traiter_lot(ids)

        print(f"\nTerminé : {resume['traites']} traités, {resume['echecs']} échecs.")
        print(f"Appels de recherche payants utilisés : {budget_guard.appels_effectues}/{budget_guard.plafond_appels}")


if __name__ == "__main__":
    main()
