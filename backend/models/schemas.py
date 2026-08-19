"""
Modèles de données échangés entre agents.

Principe : les agents ne se passent jamais de dict "libres" entre eux.
Ils communiquent via ces dataclasses, ce qui évite les erreurs de clé
manquante/mal orthographiée et rend chaque contrat d'agent explicite
et testable indépendamment des autres.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Entreprise:
    """Reflète une ligne de la table `entreprises`. Lecture seule pour les agents
    autres que DatabaseAgent — aucun agent ne doit modifier ceci directement en base."""
    id: int
    nom: str
    secteur: str
    sous_secteur: str
    type_gestion: Optional[str] = None
    telephone: Optional[str] = None
    telephone2: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    adresse: Optional[str] = None
    commune_brute: Optional[str] = None
    commune_name: Optional[str] = None
    wilaya_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @classmethod
    def from_row(cls, row: dict) -> "Entreprise":
        champs_valides = {k: v for k, v in row.items() if k in cls.__dataclass_fields__}
        return cls(**champs_valides)


@dataclass
class DiscoverySources:
    """Sortie du DiscoveryAgent : uniquement des sources, aucune donnée de contact.
    `confidence` (0-100 par source) permet aux agents suivants et à un futur contrôle
    humain de savoir si une source a été trouvée avec certitude ou par déduction faible."""
    website: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    google_business: Optional[str] = None
    pages_jaunes: Optional[str] = None
    annuaires: list = field(default_factory=list)  # sources tierces à scraper pour contact, jamais présentées comme site officiel
    confidence: dict = field(default_factory=dict)  # ex: {"website": 98, "facebook": 60}
    recherche_payante_utilisee: bool = False
    critic_valide: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProfileData:
    """Sortie du ProfileAgent : toutes les données extraites des sources trouvées
    par le DiscoveryAgent. Tous les champs sont optionnels — une source injoignable
    ou muette sur un point ne doit jamais faire planter le pipeline."""
    telephone: Optional[str] = None
    telephone2: Optional[str] = None
    email: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    email_qualite: Optional[int] = None       # 0 générique, 1 propre au domaine
    site_web_qualite: Optional[int] = None    # 0 absent, 1 obsolète, 2 à jour
    effectif: Optional[str] = None            # '<10' / '10-100' / '>100'
    reseau_groupe: Optional[int] = None        # 0 / 1
    reseau_nom: Optional[str] = None
    contact_nom: Optional[str] = None
    contact_fonction: Optional[str] = None
    annuaire_source: Optional[str] = None 
    contact_email_personnel: Optional[str] = None      # NOUVEAU
    contact_telephone_personnel: Optional[str] = None  # NOUVEAU
    contact_linkedin_personnel: Optional[str] = None   # NOUVEAU  
    sources_utilisees: dict = field(default_factory=dict)  # traçabilité : quelle page a donné quel champ

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoreResult:
    """Sortie du ScoringAgent. `detail` garde la décomposition du calcul pour
    pouvoir expliquer un score à l'entreprise sans deviner a posteriori."""
    score_dasec: float
    score_completude: float
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunLogEntry:
    """Une ligne de suivi par établissement traité, pour diagnostiquer un run
    sans avoir à rejouer tout le pipeline."""
    entreprise_id: int
    etape: str
    statut: str  # 'ok' / 'echec' / 'ignore'
    detail: Optional[str] = None
    cout_estime_usd: float = 0.0


@dataclass
class DiscoveryObservation:
    """Résultat brut de l'exécution d'un outil par DiscoveryAgent — ce que
    l'agent 'observe' après avoir agi, avant de décider du prochain tour.
    `resultats` contient des tools.web_search.ResultatRecherche, laissé non
    typé ici pour éviter une dépendance models -> tools."""
    resume: str
    resultats: list = field(default_factory=list)
    paiement_effectue: bool = False  # signal explicite, ne jamais déduire ça d'un texte libre


@dataclass
class DiscoveryDecision:
    """Une décision du Planner : quelle action, avec quel input."""
    thought: str
    action: str
    input: Optional[str] = None


@dataclass
class DiscoveryState:
    """Mémoire de travail d'une mission DiscoveryAgent, un état par établissement."""
    entreprise: Entreprise
    sources: DiscoverySources = field(default_factory=DiscoverySources)
    iteration: int = 0
    historique_actions: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    termine: bool = False

