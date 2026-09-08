import sqlite3
import getpass
from passlib.context import CryptContext

DB_PATH = "data/dasec_prospection.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

username = input("Nom d'utilisateur à modifier : ").strip()
nouveau_mdp = getpass.getpass("Nouveau mot de passe : ")
confirmation = getpass.getpass("Confirme le nouveau mot de passe : ")

if nouveau_mdp != confirmation:
    print("Les mots de passe ne correspondent pas.")
else:
    hashed = pwd_context.hash(nouveau_mdp)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET hashed_password = ? WHERE username = ?", (hashed, username))
    if cur.rowcount == 0:
        print(f"Aucun utilisateur '{username}' trouvé.")
    else:
        conn.commit()
        print(f"Mot de passe de '{username}' changé avec succès.")
    conn.close()