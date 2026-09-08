"""
Fournisseurs de recherche web bruts : DuckDuckGo (gratuit) et Serper (payant).

Utilisés directement par tools/discovery_tools.py (RechercheGratuiteTool /
RecherchePayanteTool) — c'est le Planner de DiscoveryAgent qui décide lequel
utiliser et quand, pas une logique d'escalade automatique ici.
"""

from dataclasses import dataclass

import requests

from config import SERPER_API_KEY, MAX_ESSAIS_RESEAU, TAVILY_API_KEY
from tools.rate_limiter import avec_retry


@dataclass
class ResultatRecherche:
    titre: str
    url: str
    extrait: str


class QuotaEpuiseError(Exception):
    """PATCH (quota Serper épuisé) : erreur PERMANENTE (compte à sec), à ne
    jamais confondre avec une erreur réseau transitoire. Volontairement
    absente du tuple `exceptions` de @avec_retry sur SerperProvider.search :
    elle doit remonter immédiatement, sans les 3 tentatives habituelles —
    réessayer ne changera rien tant que le compte n'est pas rechargé."""
    pass


class DuckDuckGoProvider:
    """Utilise la librairie ddgs (gratuite, pas de clé API).

    PATCH (bascule brave/duckduckgo) : ce provider a déjà changé de backend
    "de référence" une fois (duckduckgo -> brave, cf. ancien commentaire), et
    on vient de reconstater l'inverse en conditions réelles : brave renvoie
    du 429 (rate-limited) pendant que duckduckgo fonctionne à nouveau. Plutôt
    que de figer une hypothèse qui recassera à la prochaine bascule, on
    essaie les deux dans l'ordre et on prend le premier qui répond — chaque
    tentative garde son propre retry (@avec_retry) pour les erreurs
    transitoires, mais on ne s'arc-boute plus sur un seul backend supposé
    fiable."""

    ORDRE_BACKENDS = ("duckduckgo", "brave")

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
        derniere_erreur = None
        for backend in self.ORDRE_BACKENDS:
            try:
                return self._rechercher_avec_backend(requete, max_resultats, backend)
            except Exception as e:
                print(f"[DISCOVERY][recherche_gratuite] backend '{backend}' indisponible : {type(e).__name__}: {e}")
                derniere_erreur = e
        raise derniere_erreur


class SerperProvider:
    """Utilise l'API Serper (payante, résultats Google). Nécessite SERPER_API_KEY.

    PATCH (quota Serper épuisé) : avant, @avec_retry(exceptions=(Exception,))
    attrapait AUSSI l'erreur 400 "Not enough credits" — une erreur permanente
    de compte, pas un problème réseau passager. Résultat observé en prod :
    3 tentatives identiques et vouées à l'échec, À CHAQUE établissement
    traité dans le run (22 établissements → 66 appels HTTP gaspillés pour
    rien). Le fix restreint `exceptions` aux erreurs réellement transitoires
    (requests.exceptions.RequestException) et distingue explicitement le cas
    "crédits épuisés" via QuotaEpuiseError, qui remonte immédiatement."""

    def __init__(self, budget_guard):
        self.budget_guard = budget_guard

    @avec_retry(max_essais=MAX_ESSAIS_RESEAU, delai_base=2.0, exceptions=(requests.exceptions.RequestException,))
    def search(self, requete: str, max_resultats: int = 8) -> list[ResultatRecherche]:
        if not SERPER_API_KEY:
            raise RuntimeError("SERPER_API_KEY manquante : impossible d'utiliser le secours payant.")

        self.budget_guard.consommer(1)  # lève une exception si le plafond local est dépassé

        response = requests.post(
           "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": requete, "num": max_resultats},
           timeout=15,
          )

        # PATCH : détection explicite du quota épuisé, AVANT raise_for_status
        # (qui aurait levé un HTTPError générique, retenté 3x pour rien).
        if response.status_code == 400 and "not enough credits" in response.text.lower():
            raise QuotaEpuiseError(response.text)

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