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
    (jitter, backoff exponentiel, conditions par type d'erreur...)."""
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
    plutôt que de continuer à dépenser silencieusement au-delà du plafond configuré."""
    def __init__(self, plafond_appels: int):
        self.plafond_appels = plafond_appels
        self.appels_effectues = 0

    def consommer(self, n: int = 1):
        if self.appels_effectues + n > self.plafond_appels:
            raise RuntimeError(
                f"Plafond budget atteint : {self.appels_effectues}/{self.plafond_appels} "
                f"appels payants déjà utilisés sur ce run."
            )
        self.appels_effectues += n

    @property
    def restant(self) -> int:
        return self.plafond_appels - self.appels_effectues
