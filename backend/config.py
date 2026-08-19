"""
Configuration centrale du projet.

Tout ce qui est "réglage métier" (barèmes, poids, budget, clés d'API) vit ici,
jamais en dur dans un agent. Les clés d'API viennent de variables d'environnement
(.env, jamais commité) via python-dotenv.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


import os
from dotenv import load_dotenv

load_dotenv()

# --- Base de données ---
DB_PATH = os.getenv("DB_PATH", "data/dasec_prospection.db")

# --- Fournisseurs LLM ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # 'anthropic' ou 'openai'
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
import os


_gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in _gemini_keys_raw.split(",") if k.strip()]

if not GEMINI_API_KEYS:
    _legacy = os.getenv("GEMINI_API_KEY", "")
    if _legacy:
        GEMINI_API_KEYS = [_legacy]

# --- Recherche web (gratuit d'abord, payant en secours si le Planner le décide) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BUDGET_MAX_APPELS_SERPER_PAR_RUN = int(os.getenv("BUDGET_MAX_APPELS_SERPER_PAR_RUN", "400"))
# 150 = large marge pour un pilote de 100 fiches (chaque fiche peut nécessiter
# 1 à 2 requêtes de secours) tout en gardant un plafond dur.

# --- Limitation de débit (leçon tirée des blocages Overpass/SQLite du notebook) ---
DELAI_ENTRE_ETABLISSEMENTS_SEC = 1.5
DELAI_ENTRE_APPELS_RECHERCHE_SEC = 1.0
MAX_ESSAIS_RESEAU = 3

# --- Barème de scoring par secteur ---
# Un secteur = une config complète, indépendante des autres.
# Pour ajouter un secteur (banques, assurances, cabinets d'avocats...),
# il suffit d'ajouter une entrée ici — aucun agent n'a besoin d'être modifié.
SECTOR_CONFIGS = {
    "santé": {
        "bareme_sous_secteur": {
            "CHU": 10, "clinique privée": 10, "EPH": 10, "hôpital": 10, "EH": 10,
            "CAC": 7, "EHS": 7, "laboratoire d'analyses": 7,
            "centre de transfusion sanguine": 7,
            "cabinet médical": 4, "cabinet dentaire": 4,
            "pharmacie": 2, "opticien": 2,
        },
        "minimum_si_reseau_groupe": 7,
        "bonus_type_gestion": {"privé": 2, "public": 0, "inconnu": 0},
        "poids": {
            "secteur": 0.25,
            "commune": 0.10,
            "effectif": 0.30,
            "maturite_digitale": 0.25,
            "reseau_groupe": 0.10,
        },
        "score_effectif": {"<10": 20, "10-100": 60, ">100": 100},
    },

    # --- NOUVEAU : à valider avec toi avant utilisation en prod ---

    "étatique": {
        "bareme_sous_secteur": {
            "siège de wilaya": 10,
            "mairie": 5,
        },
        "minimum_si_reseau_groupe": 0,  # pas de notion de "réseau" pour le secteur public
        "bonus_type_gestion": {"privé": 0, "public": 0, "inconnu": 0},
        "poids": {
            "secteur": 0.30,
            "commune": 0.20,
            "effectif": 0.30,
            "maturite_digitale": 0.15,
            "reseau_groupe": 0.05,
        },
        "score_effectif": {"<10": 20, "10-100": 60, ">100": 100},
    },

    "assurance": {
        "bareme_sous_secteur": {
            "assurance privée": 10,
            "CNAS": 6,
            "CASNOS": 6,
        },
        "minimum_si_reseau_groupe": 7,
        "bonus_type_gestion": {"privé": 2, "public": 0, "inconnu": 0},
        "poids": {
            "secteur": 0.25,
            "commune": 0.10,
            "effectif": 0.30,
            "maturite_digitale": 0.25,
            "reseau_groupe": 0.10,
        },
        "score_effectif": {"<10": 20, "10-100": 60, ">100": 100},
    },

    "industrie": {
        "bareme_sous_secteur": {
            "entreprise industrielle": 10,
        },
        "minimum_si_reseau_groupe": 7,
        "bonus_type_gestion": {"privé": 2, "public": 0, "inconnu": 0},
        "poids": {
            "secteur": 0.20,
            "commune": 0.10,
            "effectif": 0.35,
            "maturite_digitale": 0.25,
            "reseau_groupe": 0.10,
        },
        "score_effectif": {"<10": 20, "10-100": 60, ">100": 100},
    },

    "juridique": {
        "bareme_sous_secteur": {
            "notaire": 10,
            "cabinet d'avocat": 7,
            "cabinet comptable": 7,
        },
        "minimum_si_reseau_groupe": 6,
        "bonus_type_gestion": {"privé": 2, "public": 0, "inconnu": 0},
        "poids": {
            "secteur": 0.30,
            "commune": 0.15,
            "effectif": 0.20,
            "maturite_digitale": 0.25,
            "reseau_groupe": 0.10,
        },
        "score_effectif": {"<10": 30, "10-100": 70, ">100": 100},
    },
}

DOMAINES_EMAIL_GENERIQUES = {
    "gmail.com", "yahoo.fr", "yahoo.com", "hotmail.com", "hotmail.fr",
    "outlook.com", "outlook.fr", "live.com", "live.fr",
}
