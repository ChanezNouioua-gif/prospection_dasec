"""
Limitation de débit + retry.

Leçon tirée du notebook : le code de retry a été réécrit à la main 3-4 fois
(Overpass, Nominatim, scraping) avec des variations légères à chaque fois.
Ici, un seul décorateur générique, testé une fois, utilisé partout.
"""

import time
import functools
from collections.abc import Callable


def avec_delai(delai_secondes: float):
    """Ajoute un délai fixe après l'exécution de la fonction décorée —
    utile pour respecter les politiques de débit d'une API externe."""
    def decorateur(fonction: Callable):
        @functools.wraps(fonction)
        def wrapper(*args, **kwargs):
            resultat = fonction(*args, **kwargs)
            time.sleep(delai_secondes)
            return resultat
        return wrapper
    return decorateur


def avec_retry(max_essais: int = 3, delai_base: float = 3.0, exceptions=(Exception,)):
    """Retry avec backoff linéaire simple (delai_base * numero_essai).
    Volontairement plus simple qu'une lib comme tenacity pour rester lisible,
    mais peut être remplacé par tenacity si les besoins de retry se complexifient
    (jitter, backoff exponentiel, conditions par type d'erreur...).

    IMPORTANT : `exceptions` doit rester restreint aux erreurs réellement
    transitoires (réseau, timeout...). Une erreur permanente (quota API
    épuisé, clé invalide) ne doit PAS passer par ce tuple — sinon elle est
    retentée `max_essais` fois pour rien, à chaque appel, sur chaque
    établissement traité dans le run."""
    def decorateur(fonction: Callable):
        @functools.wraps(fonction)
        def wrapper(*args, **kwargs):
            derniere_erreur = None
            for essai in range(1, max_essais + 1):
                try:
                    return fonction(*args, **kwargs)
                except exceptions as e:
                    derniere_erreur = e
                    if essai < max_essais:
                        time.sleep(delai_base * essai)
            raise derniere_erreur
        return wrapper
    return decorateur


class BudgetGuard:
    """Garde-fou budgétaire pour les appels payants (Serper). Lève une exception
    plutôt que de continuer à dépenser silencieusement au-delà du plafond configuré.

    PATCH (quota Serper épuisé) : ce plafond (`plafond_appels`) est purement
    local au run — il ne reflète PAS le solde réel du compte Serper. Avant ce
    patch, quand le compte réel était à sec (erreur 400 "Not enough credits"),
    ce garde-fou local restait à moitié plein et laissait le pipeline retenter
    Serper sur chaque établissement suivant, pour échouer à chaque fois.
    `epuiser_definitivement()` permet au code appelant (RecherchePayanteTool)
    de signaler explicitement "le fournisseur lui-même n'a plus de crédits",
    ce qui fait immédiatement tomber `restant` à 0 pour le reste du run —
    DiscoveryAgent._doit_forcer_payant() s'arrête alors de lui-même, sans
    changement nécessaire côté DiscoveryAgent."""

    def __init__(self, plafond_appels: int):
        self.plafond_appels = plafond_appels
        self.appels_effectues = 0
        self.quota_fournisseur_epuise = False

    def consommer(self, n: int = 1):
        if self.appels_effectues + n > self.plafond_appels:
            raise RuntimeError(
                f"Plafond budget atteint : {self.appels_effectues}/{self.plafond_appels} "
                f"appels payants déjà utilisés sur ce run."
            )
        self.appels_effectues += n

    def epuiser_definitivement(self):
        """PATCH : à appeler quand le fournisseur confirme lui-même que le
        quota réel est épuisé (pas juste notre plafond local). Rend `restant`
        nul immédiatement, pour le reste du run entier — plus aucun
        établissement suivant ne retentera Serper inutilement."""
        self.quota_fournisseur_epuise = True
        self.appels_effectues = self.plafond_appels

    @property
    def restant(self) -> int:
        if self.quota_fournisseur_epuise:
            return 0
        return self.plafond_appels - self.appels_effectues