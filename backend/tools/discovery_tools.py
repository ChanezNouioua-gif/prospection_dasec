"""
Outils que le Planner de DiscoveryAgent peut choisir d'utiliser.

Le Planner ne connaît que le nom de ces outils et leur description dans le
prompt — il ignore qu'il y a du DuckDuckGo ou du Serper derrière. Ça permet
de changer de fournisseur de recherche sans toucher au raisonnement de
l'agent, et surtout : c'est le LLM qui décide s'il "paie" ou non (le budget
restant lui est donné dans le prompt), pas un seuil hardcodé comme dans
l'ancienne version (HybridSearchTool).

PATCH (quota Serper épuisé) : RecherchePayanteTool distingue maintenant
QuotaEpuiseError (compte Serper réellement à sec, erreur permanente) des
autres échecs (réseau, timeout — déjà retentés par SerperProvider lui-même).
Sur QuotaEpuiseError, le budget est désactivé pour TOUT le reste du run
(budget_guard.epuiser_definitivement()) : les établissements suivants ne
perdront plus de temps à retenter Serper.
"""

import time

import requests

from models.schemas import DiscoveryObservation
from tools.web_search import DuckDuckGoProvider, SerperProvider, ResultatRecherche, TavilyProvider, QuotaEpuiseError
from tools.rate_limiter import BudgetGuard
DOMAINES_PAR_TYPE = {
    "facebook": ["facebook.com"],
    "linkedin": ["linkedin.com"],
    "google_business": ["business.google.com", "g.page", "maps.google.com", "mapcarta.com"],
    "pages_jaunes": ["pagesjaunes.dz", "ouedkniss.com"],
}
DOMAINES_ANNUAIRES = [
    "hospitalby.com", "bejaia-guidedepoche.com", "algerie-docto.com",
    "1sante.com", "angels-initiative.com", "dbpedia.org",
    "pagesmaghreb.com", "africabizinfo.com", "algdz.com",
    "annumed.sante-dz.com", "caci.dz", "algerie360.com",
    "annuaire-algerie.com", "annuaire-algerie.net", "annuaire-algerie.org",
    "guideoran.com", "sihhatech.com", "sahadoc.net", "tidjara.dz",
    "dz.kompass.com", "adresse-algerie.com", "alger-city.com",
    "lkeria.com",
]

DOMAINES_EXCLUS = [
    "wikipedia.org", "wikidata.org", "youtube.com", "instagram.com",
    "tiktok.com", "twitter.com", "x.com", "uicc.org", "waze.com",
]
PATTERNS_LISTING = ["/filter/", "/search", "/liste", "?commune=", "?wilaya=", "/category/", "/annuaire/"]

DOMAINES_PRESSE_INSTITUTIONNEL = [
    "lactualgerie.com", "entrenous.dz", "masantemavie.dz",
    "elmoudjahid.dz", "aps.dz", "tsa-algerie.com", "elwatan.dz",
]

def classifier_url(url: str) -> str | None:
    if not url:
        return None
    url_min = url.lower()
    for type_source, domaines in DOMAINES_PAR_TYPE.items():
        if any(d in url_min for d in domaines):
            return type_source
    if any(d in url_min for d in DOMAINES_ANNUAIRES):
        return None if est_page_listing(url) else "annuaire"
    if any(d in url_min for d in DOMAINES_PRESSE_INSTITUTIONNEL) or ".univ-" in url_min or url_min.startswith("https://www.univ") or "univ-" in url_min:
        return None if est_page_listing(url) else "annuaire"  # traité comme annuaire : utile pour contact, jamais affiché comme site officiel
    if not any(d in url_min for d in DOMAINES_EXCLUS):
        return "website"
    return None

def est_page_listing(url: str) -> bool:
    """Détecte les pages de résultats/filtres d'annuaire, qui ne représentent
    pas un établissement précis et ne doivent jamais être scrapées comme source
    de contact — elles mélangent plusieurs structures ou nécessitent du JS."""
    url_min = url.lower()
    return any(p in url_min for p in PATTERNS_LISTING) 


class RechercheTavilyTool:
    def __init__(self):
        self.provider = TavilyProvider()

    def executer(self, requete: str) -> DiscoveryObservation:
        if not requete:
            return DiscoveryObservation(resume="recherche_tavily : requête vide", resultats=[])
        try:
            resultats = self.provider.search(requete, max_resultats=8)
        except Exception as e:
            print(f"[DISCOVERY][recherche_tavily] échec réel : {type(e).__name__}: {e}")
            return DiscoveryObservation(resume=f"recherche Tavily échouée : {type(e).__name__}", resultats=[])
        return DiscoveryObservation(
            resume=f"recherche Tavily pour '{requete}' : {len(resultats)} résultat(s)",
            resultats=resultats,
        )
    


