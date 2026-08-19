"""
ProfileAgent — visite les sources trouvées par DiscoveryAgent et complète la fiche.

Règle du projet : une règle Python déterministe passe toujours avant un appel LLM.
Pour les 4 champs qui demandent un jugement (effectif, qualité du site, réseau,
décideur), UN SEUL appel LLM combiné est fait par établissement (JSON structuré)
plutôt que 4 appels séparés.

Fix (contact décideur) : avant, la recherche s'arrêtait dès qu'un nom+fonction
étaient trouvés — aucune étape ne cherchait ensuite un moyen de contacter
CETTE personne précisément (LinkedIn personnel, email nominatif). Maintenant,
dès qu'un contact_nom est connu (peu importe la source), une étape dédiée
_enrichir_contact_personnel() cherche activement ces coordonnées.
"""

import json
import re
import unicodedata

import requests
from bs4 import BeautifulSoup

from config import MAX_ESSAIS_RESEAU
from models.schemas import Entreprise, DiscoverySources, ProfileData
from tools.llm_client import LLMClient
from tools.rules import classifier_email, extraire_contacts_depuis_html
from tools.rate_limiter import avec_retry
from tools.json_utils import nettoyer_json

PAGES_A_EXPLORER = ["", "contact", "contactez-nous", "contact-us", "a-propos", "about", "mentions-legales"]

PROMPT_SYSTEME = (
    "Tu analyses le contenu d'un site web d'établissement de santé algérien pour "
    "en extraire des informations factuelles. Réponds UNIQUEMENT en JSON valide, "
    "sans texte autour, avec exactement ces clés : effectif ('<10', '10-100', '>100' "
    "ou null si indéterminable), site_web_qualite (1=obsolète, 2=à jour), "
    "reseau_groupe (0 ou 1), reseau_nom (string ou null), contact_nom (string ou null), "
    "contact_fonction (string ou null, ex: 'Directeur', 'RSSI', 'DSI', 'Responsable achats'), "
    "contact_email_personnel (string ou null — UNIQUEMENT si un email au format nominatif "
    "type prenom.nom@domaine ou initiale.nom@domaine est explicitement associé au nom du "
    "décideur dans le texte ; ne JAMAIS y mettre un email générique comme contact@, info@, "
    "direction@ — dans ce cas laisse null), "
    "contact_telephone_personnel (string ou null — UNIQUEMENT une ligne directe explicitement "
    "associée au décideur, jamais le standard général de l'établissement)."
)

CONFIANCE_MINIMALE_WEBSITE = 60


