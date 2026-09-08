"""
CoordinatorAgent — orchestre le pipeline complet pour un lot d'établissements.

Une erreur sur un établissement (site injoignable, LLM en échec) ne doit
jamais interrompre le traitement des autres — elle est loguée dans
enrichment_log et le pipeline continue sur l'établissement suivant.

Le dépassement de budget n'est plus une exception qui remonte jusqu'ici :
RecherchePayanteTool (tools/discovery_tools.py) échoue proprement en interne
et retourne une observation "épuisé" au Planner, qui peut alors continuer
sans recherche payante plutôt que de faire échouer tout le run. Ce choix est
délibéré : sur un lot de 100 établissements, un budget épuisé à l'établissement
40 ne doit pas priver les 60 suivants de tout enrichissement gratuit.
"""

import time

from backend.agents.database_agent import DatabaseAgent
from backend.agents.discovery import DiscoveryAgent
from backend.agents.profile import ProfileAgent
from backend.agents.scoring import ScoringAgent
from backend.config import DELAI_ENTRE_ETABLISSEMENTS_SEC


class CoordinatorAgent:
    def __init__(
        self,
        database_agent: DatabaseAgent,
        discovery_agent: DiscoveryAgent,
        profile_agent: ProfileAgent,
        scoring_agent: ScoringAgent,
    ):
        self.database_agent = database_agent
        self.discovery_agent = discovery_agent
        self.profile_agent = profile_agent
        self.scoring_agent = scoring_agent

    def traiter_lot(self, ids_entreprises: list[int]) -> dict:
        self.database_agent.preparer_schema()

        resume = {"traites": 0, "echecs": 0}

        for entreprise_id in ids_entreprises:
            entreprise = self.database_agent.charger_entreprise(entreprise_id)
            if entreprise is None:
                continue

            try:
                self._traiter_un_etablissement(entreprise)
                resume["traites"] += 1
            except Exception as e:
                resume["echecs"] += 1
                self.database_agent.logger(entreprise_id, "coordinator", "echec", str(e))

            time.sleep(DELAI_ENTRE_ETABLISSEMENTS_SEC)

        return resume

    def _traiter_un_etablissement(self, entreprise):
        sources = self.discovery_agent.run(entreprise)
        self.database_agent.sauvegarder_sources(entreprise.id, sources)
        self.database_agent.logger(
            entreprise.id, "discovery", "ok",
            detail=f"payant={sources.recherche_payante_utilisee}",
        )

        profil = self.profile_agent.run(entreprise, sources)
        self.database_agent.sauvegarder_profil(entreprise.id, profil)
        self.database_agent.logger(entreprise.id, "profile", "ok")

        commune_id = self.database_agent.commune_id_de(entreprise.id)
        score = self.scoring_agent.run(entreprise, profil, commune_id)
        self.database_agent.sauvegarder_score(entreprise.id, score)
        self.database_agent.logger(entreprise.id, "scoring", "ok", detail=str(score.detail))
