# reset_password.py
import sqlite3
from passlib.context import CryptContext

DB_PATH = "data/dasec_prospection.db"
USERNAME = "karim"          # <-- mets le username exact trouvé à l'étape 1
NOUVEAU_MOT_DE_PASSE = "dasec_is_the_best!"  # <-- choisis un mot de passe temporaire

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
nouveau_hash = pwd_context.hash(NOUVEAU_MOT_DE_PASSE)

connexion = sqlite3.connect(DB_PATH)
cursor = connexion.execute(
    "UPDATE users SET hashed_password = ? WHERE username = ?",
    (nouveau_hash, USERNAME),
)
connexion.commit()

if cursor.rowcount == 0:
    print(f"Aucun utilisateur '{USERNAME}' trouvé — rien n'a été modifié.")
else:
    print(f"Mot de passe de '{USERNAME}' réinitialisé avec succès.")

connexion.close()