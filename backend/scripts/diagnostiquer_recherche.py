import requests

print("=== Test 1 : accès direct à Brave Search ===")
try:
    r = requests.get(
        "https://search.brave.com/search?q=test",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    print(f"status_code={r.status_code}, taille_reponse={len(r.text)} caractères")
    if r.status_code != 200:
        print("  -> réponse non-200, probable blocage")
    elif len(r.text) < 5000:
        print("  -> réponse anormalement courte, probable page de blocage/captcha")
    else:
        print("  -> ça a l'air normal côté HTTP direct")
except Exception as e:
    print(f"  -> échec réseau : {type(e).__name__}: {e}")

print("\n=== Test 2 : ddgs backend brave ===")
try:
    from ddgs import DDGS
    with DDGS(timeout=10) as ddgs:
        resultats = list(ddgs.text("test", max_results=3, backend="brave"))
    print(f"{len(resultats)} résultat(s) via ddgs/brave")
except Exception as e:
    print(f"  -> échec : {type(e).__name__}: {e}")

print("\n=== Test 3 : ddgs backend duckduckgo (au cas où) ===")
try:
    from ddgs import DDGS
    with DDGS(timeout=10) as ddgs:
        resultats = list(ddgs.text("test", max_results=3, backend="duckduckgo"))
    print(f"{len(resultats)} résultat(s) via ddgs/duckduckgo")
except Exception as e:
    print(f"  -> échec : {type(e).__name__}: {e}")