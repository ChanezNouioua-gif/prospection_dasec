#!/usr/bin/env python3
"""
Résout commune_id pour les lignes qui ont commune_brute (texte) + wilaya_name
déjà connue, en fuzzy-matchant commune_brute contre les communes de CETTE
wilaya uniquement (restreint le champ de recherche, évite les faux matches
inter-wilayas).

Les commune_brute en arabe ne matcheront probablement à rien (communes.commune_name
est en français/latin uniquement) — c'est voulu : mieux vaut ne rien assigner
qu'assigner au hasard.

Usage:
    python fuzzy_match_communes.py --dry-run
    python fuzzy_match_communes.py --apply --seuil 0.75
"""

import sqlite3
import argparse
import difflib
import unicodedata

DB_PATH = "data/dasec_prospection.db"


def normaliser(texte: str) -> str:
    if not texte:
        return ""
    texte = texte.lower().strip()
    texte = "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")
    for car in ["-", "_", "'", ".", ","]:
        texte = texte.replace(car, " ")
    return " ".join(texte.split())


def meilleur_match(commune_brute: str, wilaya_name: str, candidats: list[tuple[int, str]]) -> tuple[int, str, float] | None:
    """candidats = [(id, nom), ...] restreints à une wilaya."""
    cible = normaliser(commune_brute)
    if not cible:
        return None

    # Un commune_brute qui n'est que le nom de la wilaya répété ("Alger", "Oran"...)
    # n'identifie rien de précis SAUF s'il existe une commune portant EXACTEMENT
    # ce nom (cas fréquent : la commune chef-lieu porte le même nom que la wilaya).
    # Dans ce cas on ne doit matcher que l'exact, jamais une sous-chaîne partielle
    # (interdiction du boost substring ci-dessous pour ce cas précis).
    est_juste_le_nom_wilaya = cible == normaliser(wilaya_name)

    meilleur = None
    meilleur_score = 0.0
    for id_, nom in candidats:
        nom_norm = normaliser(nom)
        score = difflib.SequenceMatcher(None, cible, nom_norm).ratio()

        if est_juste_le_nom_wilaya:
            if cible != nom_norm:
                continue  # seul un match EXACT est acceptable ici, pas de boost substring
        elif len(cible) >= 4 and (cible in nom_norm or nom_norm in cible):
            score = max(score, 0.85)

        if score > meilleur_score:
            meilleur_score = score
            meilleur = (id_, nom, score)
    return meilleur


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--seuil", type=float, default=0.75, help="Score minimum de similarité pour accepter le match (0-1)")
    parser.add_argument("--limite-dry-run", type=int, default=40)
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Précise --dry-run ou --apply.")
        return

    conn = sqlite3.connect(DB_PATH, timeout=30)  # timeout généreux : l'enrichissement tourne en parallèle dans un autre terminal
    conn.execute("PRAGMA busy_timeout = 30000")
    cur = conn.cursor()

    cur.execute("SELECT id, commune_name, wilaya_name FROM communes")
    communes_par_wilaya = {}
    for id_, nom, wilaya in cur.fetchall():
        communes_par_wilaya.setdefault(wilaya, []).append((id_, nom))

    cur.execute("""
        SELECT id, commune_brute, wilaya_name FROM entreprises
        WHERE commune_id IS NULL AND commune_brute IS NOT NULL AND commune_brute != ''
          AND wilaya_name IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f"{len(rows)} lignes à traiter.\n")

    resolus, non_resolus = [], []

    for id_, commune_brute, wilaya_name in rows:
        candidats = communes_par_wilaya.get(wilaya_name, [])
        match = meilleur_match(commune_brute, wilaya_name, candidats)
        if match and match[2] >= args.seuil:
            resolus.append((id_, commune_brute, wilaya_name, match[0], match[1], round(match[2], 2)))
        else:
            non_resolus.append((id_, commune_brute, wilaya_name, match[1] if match else None, round(match[2], 2) if match else 0))

    print(f"Résolus (score >= {args.seuil}) : {len(resolus)}")
    print(f"Non résolus : {len(non_resolus)}\n")

    if args.dry_run:
        print(f"--- Échantillon des RÉSOLUS (max {args.limite_dry_run}) ---")
        for id_, brute, wilaya, commune_id, nom_match, score in resolus[:args.limite_dry_run]:
            print(f"  id={id_:6} '{brute}' ({wilaya}) -> '{nom_match}' [score={score}]")

        print(f"\n--- Échantillon des NON RÉSOLUS (max {args.limite_dry_run}) ---")
        for id_, brute, wilaya, meilleur_nom, score in non_resolus[:args.limite_dry_run]:
            print(f"  id={id_:6} '{brute}' ({wilaya}) -> meilleur candidat: '{meilleur_nom}' [score={score}, rejeté]")

        print(f"\nRien n'est écrit en DB. Relance avec --apply --seuil {args.seuil} pour appliquer.")

    elif args.apply:
        for id_, brute, wilaya, commune_id, nom_match, score in resolus:
            cur.execute("UPDATE entreprises SET commune_id = ? WHERE id = ?", (commune_id, id_))
        conn.commit()
        print(f"{len(resolus)} lignes mises à jour avec commune_id.")
        print(f"{len(non_resolus)} lignes laissées de côté (score < {args.seuil} ou pas de candidat dans leur wilaya).")

    conn.close()


if __name__ == "__main__":
    main()