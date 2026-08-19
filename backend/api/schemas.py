from pydantic import BaseModel
from typing import Optional

class ProspectOut(BaseModel):
    id: int
    nom: str
    secteur: str
    sous_secteur: Optional[str] = None
    wilaya_name: Optional[str] = None
    commune_brute: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    google_business: Optional[str] = None
    pages_jaunes: Optional[str] = None
    effectif: Optional[str] = None
    reseau_groupe: Optional[int] = None
    reseau_nom: Optional[str] = None
    contact_nom: Optional[str] = None
    contact_fonction: Optional[str] = None
    statut: Optional[str] = None
    score_dasec: Optional[float] = None
    score_completude: Optional[float] = None
    critic_valide: Optional[bool] = None
    dans_crm: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    annuaires: Optional[str] = None
    score_detail: Optional[str] = None
    # Avancement de la prospection
    prochaine_action: Optional[str] = None
    prochaine_action_date: Optional[str] = None
    motif_perte: Optional[str] = None
    date_mise_a_jour: Optional[str] = None
    contact_email_personnel: Optional[str] = None
    contact_telephone_personnel: Optional[str] = None
    contact_linkedin_personnel: Optional[str] = None

    class Config:
        from_attributes = True