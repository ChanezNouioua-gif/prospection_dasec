#!/usr/bin/env python3
"""
Test décisif : "BENAKILA" est un nom de notaire qu'on a vu affiché sur la page
Alger. S'il n'apparaît PAS dans le HTML brut renvoyé par requests, ça confirme
que le contenu des fiches est chargé en JavaScript après le chargement initial
(donc invisible pour requests/BeautifulSoup, il faudra un navigateur headless).
"""

import requests

URL = "https://www.lkeria.com/notaire-alger-16.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = requests.get(URL, headers=HEADERS, timeout=15)
print(f"Status: {r.status_code}, longueur: {len(r.text)} caractères\n")

for terme in ["BENAKILA", "benakilaek@yahoo.fr", "0770 35 40 55", "CHOUCHANE"]:
    trouve = terme in r.text
    print(f"  '{terme}' présent dans le HTML brut : {'OUI' if trouve else 'NON'}")

print()
if "BENAKILA" not in r.text:
    print("=> CONFIRMÉ : le contenu des fiches est chargé dynamiquement (JS/AJAX).")
    print("   requests + BeautifulSoup ne suffiront pas pour ce site.")
    print("   Il faudra soit trouver l'endpoint AJAX appelé par le JS, soit")
    print("   utiliser un navigateur headless (Playwright/Selenium).")
else:
    print("=> Le contenu EST présent en brut, le problème vient d'ailleurs (regex à revoir).")

# Sauvegarde la page complète pour inspection manuelle si besoin
with open("lkeria_debug.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("\nPage brute sauvegardée dans lkeria_debug.html pour inspection si besoin.")