#!/usr/bin/env python3
"""
Construit la liste des décideurs à retraiter (confiance Faible ou Aucun
contact), triée par priorité secteur (même ordre que SECTOR_CONFIGS) puis
par gravité (Aucun contact avant Faible), et génère UNE SEULE commande
`main.py --ids "..."` à coller.

Pourquoi un seul appel plutôt qu'un par secteur ?
Le budget Serper (BUDGET_MAX_APPELS_SERPER_PAR_RUN) est remis à zéro à
chaque lancement de main.py. Un seul appel avec la liste complète, déjà
triée par priorité, garantit que le budget s'épuise naturellement dans le
bon ordre (santé d'abord) plutôt que d'être gaspillé en 150 requêtes par
secteur.

Usage:
    python build_retraitement_queue.py                    # aperçu, rien n'est lancé
    python build_retraitement_queue.py --max-entreprises 60
"""

import sqlite3
import argparse
import json

DB_PATH = "data/dasec_prospection.db"

# Même ordre que config.SECTOR_CONFIGS, donné par Nina.
ORDRE_PRIORITE_SECTEURS = ["santé", "étatique", "assurance", "industrie", "juridique"]

# Estimation d'appels LLM par entreprise (Planner jusqu'à 5 itérations +
# Critic + Profile). Fourchette large car ça dépend de la difficulté du cas.
ESTIMATION_APPELS_LLM_MIN = 3
ESTIMATION_APPELS_LLM_MAX = 6

# Ratio Serper réel observé (pas 1:1) : avec DDG cassé la plupart du temps,
# le Planner ET ProfileAgent._rechercher_decideur retombent tous deux sur le
# payant plus souvent que prévu. Mesuré : 86 appels Serper pour 50 entreprises
# traitées (run du 16/08) = ~1.72 appel payant par entreprise en moyenne.
RATIO_SERPER_PAR_ENTREPRISE = 1.72
BUDGET_SERPER_PAR_RUN = 150  # doit rester synchro avec config.BUDGET_MAX_APPELS_SERPER_PAR_RUN


def calculer_confiance_simplifiee(row: dict) -> str:
    """Reproduit la logique de calculer_confiance_contact() côté backend,
    juste assez pour classer Aucun contact vs Faible vs Moyenne/Élevée
    sans dupliquer tout le détail des raisons (pas nécessaire ici)."""
    if not row.get("contact_nom"):
        return "Aucun contact"

    points = 25  # identité trouvée
    if row.get("contact_fonction"):
        points += 15

    try:
        confiance_sources = json.loads(row.get("sources_confidence") or "{}")
    except (json.JSONDecodeError, TypeError):
        confiance_sources = {}

    if confiance_sources.get("linkedin", 0) >= 70:
        points += 30
    elif confiance_sources.get("website", 0) >= 70:
        points += 20

    if row.get("email") and row.get("email_qualite") == 1:
        points += 30
    elif row.get("email"):
        points += 10

    if points >= 70:
        return "Élevée"
    elif points >= 40:
        return "Moyenne"
    return "Faible"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-entreprises", type=int, default=50,
                         help="Limite le nombre total d'entreprises dans la file (défaut: 50, ton usage habituel)")
    parser.add_argument("--secteurs", nargs="+", default=ORDRE_PRIORITE_SECTEURS,
                         help="Sous-ensemble de secteurs à traiter, dans l'ordre voulu (défaut: tous, ordre standard)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    cur = conn.cursor()

    file_ordonnee = []  # [(id, secteur, sous_secteur, confiance), ...]

    for secteur in args.secteurs:
        cur.execute("""
            SELECT id, sous_secteur, contact_nom, contact_fonction, email, email_qualite, sources_confidence
            FROM entreprises
            WHERE secteur = ?
        """, (secteur,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        candidats_secteur = []
        for row in rows:
            d = dict(zip(cols, row))
            conf = calculer_confiance_simplifiee(d)
            if conf in ("Aucun contact", "Faible"):
                candidats_secteur.append((d["id"], secteur, d["sous_secteur"], conf))

        # Aucun contact avant Faible, au sein d'un même secteur
        candidats_secteur.sort(key=lambda x: 0 if x[3] == "Aucun contact" else 1)
        file_ordonnee.extend(candidats_secteur)

        print(f"{secteur:12} : {len(candidats_secteur):5} à retraiter "
              f"({sum(1 for c in candidats_secteur if c[3]=='Aucun contact')} aucun contact, "
              f"{sum(1 for c in candidats_secteur if c[3]=='Faible')} faible)")

    conn.close()

    total_disponible = len(file_ordonnee)
    print(f"\nTotal disponible (tous secteurs confondus) : {total_disponible}")

    if args.max_entreprises:
        file_ordonnee = file_ordonnee[:args.max_entreprises]
        print(f"Limité à --max-entreprises {args.max_entreprises} -> {len(file_ordonnee)} retenues")

    ids = [str(x[0]) for x in file_ordonnee]
    n = len(ids)

    print(f"\n{'='*70}")
    print(f"Estimation de charge pour cette session ({n} entreprises)")
    print(f"{'='*70}")
    print(f"Appels LLM (Gemini) estimés : {n * ESTIMATION_APPELS_LLM_MIN} à {n * ESTIMATION_APPELS_LLM_MAX}")

    serper_estime = round(n * RATIO_SERPER_PAR_ENTREPRISE)
    depassement = serper_estime > BUDGET_SERPER_PAR_RUN
    marqueur = "  ⚠️  DÉPASSE le budget !" if depassement else ""
    print(f"Appels Serper estimés (ratio réel ~{RATIO_SERPER_PAR_ENTREPRISE}/entreprise, DDG cassé) : ~{serper_estime}/{BUDGET_SERPER_PAR_RUN}{marqueur}")
    if depassement:
        max_sur = int(BUDGET_SERPER_PAR_RUN / RATIO_SERPER_PAR_ENTREPRISE)
        print(f"   -> à ce ratio, {max_sur} entreprises est le maximum sûr pour rester sous {BUDGET_SERPER_PAR_RUN} appels.")
        print(f"      Au-delà, les dernières entreprises de la liste risquent de manquer de recherche")
        print(f"      payante ET gratuite (DDG cassé) une fois le budget épuisé.")
    print("Vérifie aussi que le total LLM tient dans ton quota Gemini du jour avant de lancer.")

    if n == 0:
        print("\nRien à traiter avec ces critères.")
        return

    print(f"\n{'='*70}")
    print("Commande prête à coller :")
    print(f"{'='*70}")
    print(f'python main.py --ids "{",".join(ids)}"')


if __name__ == "__main__":
    main()