def _normaliser_ascii(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return texte.lower()


def _extraire_email_nominatif(contexte: str, nom_decideur: str) -> str | None:
    """Règle déterministe (gratuite, avant tout recours au LLM) : ne retient
    un email que si sa partie locale contient un fragment significatif du nom
    du décideur — c'est ce qui distingue un email personnel d'un email
    générique d'entreprise repéré dans le même texte."""
    if not nom_decideur:
        return None
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", contexte)
    if not emails:
        return None

    fragments_nom = [
        f for f in _normaliser_ascii(nom_decideur).replace("-", " ").split()
        if len(f) >= 3
    ]
    if not fragments_nom:
        return None

    for email in emails:
        partie_locale = _normaliser_ascii(email.split("@")[0])
        if any(fragment in partie_locale for fragment in fragments_nom):
            return email
    return None

def _slug_correspond_au_nom(url_linkedin: str, nom_decideur: str) -> bool:
    """Un lien linkedin.com/in/<slug> n'est retenu que si le slug contient
    au moins un fragment significatif (≥3 lettres) du nom recherché —
    évite d'accepter le premier résultat LinkedIn de la liste sans lien
    réel avec la personne visée."""
    if not nom_decideur or not url_linkedin:
        return False
    slug = url_linkedin.rstrip("/").rsplit("/in/", 1)[-1]
    slug_normalise = _normaliser_ascii(slug).replace("-", " ")

    fragments_nom = [
        f for f in _normaliser_ascii(nom_decideur).replace("-", " ").split()
        if len(f) >= 3 and f not in ("dr", "mr", "mme")
    ]
    if not fragments_nom:
        return False

    return any(fragment in slug_normalise for fragment in fragments_nom)


class ProfileAgent:
    def __init__(self, llm_client: LLMClient, headers: dict, outil_recherche_gratuite,
             outil_recherche_payante, outil_recherche_tavily, budget_guard):
      
      self.llm_client = llm_client
      self.headers = headers
      self.outil_recherche_gratuite = outil_recherche_gratuite
      self.outil_recherche_payante = outil_recherche_payante
      self.outil_recherche_tavily = outil_recherche_tavily
      self.budget_guard = budget_guard

    def run(self, entreprise: Entreprise, sources: DiscoverySources) -> ProfileData:
        profil = ProfileData()
        contenu_pages = []

        confiance_website = sources.confidence.get("website", 0)
        if confiance_website >= CONFIANCE_MINIMALE_WEBSITE:
            contenu_pages = self._explorer_site(sources.website, profil)
        elif sources.facebook:
            contenu_pages = self._explorer_facebook(sources.facebook, profil)

        if entreprise.email or profil.email:
            profil.email_qualite = classifier_email(profil.email or entreprise.email)

        profil.site_web_qualite = 0 if not sources.website else profil.site_web_qualite

        if contenu_pages:
            self._enrichir_via_llm(entreprise, contenu_pages, profil)

        if not profil.contact_nom:
            self._rechercher_decideur(entreprise, profil)

        # Fix principal : dès qu'un nom est connu, on cherche activement à
        # le/la contacter — avant, cette étape n'existait tout simplement pas.
        if profil.contact_nom:
            self.enrichir_contact_personnel(entreprise, profil)

        if sources.annuaires:
            profil.annuaire_source = sources.annuaires[0]

        profil.sources_utilisees = {
            "website": sources.website,
            "facebook": sources.facebook,
            "linkedin": sources.linkedin,
        }
        print(f"email extrait par ProfileAgent : {profil.email!r}")
        print(f"décideur trouvé : {profil.contact_nom!r} ({profil.contact_fonction!r})")
        print(
            f"contact personnel : email={profil.contact_email_personnel!r} "
            f"tel={profil.contact_telephone_personnel!r} "
            f"linkedin={profil.contact_linkedin_personnel!r}"
        )
        return profil

    # ---------- extraction déterministe : site web ----------

    def _explorer_site(self, site_web: str, profil: ProfileData) -> list[str]:
        contenu_pages = []
        base = self._trouver_base_fonctionnelle(site_web)
        if not base:
            return contenu_pages

        for chemin in PAGES_A_EXPLORER:
            url_page = f"{base.rstrip('/')}/{chemin}".rstrip("/")
            reponse = self._recuperer_page(url_page)
            if reponse is None:
                continue

            contenu_pages.append(reponse.text[:4000])
            soup = BeautifulSoup(reponse.text, "html.parser")
            contacts = extraire_contacts_depuis_html(soup)
            for champ, valeur in contacts.items():
                if valeur and getattr(profil, champ, None) is None:
                    setattr(profil, champ, valeur)

            if profil.telephone and profil.email:
                break

        if base:
            profil.site_web_qualite = 2
        return contenu_pages

    @avec_retry(max_essais=MAX_ESSAIS_RESEAU, delai_base=2.0, exceptions=(requests.exceptions.RequestException,))
    def _recuperer_page(self, url: str):
        reponse = requests.get(url, headers=self.headers, timeout=12)
        return reponse if reponse.status_code == 200 else None

    def _trouver_base_fonctionnelle(self, url_originale: str) -> str | None:
        candidates = []
        url = url_originale if url_originale.startswith("http") else f"https://{url_originale}"
        hote_brut = url.split("://", 1)[-1].split("/", 1)[0]
        hote = hote_brut.replace("www.", "")
        for schema in ("https://", "http://"):
            candidates.append(f"{schema}{hote}")
            candidates.append(f"{schema}www.{hote}")

        vus = set()
        for candidate in candidates:
            if candidate in vus:
                continue
            vus.add(candidate)
            try:
                reponse = requests.get(candidate, headers=self.headers, timeout=10)
                if reponse.status_code == 200:
                    return candidate
            except requests.exceptions.RequestException:
                continue
        return None

    # ---------- extraction déterministe : Facebook (fallback) ----------

    def _explorer_facebook(self, url_facebook: str, profil: ProfileData) -> list[str]:
        reponse = self._recuperer_page(url_facebook)
        if reponse is None:
            return []
        soup = BeautifulSoup(reponse.text, "html.parser")
        contacts = extraire_contacts_depuis_html(soup)
        for champ, valeur in contacts.items():
            if valeur and getattr(profil, champ, None) is None:
                setattr(profil, champ, valeur)
        return [reponse.text[:4000]]

    # ---------- recherche dédiée : trouver LE NOM du décideur ----------

    def _rechercher_decideur(self, entreprise: Entreprise, profil: ProfileData):
        lieu = entreprise.commune_name or entreprise.wilaya_name or ""
        requetes = [
            f"DSI OR RSSI {entreprise.nom} {lieu} Algérie",
            f"directeur {entreprise.nom} {lieu} Algérie",
        ]
        for requete in requetes:
            observation = self.outil_recherche_gratuite.executer(requete)
            if not observation.resultats:
                continue
            contexte = "\n---\n".join(self._extraire_texte(r) for r in observation.resultats[:5])
            if not contexte.strip():
                continue
            self._enrichir_via_llm(entreprise, [contexte], profil)
            if profil.contact_nom:
                return

        if not profil.contact_nom:
            observation = self.outil_recherche_payante.executer(requetes[0])
            if observation.resultats:
                contexte = "\n---\n".join(self._extraire_texte(r) for r in observation.resultats[:5])
                if contexte.strip():
                    self._enrichir_via_llm(entreprise, [contexte], profil)

    # ---------- NOUVEAU : recherche dédiée à LA PERSONNE, une fois son nom connu ----------

    def enrichir_contact_personnel(self, entreprise: Entreprise, profil: ProfileData):
     """Cible la personne, pas l'entreprise — c'est le fix principal.
     Avant, aucune requête ne portait jamais sur le nom du décideur
     lui-même une fois trouvé."""
     requete_linkedin = f'"{profil.contact_nom}" {entreprise.nom} LinkedIn'
     print(f"[DEBUG] requête envoyée : {requete_linkedin}")

     observation = self.outil_recherche_gratuite.executer(requete_linkedin)  # DDG/Brave

     if not observation.resultats:
        print(f"  [fallback] {entreprise.nom} : DDG/Brave vide, tentative Tavily")
        observation = self.outil_recherche_tavily.executer(requete_linkedin)

     if not observation.resultats and self.budget_guard.restant > 0:
        print(f"  [fallback] {entreprise.nom} : Tavily vide, tentative Serper")
        observation = self.outil_recherche_payante.executer(requete_linkedin)

     contexte_combine = ""
     if observation.resultats:
        contexte_combine = "\n---\n".join(self._extraire_texte(r) for r in observation.resultats[:5])
        for r in observation.resultats:
         url = getattr(r, "url", "") or ""
         if "linkedin.com/in/" in url and _slug_correspond_au_nom(url, profil.contact_nom):
           profil.contact_linkedin_personnel = url
           break

     if not profil.contact_email_personnel and contexte_combine:
        email_trouve = _extraire_email_nominatif(contexte_combine, profil.contact_nom)
        if email_trouve:
            profil.contact_email_personnel = email_trouve

     if contexte_combine.strip():
        self._enrichir_via_llm(entreprise, [contexte_combine], profil)

    @staticmethod
    def _extraire_texte(resultat) -> str:
        return getattr(resultat, "extrait", "") or getattr(resultat, "description", "") or ""

    # ---------- jugement via LLM (un seul appel, JSON structuré) ----------

    def _enrichir_via_llm(self, entreprise: Entreprise, contenu_pages: list[str], profil: ProfileData):
        contexte = "\n---\n".join(contenu_pages)[:8000]
        prompt = (
            f"Établissement : {entreprise.nom} ({entreprise.sous_secteur}), "
            f"{entreprise.commune_name or entreprise.wilaya_name or ''}.\n\n"
            f"Contenu extrait :\n{contexte}"
        )

        try:
            reponse_brute = self.llm_client.complete(PROMPT_SYSTEME, prompt, max_tokens=350)
            donnees = json.loads(nettoyer_json(reponse_brute))
        except (json.JSONDecodeError, Exception):
            return

        if donnees.get("effectif") in ("<10", "10-100", ">100"):
            profil.effectif = donnees["effectif"]
        if donnees.get("site_web_qualite") in (1, 2):
            profil.site_web_qualite = donnees["site_web_qualite"]
        if donnees.get("reseau_groupe") in (0, 1):
            profil.reseau_groupe = donnees["reseau_groupe"]
        if donnees.get("reseau_nom"):
            profil.reseau_nom = donnees["reseau_nom"]
        # Ne jamais écraser un contact déjà trouvé par une réponse ultérieure
        # (ex: la recherche personnelle qui suit pourrait autrement remplacer
        # un nom fiable par un faux positif du contexte LinkedIn).
        if donnees.get("contact_nom") and not profil.contact_nom:
            profil.contact_nom = donnees["contact_nom"]
        if donnees.get("contact_fonction") and not profil.contact_fonction:
            profil.contact_fonction = donnees["contact_fonction"]
        if donnees.get("contact_email_personnel") and not profil.contact_email_personnel:
            profil.contact_email_personnel = donnees["contact_email_personnel"]
        if donnees.get("contact_telephone_personnel") and not profil.contact_telephone_personnel:
            profil.contact_telephone_personnel = donnees["contact_telephone_personnel"]