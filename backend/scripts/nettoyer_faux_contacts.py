"""
Nettoyage rétroactif : revérifie tous les contact_telephone_personnel et
contact_email_personnel déjà en base, et vide ceux qui sont en réalité
identiques au contact générique de l'entreprise (telephone/email) —
symptôme observé : l'enrichissement "personnel" ramène en fait les
coordonnées du standard, pas celles du décideur.

Complète nettoyer_faux_linkedin.py (qui ne traite que le LinkedIn) :
à lancer en plus, pas à la place.

Ne fait AUCUN appel réseau — relit juste ce qui est déjà stocké.

Usage :
    python scripts/nettoyer_faux_contacts.py              # dry-run, affiche seulement
    python scripts/nettoyer_faux_contacts.py --appliquer
    python scripts/nettoyer_faux_contacts.py --appliquer --reset-tente
"""

import argparse
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_PATH
from database.connection import obtenir_connexion


def _normaliser_telephone(tel: str) -> str:
    return re.sub(r"\D", "", tel or "")


def _telephones_identiques(a: str, b: str) -> bool:
    na, nb = _normaliser_telephone(a), _normaliser_telephone(b)
    if not na or not nb:
        return False
    # compare sur les 8 derniers chiffres pour absorber +213 / 0 / indicatif wilaya
    return na[-8:] == nb[-8:]


def _emails_identiques(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def main():
    parser = argparse.ArgumentParser(description="Nettoyage rétroactif des faux contacts tel/email.")
    parser.add_argument("--appliquer", action="store_true",
                         help="Sans ce flag : dry-run, affiche seulement ce qui serait nettoyé.")
    parser.add_argument("--reset-tente", action="store_true",
                         help="Remet aussi contact_personnel_tente à 0 pour les lignes nettoyées, "
                              "pour qu'elles soient retraitées au prochain enrichissement.")
    args = parser.parse_args()

    with obtenir_connexion(DB_PATH) as connexion:
        rows = connexion.execute("""
            SELECT id, nom, telephone, email,
                   contact_nom, contact_telephone_personnel, contact_email_personnel
            FROM entreprises
            WHERE contact_telephone_personnel IS NOT NULL
               OR contact_email_personnel IS NOT NULL
        """).fetchall()

        a_nettoyer_tel = []
        a_nettoyer_email = []
        for row in rows:
            d = dict(row)
            if d["contact_telephone_personnel"] and _telephones_identiques(
                d["contact_telephone_personnel"], d["telephone"]
            ):
                a_nettoyer_tel.append(d)
            if d["contact_email_personnel"] and _emails_identiques(
                d["contact_email_personnel"], d["email"]
            ):
                a_nettoyer_email.append(d)

        print(f"{len(rows)} entreprises avec un contact personnel en base.")
        print(f"{len(a_nettoyer_tel)} téléphones 'personnels' == standard général :")
        for d in a_nettoyer_tel:
            print(f"  — {d['nom']} : contact_nom={d['contact_nom']!r} "
                  f"tel_personnel={d['contact_telephone_personnel']!r} standard={d['telephone']!r}")

        print(f"\n{len(a_nettoyer_email)} emails 'personnels' == contact générique :")
        for d in a_nettoyer_email:
            print(f"  — {d['nom']} : contact_nom={d['contact_nom']!r} "
                  f"email_personnel={d['contact_email_personnel']!r} generique={d['email']!r}")

        if not args.appliquer:
            print("\nDry-run : rien n'a été modifié. Relance avec --appliquer pour nettoyer pour de vrai.")
            return

        ids_tel = {d["id"] for d in a_nettoyer_tel}
        ids_email = {d["id"] for d in a_nettoyer_email}
        ids_tous = ids_tel | ids_email

        for id_ in ids_tous:
            champs = []
            valeurs = []
            if id_ in ids_tel:
                champs.append("contact_telephone_personnel = NULL")
            if id_ in ids_email:
                champs.append("contact_email_personnel = NULL")
            if args.reset_tente:
                champs.append("contact_personnel_tente = 0")
            connexion.execute(
                f"UPDATE entreprises SET {', '.join(champs)} WHERE id = ?",
                (id_,),
            )
        connexion.commit()
        print(f"\n{len(ids_tous)} lignes nettoyées "
              f"({len(ids_tel)} téléphone, {len(ids_email)} email, "
              f"{len(ids_tel & ids_email)} les deux).")
        if args.reset_tente:
            print("contact_personnel_tente remis à 0 pour ces lignes : elles seront retraitées au prochain run.")


if __name__ == "__main__":
    main()