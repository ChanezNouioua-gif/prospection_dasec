"""
DiscoveryAgent — trouve les sources publiques d'un établissement, en boucle
Observer → Réfléchir → Choisir un outil → Exécuter → Valider (Critic).

Le LLM Planner ne voit jamais DuckDuckGo/Serper directement : il choisit une
action dans self.tools, l'agent l'exécute (_execute), observe le résultat et
met à jour son état (_update_state) avant de redécider. Une fois la mission
terminée, un second passage LLM (Critic) revalide en un seul appel que les
sources trouvées appartiennent bien à CET établissement précis.

Toujours pas de téléphone/email ici : uniquement des sources — le
ProfileAgent reste seul responsable de l'extraction de contacts.
"""

import json

from models.schemas import Entreprise, DiscoverySources, DiscoveryState, DiscoveryDecision, DiscoveryObservation
from tools.discovery_tools import RechercheGratuiteTool, RecherchePayanteTool, VisiterUrlTool, classifier_url
from tools.rules import similarite_nom_domaine
from tools.rate_limiter import BudgetGuard
from tools.llm_client import LLMClient
from tools.json_utils import nettoyer_json
from tools.json_utils import nettoyer_json, extraire_champ_regex

MAX_ITERATIONS = 5  # garde-fou : jamais de mission infinie

PROMPT_SYSTEME_PLANNER = (
    "Tu es DiscoveryAgent. Ta seule mission : trouver les sources publiques "
    "(site officiel, Facebook, LinkedIn, fiche Google Business, Pages Jaunes) "
    "d'un établissement algérien. Ne cherche JAMAIS de téléphone ou d'email, "
    "seulement des URLs. Choisis UNE action par tour. Réponds UNIQUEMENT en "
    'JSON valide, sans texte autour : {"thought":"...","action":"...","input":"..."} '
    "(input peut être null pour l'action 'finish'). "
    "IMPORTANT : 'thought' doit tenir en une phrase très courte (15 mots maximum) — "
    "ce n'est qu'une note interne, pas une explication détaillée. "
    "N'ajoute STRICTEMENT AUCUN caractère, symbole ou commentaire après "
    "l'accolade fermante finale '}'. Ta réponse doit se terminer exactement par '}'."
)

PROMPT_SYSTEME_CRITIC = (
    "Tu es Critic. Tu vérifies que des sources trouvées par un autre agent "
    "appartiennent bien à UN établissement algérien précis (pas un homonyme, "
    "pas une autre agence/franchise du même réseau). Réponds UNIQUEMENT en JSON, "
    'une clé par source à vérifier : {"website": {"valide": true/false, "raison": "..."}, "facebook": {...}}'
)


