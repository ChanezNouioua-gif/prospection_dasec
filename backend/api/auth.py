from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import sqlite3

from api.dependencies import get_connexion
from api.security import verifier_mot_de_passe, hasher_mot_de_passe, creer_token, decoder_token

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

class ChangerMotDePasseIn(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


@router.patch("/mot-de-passe")
def changer_mot_de_passe(
    body: ChangerMotDePasseIn,
    utilisateur: UserOut = Depends(get_current_user),
    connexion: sqlite3.Connection = Depends(get_connexion),
):
    row = connexion.execute(
        "SELECT * FROM users WHERE username = ?", (utilisateur.username,)
    ).fetchone()

    if not verifier_mot_de_passe(body.ancien_mot_de_passe, row["hashed_password"]):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
    if len(body.nouveau_mot_de_passe) < 8:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit faire au moins 8 caractères")

    nouveau_hash = hasher_mot_de_passe(body.nouveau_mot_de_passe)
    connexion.execute(
        "UPDATE users SET hashed_password = ? WHERE username = ?",
        (nouveau_hash, utilisateur.username),
    )
    connexion.commit()
    return {"message": "Mot de passe modifié"}


@router.get("/equipe")
def lister_equipe(
    utilisateur: UserOut = Depends(get_current_user),
    connexion: sqlite3.Connection = Depends(get_connexion),
):
    cursor = connexion.execute("SELECT username, nom_complet FROM users ORDER BY username")
    return [dict(row) for row in cursor.fetchall()]


class PreferencesIn(BaseModel):
    notifications_actives: bool


@router.get("/preferences")
def obtenir_preferences(
    utilisateur: UserOut = Depends(get_current_user),
    connexion: sqlite3.Connection = Depends(get_connexion),
):
    row = connexion.execute(
        "SELECT notifications_actives FROM users WHERE username = ?", (utilisateur.username,)
    ).fetchone()
    return {"notifications_actives": bool(row["notifications_actives"])}


@router.patch("/preferences")
def maj_preferences(
    body: PreferencesIn,
    utilisateur: UserOut = Depends(get_current_user),
    connexion: sqlite3.Connection = Depends(get_connexion),
):
    connexion.execute(
        "UPDATE users SET notifications_actives = ? WHERE username = ?",
        (int(body.notifications_actives), utilisateur.username),
    )
    connexion.commit()
    return {"ok": True}