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

PATCH (faux positifs contact générique) : le filtre sur l'email nominatif
existait déjà (_extraire_email_nominatif), mais RIEN n'empêchait le LLM de
renvoyer le standard téléphonique général de l'entreprise comme
"contact_telephone_personnel", ni de renvoyer un email générique via le
chemin LLM (le filtre déterministe ne protégeait que le chemin regex).
Résultat observé : l'enrichissement "personnel" ramenait en réalité les
coordonnées de l'entreprise, pas celles du décideur. On ajoute donc :
  1. le contact générique déjà connu (entreprise.* ou profil.* extrait du
     site) est passé au LLM dans le prompt, avec consigne explicite de
     renvoyer null si ça correspond ;
  2. un filet de sécurité déterministe APRÈS le LLM (et après le chemin
     regex) qui rejette toute valeur strictement identique au contact
     générique connu, quelle que soit sa provenance.

PATCH (pollution croisée sur contact_nom) : _rechercher_decideur n'avait
aucune vérification que le nom trouvé appartient réellement à l'entreprise
recherchée — une requête large ("DSI OR RSSI {nom} {lieu} Algérie") pouvait
faire remonter n'importe quelle personnalité visible en ligne. Audit sur la
base réelle : un même nom ("Djallal Bouabdallah") trouvé sur 22 entreprises
de 7 secteurs différents. Fix à deux niveaux, tous deux déterministes/gratuits
en amont du LLM :
  1. _contexte_mentionne_entreprise : n'envoie au LLM que les contextes de
     recherche qui mentionnent réellement un fragment spécifique du nom de
     l'entreprise (pas juste les mots-clés de la requête) ;
  2. PROMPT_SUFFIXE_LIEN_ENTREPRISE : quand le contexte vient d'une recherche
     web large (pas d'un site officiel), rappelle explicitement au LLM de ne
     pas extraire de nom en cas de doute sur le rattachement à CETTE entreprise.
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

# PATCH (pollution croisée) : suffixe ajouté quand le contexte vient d'une
# recherche web large (pas d'un site officiel) — rappelle explicitement au
# LLM de vérifier le lien avant d'extraire un nom, en plus du filtre
# déterministe en amont (_contexte_mentionne_entreprise), qui ne garantit
# que la présence du nom dans le texte, pas que la personne y est vraiment
# rattachée en tant que décideur DE cette entreprise précise.
PROMPT_SUFFIXE_LIEN_ENTREPRISE = (
    "\n\nATTENTION : ce texte vient d'une recherche web large et peut mentionner "
    "plusieurs personnes/entités différentes. N'extrais contact_nom QUE si le "
    "texte indique explicitement que cette personne est décideur/responsable "
    "DE L'ÉTABLISSEMENT CI-DESSUS précisément (pas d'une autre entreprise, "
    "administration ou organisme mentionné dans le même texte). En cas de doute, "
    "laisse contact_nom à null plutôt que de deviner."
)

# PATCH : suffixe ajouté au prompt uniquement quand on connaît déjà le contact
# générique de l'entreprise (utilisé par enrichir_contact_personnel).
PROMPT_SUFFIXE_CONTACT_CONNU = (
    "\n\nATTENTION : le contact générique déjà connu de cet établissement est "
    "téléphone={telephone!r}, email={email!r}. Si le numéro ou l'email que tu "
    "identifies dans le texte est identique (ou une simple variante de mise en "
    "forme) à l'un de ceux-ci, c'est le standard général de l'entreprise, PAS "
    "une coordonnée personnelle du décideur : renvoie null pour ce champ."
)

CONFIANCE_MINIMALE_WEBSITE = 60


def _normaliser_ascii(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return texte.lower()


def _normaliser_telephone(tel: str) -> str:
    """Ne garde que les chiffres, pour comparer deux numéros écrits
    différemment (espaces, +213, 0 initial, tirets...)."""
    return re.sub(r"\D", "", tel or "")


def _correspond_au_contact_generique(valeur: str, generique: str, est_telephone: bool = False) -> bool:
    """PATCH : vrai si `valeur` (censée être personnelle) est en réalité
    identique au contact générique déjà connu de l'entreprise. Sert de
    filet de sécurité déterministe, appliqué après le LLM ET après le
    filtre regex, quelle que soit la voie par laquelle la valeur est arrivée."""
    if not valeur or not generique:
        return False
    if est_telephone:
        num_valeur = _normaliser_telephone(valeur)
        num_generique = _normaliser_telephone(generique)
        if not num_valeur or not num_generique:
            return False
        # compare sur les 8 derniers chiffres pour absorber les indicatifs
        # (+213 vs 0, avec ou sans code wilaya)
        return num_valeur[-8:] == num_generique[-8:]
    return valeur.strip().lower() == generique.strip().lower()


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

# PATCH (pollution croisée) : mots trop génériques dans un nom d'entreprise
# pour servir de fragment discriminant (secteur, mentions administratives...).
MOTS_GENERIQUES_ENTREPRISE = {
    "cabinet", "clinique", "pharmacie", "medical", "dentaire", "assurance",
    "mairie", "notaire", "avocat", "hopital", "laboratoire", "analyses",
    "opticien", "sans", "nom", "prive", "privee", "medecin", "docteur",
}


def _contexte_mentionne_entreprise(contexte: str, nom_entreprise: str) -> bool:
    """PATCH (pollution croisée) : filtre déterministe et gratuit, appliqué
    AVANT tout appel LLM. La requête envoyée au moteur de recherche contient
    déjà le nom de l'entreprise, mais le moteur (DDG/Brave gratuits surtout)
    peut renvoyer des résultats qui ne le mentionnent pas du tout — juste des
    pages qui matchent "RSSI"/"DSI"/"directeur" + "Algérie". C'est exactement
    ce qui a produit les faux positifs identifiés (ex: Djallal Bouabdallah,
    remonté sur 22 entreprises sans rapport). On n'accepte donc le contexte
    comme source valide que s'il contient un fragment réellement spécifique
    du nom de l'entreprise — pas un mot-clé sectoriel générique."""
    fragments = [
        f for f in _normaliser_ascii(nom_entreprise).replace("-", " ").split()
        if len(f) >= 4 and f not in MOTS_GENERIQUES_ENTREPRISE
    ]
    if not fragments:
        # Nom trop court/générique pour filtrer sans risque de tout rejeter
        # à tort (ex: "2A", "APC") — dans ce cas on laisse passer, le Critic
        # humain reste le seul filet pour ces cas-là.
        return True
    contexte_normalise = _normaliser_ascii(contexte)
    return any(fragment in contexte_normalise for fragment in fragments)


def _slug_correspond_au_nom(url_linkedin: str, nom_decideur: str) -> bool:
    """Un lien linkedin.com/in/<slug> n'est retenu que si le slug contient
    soit deux fragments du nom (prénom+nom), soit un seul fragment mais
    assez long (≥5 lettres) — évite les faux positifs sur un prénom seul
    ou un nom de famille court/générique."""
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

    matches = [f for f in fragments_nom if f in slug_normalise]
    if len(fragments_nom) >= 2:
        return len(matches) >= 2
    return len(matches) >= 1 and len(fragments_nom[0]) >= 5


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
        """PATCH (pollution croisée) : avant d'envoyer un contexte au LLM,
        on vérifie qu'il mentionne réellement l'entreprise recherchée
        (_contexte_mentionne_entreprise). Sans ce filtre, une requête large
        type "DSI OR RSSI {nom} {lieu} Algérie" peut faire remonter une
        personnalité visible en ligne sans aucun rapport avec l'entreprise
        (cf. audit : Djallal Bouabdallah trouvé sur 22 entreprises)."""
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
            if not _contexte_mentionne_entreprise(contexte, entreprise.nom):
                print(f"  [rejet] {entreprise.nom} : résultats sans lien apparent avec l'entreprise, ignorés")
                continue
            self._enrichir_via_llm(entreprise, [contexte], profil, exiger_lien_entreprise=True)
            if profil.contact_nom:
                return

        if not profil.contact_nom:
            observation = self.outil_recherche_payante.executer(requetes[0])
            if observation.resultats:
                contexte = "\n---\n".join(self._extraire_texte(r) for r in observation.resultats[:5])
                if contexte.strip() and _contexte_mentionne_entreprise(contexte, entreprise.nom):
                    self._enrichir_via_llm(entreprise, [contexte], profil, exiger_lien_entreprise=True)
                elif contexte.strip():
                    print(f"  [rejet] {entreprise.nom} : résultats payants sans lien apparent, ignorés")

    # ---------- recherche dédiée à LA PERSONNE, une fois son nom connu ----------

    def enrichir_contact_personnel(self, entreprise: Entreprise, profil: ProfileData):
     """Cible la personne, pas l'entreprise — c'est le fix principal.
     Avant, aucune requête ne portait jamais sur le nom du décideur
     lui-même une fois trouvé.

     PATCH : on connaît potentiellement déjà le contact générique de
     l'entreprise (entreprise.telephone/.email, ou profil.telephone/.email
     extraits plus tôt via _explorer_site). On le passe au LLM pour qu'il
     évite de le reprendre, ET on le revérifie après coup en dur — sinon
     un contexte de recherche pauvre (juste une fiche Pages Jaunes avec le
     standard général) pousse le LLM à recracher ce numéro comme s'il
     était "personnel"."""
     contact_tel_connu = getattr(entreprise, "telephone", None) or profil.telephone
     contact_email_connu = getattr(entreprise, "email", None) or profil.email

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
        # PATCH : même passé le filtre regex (fragment du nom dans la partie
        # locale), on revérifie que ce n'est pas quand même l'email générique.
        if email_trouve and not _correspond_au_contact_generique(email_trouve, contact_email_connu):
            profil.contact_email_personnel = email_trouve

     if contexte_combine.strip():
        self._enrichir_via_llm(
            entreprise, [contexte_combine], profil,
            contact_generique=(contact_tel_connu, contact_email_connu),
        )

     # PATCH : filet de sécurité final, quelle que soit la voie d'entrée
     # (regex ci-dessus ou LLM dans _enrichir_via_llm).
     if _correspond_au_contact_generique(profil.contact_telephone_personnel, contact_tel_connu, est_telephone=True):
        print(f"  [rejet] {entreprise.nom} : téléphone 'personnel' == standard général, ignoré")
        profil.contact_telephone_personnel = None

     if _correspond_au_contact_generique(profil.contact_email_personnel, contact_email_connu):
        print(f"  [rejet] {entreprise.nom} : email 'personnel' == contact générique, ignoré")
        profil.contact_email_personnel = None

    @staticmethod
    def _extraire_texte(resultat) -> str:
        return getattr(resultat, "extrait", "") or getattr(resultat, "description", "") or ""

    # ---------- jugement via LLM (un seul appel, JSON structuré) ----------

    def _enrichir_via_llm(self, entreprise: Entreprise, contenu_pages: list[str], profil: ProfileData,
                           contact_generique: tuple[str | None, str | None] | None = None,
                           exiger_lien_entreprise: bool = False):
        contexte = "\n---\n".join(contenu_pages)[:8000]
        prompt = (
            f"Établissement : {entreprise.nom} ({entreprise.sous_secteur}), "
            f"{entreprise.commune_name or entreprise.wilaya_name or ''}.\n\n"
            f"Contenu extrait :\n{contexte}"
        )

        # PATCH : quand on connaît déjà le contact générique (cas de
        # enrichir_contact_personnel), on le donne explicitement au LLM.
        if contact_generique and any(contact_generique):
            telephone_connu, email_connu = contact_generique
            prompt += PROMPT_SUFFIXE_CONTACT_CONNU.format(telephone=telephone_connu, email=email_connu)

        # PATCH (pollution croisée) : renforce la consigne quand le contexte
        # vient d'une recherche web large (_rechercher_decideur), où le
        # risque de mélanger plusieurs entités est le plus élevé.
        if exiger_lien_entreprise:
            prompt += PROMPT_SUFFIXE_LIEN_ENTREPRISE

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