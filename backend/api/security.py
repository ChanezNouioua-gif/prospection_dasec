from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60 * 8  # 8h de session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hasher_mot_de_passe(mot_de_passe: str) -> str:
    return pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    return pwd_context.verify(mot_de_passe, hash_stocke)


def creer_token(donnees: dict) -> str:
    a_encoder = donnees.copy()
    expiration = datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_MINUTES)
    a_encoder["exp"] = expiration
    return jwt.encode(a_encoder, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None