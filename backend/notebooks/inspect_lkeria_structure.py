#!/usr/bin/env python3
with open("lkeria_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

# Cherche la zone de pagination (généralement classe "pagination" ou similaire)
for marker in ["pagination", "page-numbers", "nav-links", "paginate"]:
    idx = html.find(marker)
    if idx != -1:
        print(f"Marqueur '{marker}' trouvé à la position {idx} :\n")
        print(html[max(0, idx-200):idx+1200])
        print("\n" + "="*70 + "\n")

# Combien d'articles (fiches) sont réellement présents sur cette page ?
nb_articles = html.count('<article class="hentry">')
print(f"Nombre de fiches <article class=\"hentry\"> trouvées sur cette page : {nb_articles}")