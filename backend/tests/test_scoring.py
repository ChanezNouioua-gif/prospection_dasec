import sqlite3
import pytest

from database.connection import obtenir_connexion
from database.repository import EntrepriseRepository
from agents.database_agent import DatabaseAgent
from agents.scoring import ScoringAgent
from models.schemas import ProfileData


@pytest.fixture
def base_test(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE entreprises(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, secteur TEXT, sous_secteur TEXT, telephone TEXT, telephone2 TEXT,
            email TEXT, site_web TEXT, facebook TEXT, linkedin TEXT, adresse TEXT,
            commune_brute TEXT, wilaya_name TEXT, commune_id INTEGER, latitude REAL, longitude REAL,
            conventionne INTEGER DEFAULT 0, statut TEXT, source TEXT, source_id TEXT,
            date_collecte TEXT, date_mise_a_jour TEXT, score_completude REAL, score_dasec REAL,
            type_gestion TEXT
        )
    """)
    conn.execute("CREATE TABLE communes(id INTEGER PRIMARY KEY, commune_name TEXT, wilaya_code TEXT, wilaya_name TEXT)")
    conn.execute("INSERT INTO communes VALUES (1, 'Alger Centre', '16', 'Alger')")
    conn.execute("INSERT INTO communes VALUES (2, 'Tamanrasset', '11', 'Tamanrasset')")
    conn.execute("""INSERT INTO entreprises (nom, secteur, sous_secteur, type_gestion, commune_id)
                     VALUES ('CHU Mustapha', 'santé', 'CHU', 'public', 1)""")
    conn.execute("""INSERT INTO entreprises (nom, secteur, sous_secteur, type_gestion, commune_id)
                     VALUES ('Pharmacie El Fedjr', 'santé', 'pharmacie', 'privé', 1)""")
    conn.execute("""INSERT INTO entreprises (nom, secteur, sous_secteur, type_gestion, commune_id)
                     VALUES ('Cabinet Dr Test', 'santé', 'cabinet médical', 'privé', 2)""")
    conn.commit()
    conn.close()
    return str(db_path)


def test_schema_migration_ajoute_les_colonnes(base_test):
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        db_agent = DatabaseAgent(repo)
        db_agent.preparer_schema()
        assert repo._colonne_existe("entreprises", "effectif")
        assert repo._colonne_existe("entreprises", "reseau_groupe")


def test_score_chu_public_non_enrichi(base_test):
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        db_agent = DatabaseAgent(repo)
        db_agent.preparer_schema()
        scoring = ScoringAgent(db_agent.charger_densite_communes())

        chu = db_agent.charger_entreprise(1)
        resultat = scoring.run(chu, ProfileData(), commune_id=1)

        assert resultat.detail["score_secteur"] == 100  # CHU = 10/10
        assert resultat.detail["bonus_type_gestion"] == 0  # public = +0
        assert resultat.score_dasec == pytest.approx(35.0)


def test_bonus_prive_applique(base_test):
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        db_agent = DatabaseAgent(repo)
        db_agent.preparer_schema()
        scoring = ScoringAgent(db_agent.charger_densite_communes())

        pharmacie = db_agent.charger_entreprise(2)
        profil = ProfileData(email_qualite=0, site_web_qualite=0, effectif="<10", reseau_groupe=0)
        resultat = scoring.run(pharmacie, profil, commune_id=1)

        assert resultat.detail["bonus_type_gestion"] == 2  # privé = +2


def test_reseau_groupe_force_minimum_secteur(base_test):
    """Un cabinet médical (barème 4/10) en réseau doit être remonté à 7/10 minimum,
    conformément à l'exception validée par DASEC."""
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        db_agent = DatabaseAgent(repo)
        db_agent.preparer_schema()
        scoring = ScoringAgent(db_agent.charger_densite_communes())

        cabinet = db_agent.charger_entreprise(3)
        profil_sans_reseau = ProfileData(reseau_groupe=0)
        profil_avec_reseau = ProfileData(reseau_groupe=1, reseau_nom="Groupe X")

        score_sans = scoring.run(cabinet, profil_sans_reseau, commune_id=2)
        score_avec = scoring.run(cabinet, profil_avec_reseau, commune_id=2)

        assert score_sans.detail["score_secteur"] == 40   # 4/10
        assert score_avec.detail["score_secteur"] == 70   # forcé à 7/10 minimum


def test_maj_profil_n_ecrase_jamais_une_valeur_existante(base_test):
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        repo.s_assurer_schema_a_jour()
        conn.execute("UPDATE entreprises SET telephone = '0550123456' WHERE id = 2")
        conn.commit()

        repo.maj_profil(2, {"telephone": "+213700000000", "effectif": "<10"})
        row = repo.get_par_id(2)

        assert row["telephone"] == "0550123456"  # inchangé
        assert row["effectif"] == "<10"           # nouveau champ rempli


def test_secteur_sans_config_leve_une_erreur_explicite(base_test):
    with obtenir_connexion(base_test) as conn:
        repo = EntrepriseRepository(conn)
        db_agent = DatabaseAgent(repo)
        db_agent.preparer_schema()
        conn.execute("UPDATE entreprises SET secteur = 'banque' WHERE id = 1")
        conn.commit()

        scoring = ScoringAgent(db_agent.charger_densite_communes())
        banque = db_agent.charger_entreprise(1)

        with pytest.raises(ValueError, match="Aucune configuration"):
            scoring.run(banque, ProfileData(), commune_id=1)
