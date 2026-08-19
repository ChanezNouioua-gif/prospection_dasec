from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import sqlite3

from api.dependencies import get_connexion
from api.security import verifier_mot_de_passe, creer_token, decoder_token

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "session_token"


class UserOut(BaseModel):
    username: str
    nom_complet: str | None = None


@router.post("/login")
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    connexion: sqlite3.Connection = Depends(get_connexion),
):
    cursor = connexion.execute(
        "SELECT * FROM users WHERE username = ?", (form.username,)
    )
    utilisateur = cursor.fetchone()

    if utilisateur is None or not verifier_mot_de_passe(
        form.password, utilisateur["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )

    token = creer_token({"sub": utilisateur["username"]})

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,       # inaccessible en JavaScript, bloque le vol via XSS
        secure=False,        # True en production (HTTPS obligatoire pour ça)
        samesite="lax",      # protège contre le CSRF cross-site
        max_age=60 * 60 * 8, # 8h, cohérent avec l'expiration du JWT
        path="/",
    )
    return {"message": "Connecté", "username": utilisateur["username"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Déconnecté"}


def get_current_user(
    request: Request,
    connexion: sqlite3.Connection = Depends(get_connexion),
) -> UserOut:
    token = request.cookies.get(COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=401, detail="Non authentifié")

    donnees = decoder_token(token)
    if donnees is None:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")

    cursor = connexion.execute(
        "SELECT * FROM users WHERE username = ?", (donnees["sub"],)
    )
    utilisateur = cursor.fetchone()
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    return UserOut(username=utilisateur["username"], nom_complet=utilisateur["nom_complet"])


@router.get("/me", response_model=UserOut)
def me(utilisateur: UserOut = Depends(get_current_user)):
    return utilisateur