"""
Règles déterministes — pas d'appel LLM ici.

Philosophie du projet : si une règle Python suffit, on ne paie pas un appel
LLM pour la même réponse. Le LLM est réservé aux cas où le jugement est
nécessaire (effectif estimé, fraîcheur d'un site, détection d'un réseau).
"""

import re
from urllib.parse import urlparse

from backend.config import DOMAINES_EMAIL_GENERIQUES

REGEX_TEL_DZ = re.compile(r"(?:\+213|00213|0)(?:[567]\d{8}|[1-4]\d{7,8})")
REGEX_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
DOMAINES_PLACEHOLDER = {"example.com", "example.org", "example.net", "test.com", "domain.com", "yourdomain.com"}


def classifier_email(email: str) -> int:
    """0 = domaine générique (gmail, yahoo...), 1 = domaine propre à l'établissement."""
    if not email or "@" not in email:
        return 0
    domaine = email.split("@")[-1].strip().lower()
    return 0 if domaine in DOMAINES_EMAIL_GENERIQUES else 1


def normaliser_telephone_dz(numero: str) -> str | None:
    """Convertit vers le format +213XXXXXXXXX, retourne None si non exploitable."""
    if not numero:
        return None
    chiffres = re.sub(r"[^\d+]", "", numero)
    if chiffres.startswith("+213"):
        reste = chiffres[4:]
    elif chiffres.startswith("00213"):
        reste = chiffres[5:]
    elif chiffres.startswith("0"):
        reste = chiffres[1:]
    else:
        reste = chiffres
    if len(reste) < 8 or len(reste) > 9:
        return None
    return "+213" + reste


def similarite_nom_domaine(nom_entreprise: str, url: str) -> int:
    """Score de confiance grossier (0-100) qu'une URL appartient bien à
    l'établissement. Regarde l'URL complète (domaine + chemin), pas
    seulement le domaine : les pages Facebook/LinkedIn et les fiches
    d'annuaire mettent le nom de l'établissement dans le chemin
    (ex. facebook.com/clinique.chifa.hydra), jamais dans le domaine."""
    if not url:
        return 0
    url_normalisee = url.lower().replace("-", " ").replace("_", " ").replace(".", " ").replace("/", " ")
    mots_nom = [m.lower() for m in re.split(r"[\s\-']+", nom_entreprise) if len(m) > 3]
    if not mots_nom:
        return 30  # nom trop court/générique pour juger, confiance neutre-basse

    correspondances = sum(1 for m in mots_nom if m in url_normalisee)
    return min(100, int((correspondances / len(mots_nom)) * 100))


def extraire_contacts_depuis_html(soup) -> dict:
    resultat = {"telephone": None, "email": None, "facebook": None, "linkedin": None}

    for lien in soup.find_all("a", href=True):
        href = lien["href"].strip()
        if href.lower().startswith("tel:") and not resultat["telephone"]:
            resultat["telephone"] = normaliser_telephone_dz(href[4:])
        elif href.lower().startswith("mailto:") and not resultat["email"]:
            email_candidat = href[7:].split("?")[0]
            if not _est_email_placeholder(email_candidat):
                resultat["email"] = email_candidat
        elif "facebook.com" in href and not resultat["facebook"]:
            resultat["facebook"] = href
        elif "linkedin.com" in href and not resultat["linkedin"]:
            resultat["linkedin"] = href

    texte = soup.get_text(" ")
    if not resultat["telephone"]:
        m = REGEX_TEL_DZ.search(texte)
        if m:
            resultat["telephone"] = normaliser_telephone_dz(m.group())
    if not resultat["email"]:
        m = REGEX_EMAIL.search(texte)
        if m and not _est_email_placeholder(m.group()):
            resultat["email"] = m.group()

    return resultat


def _est_email_placeholder(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domaine = email.split("@")[-1].strip().lower()
    return domaine in DOMAINES_PLACEHOLDER