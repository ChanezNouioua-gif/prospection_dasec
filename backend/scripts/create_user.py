import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.security import hasher_mot_de_passe

DB_PATH = "data/prospection.db"  # adapte au vrai chemin


def creer_utilisateur(username: str, mot_de_passe: str, nom_complet: str = ""):
    connexion = sqlite3.connect(DB_PATH)
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            nom_complet TEXT,
            date_creation TEXT DEFAULT (datetime('now'))
        )
    """)
    connexion.execute(
        "INSERT INTO users (username, hashed_password, nom_complet) VALUES (?, ?, ?)",
        (username, hasher_mot_de_passe(mot_de_passe), nom_complet),
    )
    connexion.commit()
    connexion.close()
    print(f"Utilisateur '{username}' créé.")


if __name__ == "__main__":
    creer_utilisateur("karim", "chanez123", "Karim")