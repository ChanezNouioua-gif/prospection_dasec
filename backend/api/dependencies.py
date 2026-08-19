import sqlite3
from fastapi import Depends
from database.repository import EntrepriseRepository

DB_PATH = "data/dasec_prospection.db"

def get_connexion():
    connexion = sqlite3.connect(DB_PATH, check_same_thread=False)
    connexion.row_factory = sqlite3.Row
    try:
        yield connexion
    finally:
        connexion.close()

def get_repository(connexion=Depends(get_connexion)):
    return EntrepriseRepository(connexion)