"""
À exécuter sur ta machine locale (dans le venv du projet), pas dans un
environnement restreint — pour mesurer le vrai taux de succès du backend
Brave via ddgs sur un échantillon représentatif de tes requêtes réelles.
"""
import time
from ddgs import DDGS

requetes = [
    '"Dr Djennaoui Nourdine" Clinique Ennahda LinkedIn',
    '"Mohammed MOUFFOK" Clinique Hammadites LinkedIn',
    '"Mansour Kara" Clinique Kara LinkedIn',
    '"Dr. Amine Cherrak" Clinique Cherrak El Ghosli LinkedIn',
    '"Faudel Riad Guelai" El Hikma LinkedIn',
    '"Abdelaziz Baloul" Baloul LinkedIn',
    '"Ahmed Benhamouda" Centre Anti-Cancer de Batna LinkedIn',
    '"Nabil OUHBA" Compagnie Algérienne assurance LinkedIn',
    '"S. Oukrif" EHS Pierre et Marie Curie CPMC LinkedIn',
    '"Zoubir Rekik" EHS Salim Zemirli LinkedIn',
]

succes, echecs, vides = 0, 0, 0
for q in requetes:
    try:
        with DDGS(timeout=10) as ddgs:
            r = list(ddgs.text(q, max_results=8, backend="brave"))
        if r:
            print(f"OK  ({len(r)} résultats) : {q}")
            succes += 1
        else:
            print(f"VIDE (0 résultat)       : {q}")
            vides += 1
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e} : {q}")
        echecs += 1
    time.sleep(2)

print(f"\n{succes} succès / {vides} vides / {echecs} échecs sur {len(requetes)} requêtes")