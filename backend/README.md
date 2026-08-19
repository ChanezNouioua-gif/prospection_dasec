# ProspectionAI

Pipeline multi-agent d'enrichissement et de scoring de la base de prospection DASEC.

## Architecture

```
CoordinatorAgent
    ├── DiscoveryAgent   (1 recherche web -> sources : site, Facebook, LinkedIn, Google Business, Pages Jaunes)
    ├── ProfileAgent     (visite les sources, extrait tél/email par règles, 1 seul appel LLM pour effectif/qualité site/réseau/décideur)
    ├── ScoringAgent      (calcule score_dasec + score_completude selon config.SECTOR_CONFIGS)
    └── DatabaseAgent     (seul composant qui touche SQLite)
```

```
ProspectionAI/
├── agents/           # les 5 agents ci-dessus, un fichier chacun
├── database/
│   ├── connection.py  # connexion SQLite unique (WAL), un seul point d'ouverture/fermeture
│   └── repository.py  # tout le SQL brut, appelé uniquement par DatabaseAgent
├── models/
│   └── schemas.py     # contrats de données entre agents (dataclasses)
├── tools/
│   ├── web_search.py  # DuckDuckGo (gratuit) -> Serper (payant) en secours, avec budget guard
│   ├── llm_client.py  # abstraction Anthropic/OpenAI
│   ├── rules.py        # règles déterministes (email, téléphone, similarité nom/domaine)
│   └── rate_limiter.py # retry + délai + garde-fou budget
├── tests/              # pytest, ne nécessite aucune clé API (tout est mocké/déterministe)
├── notebooks/           # notebooks d'expérimentation (le pipeline "propre" vit hors des notebooks)
├── config.py            # TOUS les réglages (barèmes, poids, budget, .env)
└── main.py               # point d'entrée CLI
```

## Installation

```bash
cd ProspectionAI
pip install -r requirements.txt
cp .env.example .env
# remplis .env : ANTHROPIC_API_KEY (ou OPENAI_API_KEY) et SERPER_API_KEY
```

Place ta base existante (`dasec_prospection.db`) dans `data/`.

## Lancer le test pilote (100 établissements, comme demandé par DASEC)

```bash
python main.py --pilote
```

Ça traite 100 établissements dont `effectif IS NULL` (donc jamais encore enrichis), avec le plafond de sécurité `BUDGET_MAX_APPELS_SERPER_PAR_RUN` (150 par défaut) qui arrête tout le run si dépassé plutôt que de continuer à dépenser.

## Généraliser après validation du pilote

```bash
python main.py --secteur santé --limite 4340
```

## Tests

```bash
pytest tests/ -v
```

Tous les tests tournent sans clé API (schéma, règles, formule de score) — seuls `DiscoveryAgent`/`ProfileAgent` nécessitent une vraie exécution réseau/LLM, testable seulement en conditions réelles sur le pilote.

---

## Points où j'ai remis en question la proposition initiale

**1. Un seul appel LLM par établissement dans ProfileAgent, pas quatre.**
Effectif, qualité du site, réseau/groupe et décideur demandaient chacun un raisonnement — mais ils portent tous sur le même contenu (les pages du site visité). Un unique appel avec une consigne JSON structurée couvre les 4 champs, ce qui divise le coût LLM par ~4 par rapport à 4 agents séparés qui redemanderaient chacun le même contexte. Les règles déterministes (email générique/propre, extraction tél/email via `mailto:`/`tel:`) restent en Python pur, sans LLM, comme tu le proposais.

**2. `enrichment_log`, une table de traçabilité en plus des colonnes finales.**
Sans ça, si un score paraît bizarre dans 2 mois, il n'y a aucun moyen de savoir si `reseau_groupe` vient d'une vraie détection ou d'un échec silencieux du LLM retombé sur une valeur par défaut. Chaque étape (discovery/profile/scoring) logue son statut par établissement — coût quasi nul à l'implémentation, gain réel en debug.

**3. Connexion SQLite unique, gérée par un context manager, mode WAL.**
Ce n'est pas cosmétique : le `database is locked` qu'on a eu plusieurs fois dans le notebook venait exactement du pattern "une fonction ouvre sa propre connexion à l'intérieur d'une boucle". Ici c'est structurellement impossible : `DatabaseAgent` est le seul composant qui reçoit une connexion, ouverte une fois par `main.py`.

**4. `BudgetGuard` avec arrêt dur, pas juste un compteur informatif.**
Tu as un budget limité — un script qui continue de taper Serper après le plafond et te prévient à la fin ne protège rien. Ici, dépasser le plafond lève une exception qui arrête tout le run immédiatement, et `CoordinatorAgent` distingue explicitement "plafond dépassé" (arrête tout) de "erreur sur un établissement" (continue sur le suivant).

**5. Barèmes de scoring dans `config.SECTOR_CONFIGS`, indexés par secteur, pas dans `ScoringAgent`.**
Tu veux étendre à banques/assurances/cabinets d'avocats plus tard — si le barème était en dur dans le code de l'agent, chaque nouveau secteur demanderait de retoucher `ScoringAgent`. Là, ajouter un secteur = ajouter une entrée dans `config.py`, zéro ligne de code à changer ailleurs. `ScoringAgent` lève une erreur explicite si le secteur n'a pas de config, plutôt que de deviner un barème par défaut silencieusement (testé : `test_secteur_sans_config_leve_une_erreur_explicite`).

**6. `maj_profil` ne met à jour QUE les champs vides, jamais un `UPDATE` aveugle.**
Un rerun accidentel sur un établissement déjà enrichi ne doit jamais écraser une donnée déjà validée par un contrôle humain futur. Le repository vérifie l'existant avant d'écrire (testé : `test_maj_profil_n_ecrase_jamais_une_valeur_existante`).

## Limites connues, à valider avec le pilote

- `similarite_nom_domaine` (confiance des sources trouvées par DiscoveryAgent) est une heuristique simple par mots-clés, pas du fuzzy matching — à surveiller sur les 100 premiers résultats, `rapidfuzz` est un remplacement direct si le taux de faux positifs est trop élevé.
- Le seuil "≥2 résultats DuckDuckGo = pas besoin de Serper" (`HybridSearchTool`) est arbitraire — à ajuster une fois qu'on voit, sur le pilote, si des résultats DuckDuckGo nombreux mais non pertinents forcent des faux négatifs (on rate un bon match Serper).
- `ProfileAgent` ne visite que le site officiel pour l'instant — Facebook/LinkedIn sont détectés par DiscoveryAgent mais pas encore visités pour en extraire du contenu (nécessiterait un scraping de leurs pages publiques, plus fragile et pas couvert ici).
