"""
DatabaseAgent — seul composant du projet qui manipule SQLite.

Tous les autres agents reçoivent des dataclasses (Entreprise, ProfileData,
ScoreResult) et n'importent jamais sqlite3 ni database.repository directement.
"""

from database.repository import EntrepriseRepository
from models.schemas import Entreprise, ProfileData, ScoreResult, DiscoverySources



class DatabaseAgent:
    def __init__(self, repository: EntrepriseRepository):
        self.repository = repository

    def preparer_schema(self):
        self.repository.s_assurer_schema_a_jour()

    def charger_entreprise(self, entreprise_id: int) -> Entreprise | None:
        row = self.repository.get_par_id(entreprise_id)
        return Entreprise.from_row(row) if row else None

    def charger_lot(self, ids: list[int]) -> list[Entreprise]:
        rows = self.repository.get_echantillon(ids)
        return [Entreprise.from_row(r) for r in rows]

    def charger_densite_communes(self) -> dict:
        return self.repository.get_densite_communes()

    def commune_id_de(self, entreprise_id: int) -> int | None:
        row = self.repository.get_par_id(entreprise_id)
        return row.get("commune_id") if row else None

    def sauvegarder_profil(self, entreprise_id: int, profil: ProfileData):
        self.repository.maj_profil(entreprise_id, profil.to_dict())

    def sauvegarder_sources(self, entreprise_id: int, sources: DiscoverySources):
        self.repository.maj_sources_discovery(entreprise_id, sources.to_dict())

    
    def sauvegarder_score(self, entreprise_id: int, score: ScoreResult):
        self.repository.maj_score(entreprise_id, score.score_dasec, score.score_completude, score.detail)

    def logger(self, entreprise_id: int, etape: str, statut: str, detail: str = "", cout_usd: float = 0.0):
        self.repository.logger_etape(entreprise_id, etape, statut, detail, cout_usd)
