"""
Gestionnaire de connexion unique à SQLite.

Leçon tirée du notebook : les erreurs "database is locked" venaient toutes
du même problème — une fonction ouvrait sa propre connexion à l'intérieur
d'une boucle pendant qu'une autre connexion avait déjà des écritures en
attente sur le même fichier. Ici, une seule connexion est ouverte par
exécution du pipeline (context manager), et c'est la seule que DatabaseAgent
utilise. Aucun autre composant n'ouvre de connexion SQLite.
"""

import sqlite3
from contextlib import contextmanager


@contextmanager
def obtenir_connexion(db_path: str):
    connexion = sqlite3.connect(db_path, timeout=30)
    connexion.execute("PRAGMA journal_mode=WAL")
    connexion.execute("PRAGMA foreign_keys=ON")
    connexion.row_factory = sqlite3.Row
    try:
        yield connexion
    finally:
        connexion.close()
