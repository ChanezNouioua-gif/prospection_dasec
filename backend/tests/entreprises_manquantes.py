"""
Liste tous les établissements du sous-secteur EPH jamais passés par DiscoveryAgent
(recherche_payante_utilisee et critic_valide encore NULL = jamais touchés).

Usage :
    python trouver_eph_restants.py
    python trouver_eph_restants.py --taille-lot 40   # découpe la liste en lots

Ajuste SOUS_SECTEUR si la valeur exacte diffère dans ta base
(vérifie avec : SELECT DISTINCT sous_secteur FROM entreprises).
"""

import argparse
import sqlite3

CHEMIN_DB = "data/dasec_prospection.db"
SOUS_SECTEUR = "hôpital"
SECTEUR = "santé"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--taille-lot", type=int, default=0,
                         help="Découpe la liste en lots de N IDs (0 = tout afficher d'un bloc)")
    args = parser.parse_args()

    conn = sqlite3.connect(CHEMIN_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nom FROM entreprises
        WHERE secteur = ?
        AND recherche_payante_utilisee IS NULL
        AND critic_valide IS NULL
        ORDER BY id
    """, (SECTEUR,))
    restants = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM entreprises WHERE secteur = ?", (SECTEUR,))
    total_eph = cur.fetchone()[0]
    conn.close()

    deja_traites = total_eph - len(restants)
    print(f"secteur '{SECTEUR}' : {total_eph} au total, "
          f"{deja_traites} déjà traités, {len(restants)} restants.\n")

    if not restants:
        print("Rien à traiter, tous les EPH sont passés par DiscoveryAgent.")
        return

    ids = [str(r[0]) for r in restants]

    if args.taille_lot > 0:
        lots = [ids[i:i + args.taille_lot] for i in range(0, len(ids), args.taille_lot)]
        print(f"Découpé en {len(lots)} lot(s) de {args.taille_lot} max :\n")
        for i, lot in enumerate(lots, 1):
            print(f"--- Lot {i}/{len(lots)} ({len(lot)} établissements) ---")
            print(",".join(lot))
            print()
    else:
        print("--- Tous les IDs restants ---")
        print(",".join(ids))


if __name__ == "__main__":
    main()