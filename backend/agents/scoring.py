"""
ScoringAgent — calcule score_dasec et score_completude.

Lit son barème depuis config.SECTOR_CONFIGS[entreprise.secteur], jamais en dur :
ajouter un secteur (banques, assurances...) ne demande aucune modification ici,
seulement une nouvelle entrée dans config.py.
"""

from models.schemas import Entreprise, ProfileData, ScoreResult
from config import SECTOR_CONFIGS


class ScoringAgent:
    def __init__(self, densite_communes: dict[int, int]):
        self.densite_communes = densite_communes
        self._valeurs_densite_triees = sorted(densite_communes.values())

    def run(self, entreprise: Entreprise, profil: ProfileData, commune_id: int | None) -> ScoreResult:
        cfg = SECTOR_CONFIGS.get(entreprise.secteur)
        if cfg is None:
            raise ValueError(
                f"Aucune configuration de scoring pour le secteur '{entreprise.secteur}'. "
                f"Ajoute une entrée dans config.SECTOR_CONFIGS."
            )
        detail = {}
        detail["score_secteur"] = self._score_secteur(entreprise.sous_secteur, profil.reseau_groupe, cfg)
        detail["score_commune"] = self._score_commune(commune_id)
        detail["score_effectif"] = cfg["score_effectif"].get(profil.effectif, 0)
        detail["score_maturite"] = self._score_maturite(profil.email_qualite, profil.site_web_qualite)
        detail["score_reseau"] = 100 if profil.reseau_groupe else 0
        poids = cfg["poids"]
        score_base = (
            poids["secteur"] * detail["score_secteur"] +
            poids["commune"] * detail["score_commune"] +
            poids["effectif"] * detail["score_effectif"] +
            poids["maturite_digitale"] * detail["score_maturite"] +
            poids["reseau_groupe"] * detail["score_reseau"]
        )
        bonus = cfg["bonus_type_gestion"].get(entreprise.type_gestion, 0)
        detail["bonus_type_gestion"] = bonus
        detail["poids"] = poids
        detail["contributions"] = {
            "sous_secteur": round(poids["secteur"] * detail["score_secteur"] / 100, 1),
            "commune": round(poids["commune"] * detail["score_commune"] / 100, 1),
            "effectif": round(poids["effectif"] * detail["score_effectif"] / 100, 1),
            "maturite": round(poids["maturite_digitale"] * detail["score_maturite"] / 100, 1),
            "reseau": round(poids["reseau_groupe"] * detail["score_reseau"] / 100, 1),
            "bonus": bonus,
        }
        score_dasec = round(score_base + bonus, 1)
        score_completude = self._score_completude(entreprise, profil)
        return ScoreResult(score_dasec=score_dasec, score_completude=score_completude, detail=detail)

    @staticmethod
    def _score_secteur(sous_secteur: str, reseau_groupe: int | None, cfg: dict) -> float:
        base = cfg["bareme_sous_secteur"].get(sous_secteur, 0)
        if reseau_groupe:
            base = max(base, cfg["minimum_si_reseau_groupe"])
        return base * 10

    def _score_commune(self, commune_id: int | None) -> float:
        if not self._valeurs_densite_triees or commune_id is None:
            return 0.0
        nb = self.densite_communes.get(commune_id)
        if nb is None:
            return 0.0
        rang = sum(1 for v in self._valeurs_densite_triees if v <= nb)
        return round((rang / len(self._valeurs_densite_triees)) * 100, 1)

    @staticmethod
    def _score_maturite(email_qualite: int | None, site_web_qualite: int | None) -> float:
        partie_email = (email_qualite or 0) * 50
        partie_site = ((site_web_qualite or 0) / 2) * 50
        return partie_email + partie_site

    @staticmethod
    def _score_completude(entreprise: Entreprise, profil: ProfileData) -> float:
        champs = [
            bool(entreprise.telephone or entreprise.telephone2 or profil.telephone),
            bool(entreprise.email or profil.email),
            bool(entreprise.site_web),
            bool(entreprise.adresse),
            bool(entreprise.commune_name),
            bool(profil.effectif),
        ]
        return round((sum(champs) / len(champs)) * 100, 1)
