import json

from backend.agents.discovery import DiscoveryAgent
from backend.models.schemas import Entreprise, DiscoveryObservation
from backend.tools.web_search import ResultatRecherche
from backend.tools.rate_limiter import BudgetGuard


class FakeLLMClient:
    """LLM scripté : renvoie les réponses fournies dans l'ordre, un appel = une réponse.
    Permet de tester la boucle Planner/Critic sans dépendre d'un vrai fournisseur."""
    def __init__(self, reponses: list[str]):
        self.reponses = reponses
        self.appels = []

    def complete(self, system, prompt, max_tokens=300):
        self.appels.append((system, prompt))
        if not self.reponses:
            raise RuntimeError("FakeLLMClient : plus de réponses scriptées disponibles")
        return self.reponses.pop(0)


class FakeTool:
    """Remplace un outil réel (recherche/visite) par une observation scriptée."""
    def __init__(self, observation: DiscoveryObservation):
        self.observation = observation
        self.appels = []

    def executer(self, input_):
        self.appels.append(input_)
        return self.observation


def entreprise_test(**kwargs):
    defaults = dict(id=1, nom="Clinique Chifa", secteur="santé", sous_secteur="clinique privée",
                     type_gestion="privé", commune_name="Bab Ezzouar", wilaya_name="Alger")
    defaults.update(kwargs)
    return Entreprise(**defaults)


def construire_agent(reponses_llm, tool_gratuit=None, tool_payant=None, tool_visite=None):
    llm = FakeLLMClient(reponses_llm)
    budget_guard = BudgetGuard(plafond_appels=10)
    agent = DiscoveryAgent(llm, budget_guard, headers={})
    if tool_gratuit is not None:
        agent.tools["recherche_gratuite"] = tool_gratuit
    if tool_payant is not None:
        agent.tools["recherche_payante"] = tool_payant
    if tool_visite is not None:
        agent.tools["visiter_url"] = tool_visite
    return agent, llm


def test_planner_trouve_un_site_puis_termine():
    """Planner : 1) recherche_gratuite  2) finish. Critic : valide la source."""
    observation_recherche = DiscoveryObservation(
        resume="recherche gratuite pour 'Clinique Chifa Bab Ezzouar Algérie' : 1 résultat(s)",
        resultats=[ResultatRecherche(titre="Clinique Chifa", url="https://cliniquechifa.dz", extrait="...")],
    )
    tool_gratuit = FakeTool(observation_recherche)

    reponses_llm = [
        json.dumps({"thought": "je cherche d'abord gratuitement", "action": "recherche_gratuite",
                    "input": "Clinique Chifa Bab Ezzouar Algérie"}),
        json.dumps({"thought": "site trouvé, je termine", "action": "finish", "input": None}),
        json.dumps({"website": {"valide": True, "raison": "nom et lieu correspondent"}}),
    ]
    agent, llm = construire_agent(reponses_llm, tool_gratuit=tool_gratuit)

    sources = agent.run(entreprise_test())

    assert sources.website == "https://cliniquechifa.dz"
    assert len(tool_gratuit.appels) == 1
    assert len(llm.appels) == 3  # 2 tours Planner + 1 Critic


def test_critic_rejette_une_source_incorrecte():
    """Le Critic doit pouvoir retirer une source que le tri par domaine avait acceptée à tort."""
    observation_recherche = DiscoveryObservation(
        resume="1 résultat",
        resultats=[ResultatRecherche(titre="Clinique Chifa Oran (homonyme)", url="https://clinique-chifa-oran.dz", extrait="...")],
    )
    tool_gratuit = FakeTool(observation_recherche)

    reponses_llm = [
        json.dumps({"thought": "je cherche", "action": "recherche_gratuite", "input": "Clinique Chifa"}),
        json.dumps({"thought": "je termine", "action": "finish", "input": None}),
        json.dumps({"website": {"valide": False, "raison": "c'est un homonyme à Oran, pas à Bab Ezzouar"}}),
    ]
    agent, _ = construire_agent(reponses_llm, tool_gratuit=tool_gratuit)

    sources = agent.run(entreprise_test())

    assert sources.website is None  # rejeté par le Critic malgré le premier tri par domaine


def test_planner_peut_utiliser_recherche_payante_si_le_llm_le_decide():
    observation_gratuite = DiscoveryObservation(resume="0 résultat", resultats=[])
    observation_payante = DiscoveryObservation(
        resume="1 résultat payant",
        resultats=[ResultatRecherche(titre="Clinique Chifa", url="https://cliniquechifa.dz", extrait="...")],
        paiement_effectue=True,
    )
    tool_gratuit = FakeTool(observation_gratuite)
    tool_payant = FakeTool(observation_payante)

    reponses_llm = [
        json.dumps({"thought": "j'essaie gratuit d'abord", "action": "recherche_gratuite", "input": "Clinique Chifa"}),
        json.dumps({"thought": "rien trouvé, je paie", "action": "recherche_payante", "input": "Clinique Chifa Bab Ezzouar"}),
        json.dumps({"thought": "trouvé, je termine", "action": "finish", "input": None}),
        json.dumps({"website": {"valide": True, "raison": "ok"}}),
    ]
    agent, _ = construire_agent(reponses_llm, tool_gratuit=tool_gratuit, tool_payant=tool_payant)

    sources = agent.run(entreprise_test())

    assert sources.website == "https://cliniquechifa.dz"
    assert sources.recherche_payante_utilisee is True  # signal explicite, pas déduit d'un texte


def test_reponse_llm_invalide_termine_proprement_sans_planter():
    """Si le Planner renvoie un JSON cassé, l'agent doit s'arrêter proprement, pas planter."""
    reponses_llm = ["ceci n'est pas du JSON valide"]
    agent, _ = construire_agent(reponses_llm)

    sources = agent.run(entreprise_test())

    assert sources.website is None
    assert sources.facebook is None


def test_max_iterations_est_respecte():
    """Si le Planner ne dit jamais 'finish', la boucle doit s'arrêter au bout de MAX_ITERATIONS."""
    observation_vide = DiscoveryObservation(resume="0 résultat", resultats=[])
    tool_gratuit = FakeTool(observation_vide)

    reponse_boucle = json.dumps({"thought": "je continue à chercher", "action": "recherche_gratuite", "input": "x"})
    reponses_llm = [reponse_boucle] * 10  # bien plus que MAX_ITERATIONS
    agent, llm = construire_agent(reponses_llm, tool_gratuit=tool_gratuit)

    agent.run(entreprise_test())

    # MAX_ITERATIONS appels Planner + 0 Critic (rien trouvé, donc pas de critique)
    assert len(tool_gratuit.appels) == 5  # MAX_ITERATIONS dans agents/discovery.py