class DiscoveryAgent:
    def __init__(self, llm_client: LLMClient, budget_guard: BudgetGuard, headers: dict):
        self.llm_client = llm_client
        self.budget_guard = budget_guard  # lu par le Planner, jamais dupliqué dans le State
        self.tools = {
            "recherche_gratuite": RechercheGratuiteTool(),
            "recherche_payante": RecherchePayanteTool(budget_guard),
            "visiter_url": VisiterUrlTool(headers),
        }

    def run(self, entreprise: Entreprise) -> DiscoverySources:
     print(f"[DISCOVERY][v2-escalade-forcee] {entreprise.nom}")
     state = DiscoveryState(entreprise=entreprise)

     while not state.termine and state.iteration < MAX_ITERATIONS:
        decision = self._reason(state)
        if decision.action == "finish":
            if self._doit_forcer_payant(state):
                decision.action = "recherche_payante"
                decision.input = self._requete_payante_par_defaut(state.entreprise)
            else:
                state.termine = True
                break
        observation = self._execute(decision, state.entreprise)   # <-- entreprise passée ici
        self._update_state(state, decision, observation)

     self._critiquer(state)

     if self._doit_forcer_payant(state):
        requete = self._requete_payante_par_defaut(state.entreprise)
        observation = self.tools["recherche_payante"].executer(requete)
        self._update_state(state, DiscoveryDecision(thought="", action="recherche_payante", input=requete), observation)
        self._critiquer(state)

     print(f"  → {state.iteration} itération(s), actions : {state.historique_actions}")
     print("Sources trouvées :", state.sources)
     return state.sources

    def _doit_forcer_payant(self, state: DiscoveryState) -> bool:
     aucune_source = not any([state.sources.website, state.sources.facebook,
                              state.sources.linkedin, state.sources.google_business,
                              state.sources.pages_jaunes])
     deja_paye = any("recherche_payante" in a for a in state.historique_actions)
     return aucune_source and not deja_paye and self.budget_guard.restant > 0

    def _requete_payante_par_defaut(self, entreprise: Entreprise) -> str:
     lieu = entreprise.commune_name or entreprise.wilaya_name or ""
     return f"{entreprise.nom} {lieu} Algérie"

    # ---------- Planner ----------
    def _reason(self, state: DiscoveryState) -> DiscoveryDecision:
        prompt = self._construire_prompt(state)
        try:
            brut = self.llm_client.complete(PROMPT_SYSTEME_PLANNER, prompt, max_tokens=500)
        except Exception as e:
            print(f"[DISCOVERY][planner] échec appel LLM : {type(e).__name__}: {e}")
            return DiscoveryDecision(thought="Appel LLM en échec, arrêt.", action="finish")

        try:
            donnees = json.loads(nettoyer_json(brut))
            return DiscoveryDecision(
                thought=donnees.get("thought", ""),
                action=donnees.get("action", "finish"),
                input=donnees.get("input"),
            )
        except json.JSONDecodeError as e:
            print(f"[DISCOVERY][planner] JSON invalide, tentative de récupération : {e}\nRéponse brute : {brut!r}")
            action_recuperee = extraire_champ_regex(brut, "action")
            input_recupere = extraire_champ_regex(brut, "input")
            if action_recuperee:
                return DiscoveryDecision(thought="(récupéré depuis un JSON tronqué)",
                                          action=action_recuperee, input=input_recupere)
            return DiscoveryDecision(thought="Réponse LLM non exploitable, arrêt.", action="finish")

    def _construire_prompt(self, state: DiscoveryState) -> str:
        e = state.entreprise
        lieu = e.commune_name or e.wilaya_name or ""
        trouvees = {k: v for k, v in state.sources.to_dict().items()
                    if k in ("website", "facebook", "linkedin", "google_business", "pages_jaunes") and v}
        return (
            f"Entreprise : {e.nom} ({e.sous_secteur}), {lieu}, Algérie.\n\n"
            f"Sources déjà trouvées : {trouvees or 'aucune'}\n"
            f"Historique : {state.historique_actions or 'aucun'}\n"
            f"Dernières observations : {state.observations[-3:] or 'aucune'}\n"
            f"Budget recherche payante restant : {self.budget_guard.restant}/{self.budget_guard.plafond_appels} appels\n\n"
            "Outils disponibles :\n"
            "- recherche_gratuite (input: requête texte)\n"
            "- recherche_payante (input: requête texte — coûte du budget, en dernier recours)\n"
            "- visiter_url (input: une URL précise à confirmer)\n"
            "- finish (input: null, quand les sources utiles sont trouvées ou qu'il n'y a plus rien à essayer)\n"
        )

    # ---------- Executor ----------
    def _execute(self, decision: DiscoveryDecision, entreprise: Entreprise) -> DiscoveryObservation:
     outil = self.tools.get(decision.action)
     if outil is None:
        return DiscoveryObservation(resume=f"Action inconnue : {decision.action}")

     requete = decision.input or ""
     if decision.action in ("recherche_gratuite", "recherche_payante"):
        lieu = entreprise.commune_name or entreprise.wilaya_name or ""
        if lieu and lieu.lower() not in requete.lower():
            requete = f"{requete} {lieu}".strip()

     return outil.executer(requete)

    # ---------- Mémoire ----------
    def _update_state(self, state: DiscoveryState, decision: DiscoveryDecision, observation: DiscoveryObservation):
        state.iteration += 1
        state.historique_actions.append(f"{decision.action}({decision.input})")
        state.observations.append(observation.resume)

        for resultat in observation.resultats:
            type_source = classifier_url(resultat.url)
            confiance = similarite_nom_domaine(state.entreprise.nom, resultat.url)
            if type_source == "website":
                if state.sources.website is None or confiance > state.sources.confidence.get("website", -1):
                    state.sources.website = resultat.url
                    state.sources.confidence["website"] = confiance
            elif type_source == "annuaire":
               if resultat.url not in state.sources.annuaires:
                    state.sources.annuaires.append(resultat.url)
       
            elif type_source and getattr(state.sources, type_source) is None:
                setattr(state.sources, type_source, resultat.url)
                state.sources.confidence[type_source] = confiance

        # signal explicite renvoyé par l'outil, jamais déduit du texte du résumé
        if observation.paiement_effectue:
            state.sources.recherche_payante_utilisee = True

    # ---------- Critic ----------
    def _critiquer(self, state: DiscoveryState):
        """Revalidation finale : un seul appel LLM pour toutes les sources trouvées,
        pas un par source (sinon le Critic coûte aussi cher que le Planner)."""
        trouvees = {k: v for k, v in state.sources.to_dict().items()
                    if k in ("website", "facebook", "linkedin", "google_business", "pages_jaunes") and v}
        if not trouvees:
            return

        e = state.entreprise
        prompt = (
            f"Établissement attendu : {e.nom} ({e.sous_secteur}), "
            f"{e.commune_name or e.wilaya_name or ''}, Algérie.\n\n"
            f"Sources trouvées : {trouvees}\n\n"
            "Pour chacune, dis si elle appartient bien à CET établissement précis. "
            "Réponds en JSON, une clé par source listée ci-dessus."
        )

        try:
            brut = self.llm_client.complete(PROMPT_SYSTEME_CRITIC, prompt, max_tokens=300)
        except Exception as e:
            print(f"[DISCOVERY][critic] échec appel LLM : {type(e).__name__}: {e}")
            return  # Critic indisponible : on garde les sources telles quelles plutôt que deviner

        try:
            verdicts = json.loads(nettoyer_json(brut))
        except json.JSONDecodeError as e:
            print(f"[DISCOVERY][critic] JSON invalide : {e}\nRéponse brute : {brut!r}")
            return
        state.sources.critic_valide = True
        for type_source, verdict in verdicts.items():
            if isinstance(verdict, dict) and verdict.get("valide") is False and hasattr(state.sources, type_source):
                setattr(state.sources, type_source, None)
                state.sources.confidence.pop(type_source, None)
                state.observations.append(f"Critic a rejeté {type_source} : {verdict.get('raison', '')}")
