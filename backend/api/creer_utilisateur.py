import sqlite3
import getpass
from passlib.context import CryptContext

DB_PATH = "data/dasec_prospection.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

username = input("Nom d'utilisateur : ").strip()
password = getpass.getpass("Mot de passe : ")

hashed_password = pwd_context.hash(password)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("""
    INSERT INTO users (username, hashed_password)
    VALUES (?, ?)
    """, (username, hashed_password))
    conn.commit()
    print(f"Utilisateur '{username}' créé avec succès.")
except sqlite3.IntegrityError:
    print(f"Erreur : le nom d'utilisateur '{username}' existe déjà.")

conn.close()