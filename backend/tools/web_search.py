"""
Fournisseurs de recherche web bruts : DuckDuckGo (gratuit) et Serper (payant).

Utilisés directement par tools/discovery_tools.py (RechercheGratuiteTool /
RecherchePayanteTool) — c'est le Planner de DiscoveryAgent qui décide lequel
utiliser et quand, pas une logique d'escalade automatique ici.
"""

from dataclasses import dataclass
from urllib import response

import requests

from config import SERPER_API_KEY, MAX_ESSAIS_RESEAU, TAVILY_API_KEY
from tools.rate_limiter import avec_retry


@dataclass
class ResultatRecherche:
    titre: str
    url: str
    extrait: str


"""
Fournisseurs de recherche web bruts : DuckDuckGo (gratuit) et Serper (payant).

Utilisés directement par tools/discovery_tools.py (RechercheGratuiteTool /
RecherchePayanteTool) — c'est le Planner de DiscoveryAgent qui décide lequel
utiliser et quand, pas une logique d'escalade automatique ici.
"""

from dataclasses import dataclass

import requests

from config import SERPER_API_KEY, MAX_ESSAIS_RESEAU,TAVILY_API_KEY
from tools.rate_limiter import avec_retry


@dataclass
class ResultatRecherche:
    titre: str
    url: str
    extrait: str


class DuckDuckGoProvider:
    """Utilise la librairie ddgs (gratuite, pas de clé API).
    On essaie d'abord backend="duckduckgo" seul (rapide, stable, pas de
    timeout observé). Si aucun résultat, on retente avec backend="brave"
    séparément — l'agrégation combinée "duckduckgo,brave" en un seul appel
    ddgs provoquait des ConnectTimeout fréquents, donc on isole chaque
    backend dans son propre essai plutôt que de les combiner."""

    @avec_retry(max_essais=MAX_ESSAIS_RESEAU, delai_base=2.0)
    def _rechercher_avec_backend(self, requete: str, max_resultats: int, backend: str) -> list[ResultatRecherche]:
        from ddgs import DDGS

        resultats = []
        with DDGS(timeout=10) as ddgs:
            for r in ddgs.text(requete, max_results=max_resultats, backend=backend):
                resultats.append(ResultatRecherche(
                    titre=r.get("title", ""),
                    url=r.get("href", ""),
                    extrait=r.get("body", ""),
                ))
        return resultats

    def search(self, requete: str, max_resultats: int = 8) -> list[ResultatRecherche]:
        # Le backend "duckduckgo" de ddgs est bloqué de façon systémique depuis
        # plusieurs mois (confirmé : échoue même sur des requêtes génériques
        # sans rapport avec le domaine). On ne perd plus de temps à le tenter
        # et on va directement sur "brave", qui lui reste fonctionnel (avec
        # retries gérés par @avec_retry, utiles ici car ses échecs sont
        # transitoires, contrairement à ceux de duckduckgo).
        return self._rechercher_avec_backend(requete, max_resultats, "brave")

class SerperProvider:
    """Utilise l'API Serper (payante, résultats Google). Nécessite SERPER_API_KEY."""

    def __init__(self, budget_guard):
        self.budget_guard = budget_guard

    @avec_retry(max_essais=MAX_ESSAIS_RESEAU, delai_base=2.0)
    def search(self, requete: str, max_resultats: int = 8) -> list[ResultatRecherche]:
        if not SERPER_API_KEY:
            raise RuntimeError("SERPER_API_KEY manquante : impossible d'utiliser le secours payant.")

        self.budget_guard.consommer(1)  # lève une exception si le plafond est dépassé

        response = requests.post(
           "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": requete, "num": max_resultats},
           timeout=15,
          )
        if response.status_code >= 400:
         print(f"[DEBUG SERPER] status={response.status_code} body={response.text!r}")
        data = response.json()
        response.raise_for_status()
        resultats = []
        for r in data.get("organic", [])[:max_resultats]:
            resultats.append(ResultatRecherche(
                titre=r.get("title", ""),
                url=r.get("link", ""),
                extrait=r.get("snippet", ""),
            ))
        return resultats

class TavilyProvider:
    """Utilise l'API Tavily — gratuite jusqu'à 1000 requêtes/mois, renouvelées
    chaque mois (contrairement au crédit Serper, à usage unique)."""

    @avec_retry(max_essais=MAX_ESSAIS_RESEAU, delai_base=2.0)
    def search(self, requete: str, max_resultats: int = 8) -> list[ResultatRecherche]:
        if not TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY manquante.")

        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": TAVILY_API_KEY,
                "query": requete,
                "max_results": max_resultats,
            },
            timeout=15,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Tavily erreur {response.status_code}: {response.text}")
        data = response.json()

        resultats = []
        for r in data.get("results", [])[:max_resultats]:
            resultats.append(ResultatRecherche(
                titre=r.get("title", ""),
                url=r.get("url", ""),
                extrait=r.get("content", ""),
            ))
        return resultats


