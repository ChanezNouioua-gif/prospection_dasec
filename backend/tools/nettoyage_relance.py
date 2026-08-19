"""
1) Efface email/telephone des entrées identifiées par audit_pollution.py
   comme sourcées d'un annuaire ou d'un email placeholder.
2) Affiche la commande à lancer pour relancer Discovery+Profile+Scoring
   dessus (main.py gère déjà le traitement par lot d'IDs).
"""

import sqlite3

IDS_ANNUAIRE = [1, 2, 3, 5, 6, 7, 8, 11, 14, 15, 18, 21, 22, 32, 33, 35,
                51, 59, 61, 63, 64, 66, 70, 71, 73, 96, 97, 102, 104, 106]
IDS_PLACEHOLDER = [30]  # email=info@example.com, pas un problème d'annuaire


def nettoyer(chemin_db: str):
    conn = sqlite3.connect(chemin_db)

    tous_ids = IDS_ANNUAIRE + IDS_PLACEHOLDER
    placeholders = ",".join("?" * len(tous_ids))
    conn.execute(
        f"UPDATE entreprises SET email = NULL, telephone = NULL WHERE id IN ({placeholders})",
        tous_ids,
    )
    conn.commit()
    conn.close()
    print(f"{len(tous_ids)} entrées nettoyées (email + telephone remis à NULL).")
    print("\nRelance avec :")
    print(f"python main.py --ids {','.join(str(i) for i in tous_ids)}")


if __name__ == "__main__":
    nettoyer("data/dasec_prospection.db")