class RechercheGratuiteTool:
    """Recherche web via DuckDuckGo/Brave (ddgs) — gratuite, aucun garde-fou
    budget nécessaire.

    PATCH (ddgs peu fiable) : les deux backends ddgs (brave, duckduckgo) se
    sont révélés bloqués tour à tour dans la même session (rate-limiting IP
    après un run un peu volumineux) — ce n'est pas un bug ponctuel mais une
    fragilité structurelle du scraping sans API officielle. Avant de
    déclarer l'échec complet (et de faire remonter "aucune source trouvée"
    au Planner), on tente Tavily (vraie API, 1000 requêtes/mois gratuites)
    en dernier recours. Ce n'est pas gratuit à l'infini comme ddgs — donc on
    ne l'essaie qu'après l'échec de ddgs, pas en remplacement."""

    def __init__(self):
        self.provider = DuckDuckGoProvider()
        self.provider_secours = TavilyProvider()

    def executer(self, requete: str) -> DiscoveryObservation:
     if not requete:
        return DiscoveryObservation(resume="recherche_gratuite : requête vide", resultats=[])
     for tentative in range(2):
        try:
            resultats = self.provider.search(requete, max_resultats=8)
            return DiscoveryObservation(
                resume=f"recherche gratuite pour '{requete}' : {len(resultats)} résultat(s)",
                resultats=resultats,
            )
        except Exception as e:
            print(f"[DISCOVERY][recherche_gratuite] tentative {tentative+1} échouée : {type(e).__name__}: {e}")
            if tentative == 0:
                time.sleep(3)

     # PATCH : ddgs (brave + duckduckgo) a échoué sur les 2 tentatives —
     # dernier recours Tavily avant d'abandonner complètement.
     try:
        resultats = self.provider_secours.search(requete, max_resultats=8)
        print(f"[DISCOVERY][recherche_gratuite] ddgs indisponible, secours Tavily : {len(resultats)} résultat(s)")
        return DiscoveryObservation(
            resume=f"recherche gratuite (secours Tavily) pour '{requete}' : {len(resultats)} résultat(s)",
            resultats=resultats,
        )
     except Exception as e:
        print(f"[DISCOVERY][recherche_gratuite] secours Tavily aussi échoué : {type(e).__name__}: {e}")

     return DiscoveryObservation(resume="recherche gratuite échouée après retry (ddgs + Tavily)", resultats=[])

class RecherchePayanteTool:
    """Recherche web via Serper — payante. Le Planner décide de l'utiliser
    (le budget restant lui est indiqué dans le prompt), mais le garde-fou est
    quand même appliqué ici : si le LLM l'ignore et l'appelle malgré un budget
    épuisé, l'outil échoue proprement (observation, pas d'exception qui
    remonterait jusqu'au Coordinator et ferait échouer tout l'établissement).

    PATCH (quota Serper épuisé) : QuotaEpuiseError est traitée à part —
    c'est le signal que le compte Serper réel est à sec, pas juste notre
    plafond local. On appelle budget_guard.epuiser_definitivement() pour que
    plus aucun établissement suivant, dans ce run, ne retente Serper."""

    def __init__(self, budget_guard: BudgetGuard):
        self.provider = SerperProvider(budget_guard)
        self.budget_guard = budget_guard

    def executer(self, requete: str) -> DiscoveryObservation:
        if not requete:
            return DiscoveryObservation(resume="recherche_payante : requête vide", resultats=[])
        if self.budget_guard.restant <= 0:
            return DiscoveryObservation(resume="recherche payante épuisée : plafond budget déjà atteint", resultats=[])

        try:
            resultats = self.provider.search(requete, max_resultats=8)
        except QuotaEpuiseError as e:
            if not self.budget_guard.quota_fournisseur_epuise:
                print(f"[DISCOVERY][recherche_payante] quota Serper épuisé côté fournisseur, "
                      f"désactivé pour le reste du run : {e}")
            self.budget_guard.epuiser_definitivement()
            return DiscoveryObservation(resume="recherche payante épuisée : quota Serper épuisé (compte à sec)", resultats=[])
        except RuntimeError as e:
            return DiscoveryObservation(resume=f"recherche payante épuisée : {e}", resultats=[])
        except Exception as e:
            print(f"[DISCOVERY][recherche_payante] échec réel : {type(e).__name__}: {e}")
            return DiscoveryObservation(resume=f"recherche payante échouée : {type(e).__name__}", resultats=[])

        return DiscoveryObservation(
            resume=f"recherche payante pour '{requete}' : {len(resultats)} résultat(s)",
            resultats=resultats,
            paiement_effectue=True,
        )


class VisiterUrlTool:
    """Confirme qu'une URL précise est joignable, sans en extraire de contact
    (ce n'est pas son rôle — seulement une vérification d'existence pour le
    Planner avant de retenir l'URL comme source fiable)."""

    def __init__(self, headers: dict, max_essais: int = 2):
        self.headers = headers
        self.max_essais = max_essais

    def executer(self, url: str) -> DiscoveryObservation:
        if not url:
            return DiscoveryObservation(resume="visiter_url : aucune URL fournie", resultats=[])

        derniere_erreur = None
        reponse = None
        for essai in range(1, self.max_essais + 1):
            try:
                reponse = requests.get(url, headers=self.headers, timeout=10)
                break
            except requests.exceptions.RequestException as e:
                derniere_erreur = e
                time.sleep(2 * essai)

        if reponse is None:
            print(f"[DISCOVERY][visiter_url] échec réel sur {url} : {type(derniere_erreur).__name__}: {derniere_erreur}")
            return DiscoveryObservation(resume=f"visiter_url {url} injoignable : {type(derniere_erreur).__name__}", resultats=[])

        if reponse.status_code != 200:
            return DiscoveryObservation(resume=f"visiter_url {url} : code HTTP {reponse.status_code}", resultats=[])

        titre = ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(reponse.text, "html.parser")
            if soup.title and soup.title.string:
                titre = soup.title.string.strip()
        except Exception:
            pass  # absence de titre n'est pas une erreur bloquante

        return DiscoveryObservation(
            resume=f"visiter_url {url} : accessible (titre : {titre or 'inconnu'})",
            resultats=[ResultatRecherche(titre=titre, url=url, extrait=reponse.text[:300])],
        )