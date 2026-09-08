from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sqlite3

from pydantic import BaseModel

from api.dependencies import get_connexion, get_repository
from api.schemas import ProspectOut
from database.repository import EntrepriseRepository

app = FastAPI(title="ProspectionAI API")

from api.auth import router as auth_router, get_current_user, UserOut
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/prospects/{prospect_id}", response_model=ProspectOut)
def detail_prospect(
    prospect_id: int,
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    repo = EntrepriseRepository(connexion)
    prospect = repo.get_par_id(prospect_id)
    if prospect is None:
        raise HTTPException(status_code=404, detail="Prospect introuvable")
    return prospect


@app.get("/stats")
def stats(
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    cursor = connexion.execute("""
        SELECT secteur, COUNT(*) as total, AVG(score_dasec) as score_moyen
        FROM entreprises
        GROUP BY secteur
    """)
    return [dict(row) for row in cursor.fetchall()]


@app.get("/prospects")
def lister_prospects(
    wilaya: Optional[str] = None,
    commune: Optional[str] = None,
    secteur: Optional[str] = None,
    sous_secteur: Optional[str] = None,
    score_min: Optional[float] = None,
    statut: Optional[str] = None,
    dans_crm: Optional[int] = None,
    page: int = Query(1, ge=1),
    limite: int = Query(10, le=200),
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    conditions = []
    params: list = []

    if wilaya:
        conditions.append("wilaya_name = ?")
        params.append(wilaya)
    if commune:
        conditions.append("commune_brute = ?")
        params.append(commune)
    if secteur:
        conditions.append("secteur = ?")
        params.append(secteur)
    if sous_secteur:
        conditions.append("sous_secteur = ?")
        params.append(sous_secteur)
    if score_min is not None:
        conditions.append("score_dasec >= ?")
        params.append(score_min)
    if statut:
        conditions.append("statut = ?")
        params.append(statut)
    if dans_crm is not None:
        conditions.append("dans_crm = ?")
        params.append(dans_crm)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = connexion.execute(f"SELECT COUNT(*) FROM entreprises {where}", params).fetchone()[0]
    rows = connexion.execute(
        f"SELECT * FROM entreprises {where} ORDER BY score_dasec DESC LIMIT ? OFFSET ?",
        params + [limite, (page - 1) * limite],
    ).fetchall()

    return {"items": [dict(r) for r in rows], "total": total, "page": page}


@app.get("/filtres")
def obtenir_filtres(
    wilaya: Optional[str] = None,
    secteur: Optional[str] = None,
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    wilayas = [r[0] for r in connexion.execute(
        "SELECT DISTINCT wilaya_name FROM entreprises WHERE wilaya_name IS NOT NULL ORDER BY wilaya_name"
    ).fetchall()]

    secteurs = [r[0] for r in connexion.execute(
        "SELECT DISTINCT secteur FROM entreprises WHERE secteur IS NOT NULL ORDER BY secteur"
    ).fetchall()]

    cond_communes, params_communes = "WHERE commune_brute IS NOT NULL", []
    if wilaya:
        cond_communes += " AND wilaya_name = ?"
        params_communes.append(wilaya)
    communes = [r[0] for r in connexion.execute(
        f"SELECT DISTINCT commune_brute FROM entreprises {cond_communes} ORDER BY commune_brute", params_communes
    ).fetchall()]

    cond_ss, params_ss = "WHERE sous_secteur IS NOT NULL", []
    if secteur:
        cond_ss += " AND secteur = ?"
        params_ss.append(secteur)
    sous_secteurs = [r[0] for r in connexion.execute(
        f"SELECT DISTINCT sous_secteur FROM entreprises {cond_ss} ORDER BY sous_secteur", params_ss
    ).fetchall()]

    return {"wilayas": wilayas, "secteurs": secteurs, "communes": communes, "sous_secteurs": sous_secteurs}


STATUTS_PIPELINE = ["NOUVEAU", "A_CONTACTER", "CONTACTE", "ECHANGE", "RDV", "PROPOSITION", "GAGNE", "PERDU"]

@app.post("/prospects/{prospect_id}/crm")
def ajouter_au_crm(
    prospect_id: int,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    repo.ajouter_au_crm(prospect_id)
    return {"ok": True}

@app.patch("/prospects/{prospect_id}/statut")
def changer_statut(
    prospect_id: int,
    statut: str,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    if statut not in STATUTS_PIPELINE:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs acceptées : {STATUTS_PIPELINE}")
    repo.maj_statut_crm(prospect_id, statut)
    return {"ok": True}

@app.get("/crm/resume")
def resume_crm(
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    pipeline = {s: 0 for s in STATUTS_PIPELINE}
    for ligne in repo.resume_pipeline():
        pipeline[ligne["statut"]] = ligne["n"]
    total = sum(pipeline.values())

    taches_brutes = repo.taches_du_jour()
    aujourdhui = __import__("datetime").date.today().isoformat()
    taches = [{
        "id": t["id"],
        "prospect_id": t["id"],
        "prospect_nom": t["nom"],
        "type": "relance",
        "description": t["prochaine_action"] or "Relance prévue",
        "date_echeance": t["prochaine_action_date"],
        "en_retard": t["prochaine_action_date"] < aujourdhui,
        "fait": False,
    } for t in taches_brutes]

    activites_brutes = repo.get_interactions_recentes(10)
    activites = [{
        "id": a["id"],
        "prospect_id": a["entreprise_id"],
        "prospect_nom": a["entreprise_nom"],
        "type": a["type"] if a["type"] in ("appel", "email", "rdv", "note", "statut", "relance") else "note",
        "description": a["contenu"],
        "date": a["date"],
        "auteur": "Hanane",
    } for a in activites_brutes]

    perdus_bruts = repo.prospects_perdus_recents(5)
    perdus = [{
        "id": p["id"], "nom": p["nom"],
        "motif": p["motif_perte"], "date": p["date_mise_a_jour"],
    } for p in perdus_bruts]

    return {
        "pipeline": [{"statut": s, "total": n} for s, n in pipeline.items()],
        "total_crm": total,
        "opportunites": repo.top_opportunites(10),
        "jamais_contactes": repo.prospects_jamais_contactes(),
        "ajoutes_ce_mois": repo.ajoutes_ce_mois(),
        "taches_du_jour": taches,
        "taches_en_retard": sum(1 for t in taches if t["en_retard"]),
        "prospects_sans_action": repo.prospects_sans_prochaine_action(),
        "activites_recentes": activites,
        "perdus_recents": perdus,
        "equipe": [],
    }


@app.get("/crm/historique")
def historique_crm(
    q: Optional[str] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limite: int = Query(25, ge=1, le=100),
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    interactions, total = repo.get_historique_interactions(q, type, page, limite)
    types_valides = {"appel", "email", "rdv", "note", "statut", "relance"}
    return {
        "items": [
            {
                **interaction,
                "type": interaction["type"] if interaction["type"] in types_valides else "note",
                "auteur": "Hanane",
            }
            for interaction in interactions
        ],
        "total": total,
        "page": page,
    }

class MotifPerteIn(BaseModel):
    motif: str

@app.patch("/crm/taches/{prospect_id}/complete")
def completer_tache(
    prospect_id: int,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    repo.completer_tache(prospect_id)
    return {"ok": True}

@app.patch("/prospects/{prospect_id}/perdu")
def marquer_perdu(
    prospect_id: int,
    body: MotifPerteIn,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    repo.marquer_perdu(prospect_id, body.motif)
    return {"ok": True}


class ProchaineActionIn(BaseModel):
    texte: str
    date: str

@app.patch("/prospects/{prospect_id}/prochaine-action")
def changer_prochaine_action(
    prospect_id: int,
    body: ProchaineActionIn,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    repo.maj_prochaine_action(prospect_id, body.texte, body.date)
    return {"ok": True}


class NoteIn(BaseModel):
    contenu: str
    type: str = "note"

@app.post("/prospects/{prospect_id}/notes")
def ajouter_note(
    prospect_id: int,
    body: NoteIn,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    type_valide = body.type if body.type in ("appel", "email", "rdv", "note") else "note"
    repo.ajouter_interaction(prospect_id, type_valide, body.contenu)
    return {"ok": True}

@app.get("/prospects/{prospect_id}/interactions")
def lister_interactions(
    prospect_id: int,
    repo: EntrepriseRepository = Depends(get_repository),
    utilisateur: UserOut = Depends(get_current_user),
):
    return repo.get_interactions(prospect_id)


import json

def calculer_confiance_contact(row: dict) -> dict:
    if not row.get("contact_nom"):
        return {"label": "Aucun contact", "score": 0, "raisons": []}

    raisons = []
    points = 0

    raisons.append({"label": "Identité trouvée", "ok": True})
    points += 25

    if row.get("contact_fonction"):
        raisons.append({"label": "Fonction renseignée", "ok": True})
        points += 15
    else:
        raisons.append({"label": "Fonction renseignée", "ok": False})

    try:
        confiance_sources = json.loads(row.get("sources_confidence") or "{}")
    except (json.JSONDecodeError, TypeError):
        confiance_sources = {}

    linkedin_ok = confiance_sources.get("linkedin", 0) >= 70
    site_ok = confiance_sources.get("website", 0) >= 70

    if linkedin_ok:
        raisons.append({"label": "Source LinkedIn fiable", "ok": True})
        points += 30
    elif site_ok:
        raisons.append({"label": "Source site officiel fiable", "ok": True})
        points += 20
    else:
        raisons.append({"label": "Source fiable identifiée", "ok": False})

    if row.get("contact_email_personnel"):
        raisons.append({"label": "Email personnel du décideur trouvé", "ok": True})
        points += 30
    elif row.get("email") and row.get("email_qualite") == 1:
        raisons.append({"label": "Email professionnel vérifié (générique)", "ok": True})
        points += 15
    elif row.get("email"):
        raisons.append({"label": "Email trouvé (générique)", "ok": False})
        points += 5
    else:
        raisons.append({"label": "Email professionnel vérifié", "ok": False})

    if row.get("contact_linkedin_personnel"):
        raisons.append({"label": "Profil LinkedIn personnel trouvé", "ok": True})
        points += 15

    label = "Élevée" if points >= 70 else "Moyenne" if points >= 40 else "Faible"
    return {"label": label, "score": points, "raisons": raisons}


@app.get("/decideurs")
def lister_decideurs(
    wilaya: Optional[str] = None,
    secteur: Optional[str] = None,
    confiance: Optional[str] = None,
    avec_contact_uniquement: bool = True,
    page: int = Query(1, ge=1),
    limite: int = Query(20, le=200),
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    conditions = []
    params: list = []
    if avec_contact_uniquement:
        conditions.append("contact_nom IS NOT NULL")
        conditions.append(
            "(contact_email_personnel IS NOT NULL OR contact_telephone_personnel IS NOT NULL "
            "OR contact_linkedin_personnel IS NOT NULL)"
        )
    if wilaya:
        conditions.append("wilaya_name = ?")
        params.append(wilaya)
    if secteur:
        conditions.append("secteur = ?")
        params.append(secteur)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = connexion.execute(f"SELECT * FROM entreprises {where}", params).fetchall()
    resultats = []
    for row in rows:
        d = dict(row)
        conf = calculer_confiance_contact(d)
        if confiance and conf["label"] != confiance:
            continue
        resultats.append({**d, "confiance": conf})

    total = len(resultats)
    debut = (page - 1) * limite
    return {"items": resultats[debut:debut + limite], "total": total, "page": page}


@app.get("/decideurs/resume")
def resume_decideurs(
    connexion: sqlite3.Connection = Depends(get_connexion),
    utilisateur: UserOut = Depends(get_current_user),
):
    rows = connexion.execute("SELECT * FROM entreprises").fetchall()
    total = len(rows)
    trouves = 0
    a_verifier = 0
    for row in rows:
        conf = calculer_confiance_contact(dict(row))
        if conf["label"] != "Aucun contact":
            trouves += 1
        if conf["label"] in ("Moyenne", "Faible"):
            a_verifier += 1
    return {
        "analyses": total,
        "decideurs_trouves": trouves,
        "a_verifier": a_verifier,
        "a_retraiter": None,
    }
