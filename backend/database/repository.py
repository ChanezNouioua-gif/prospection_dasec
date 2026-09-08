"""
Toutes les requêtes SQL brutes vivent ici, et nulle part ailleurs.

DatabaseAgent est le seul composant qui instancie EntrepriseRepository.
Aucun autre agent ne doit importer sqlite3 ou ce module directement —
c'est ce qui garantit "les autres agents ne manipulent jamais SQLite"
demandé dans l'architecture.
"""

import sqlite3
from typing import Optional


NOUVELLES_COLONNES = {
    "email_qualite": "INTEGER",
    "site_web_qualite": "INTEGER",
    "effectif": "TEXT",
    "reseau_groupe": "INTEGER",
    "reseau_nom": "TEXT",
    "contact_nom": "TEXT",
    "contact_fonction": "TEXT",
    "google_business": "TEXT",
    "pages_jaunes": "TEXT",
    "sources_confidence": "TEXT",
    "critic_valide": "INTEGER",
    "recherche_payante_utilisee": "INTEGER",
    "annuaires": "TEXT",
    "score_detail": "TEXT",
    "date_ajout_crm": "TEXT",
    "prochaine_action": "TEXT",
    "prochaine_action_date": "TEXT",
    "motif_perte": "TEXT",
    "contact_email_personnel": "TEXT",
    "contact_telephone_personnel": "TEXT",
    "contact_linkedin_personnel": "TEXT",    
    "contact_personnel_tente": "INTEGER",
}


class EntrepriseRepository:
    def __init__(self, connexion: sqlite3.Connection):
        self.connexion = connexion

    # ---------- schéma ----------

    def _colonne_existe(self, table: str, colonne: str) -> bool:
        cursor = self.connexion.execute(f"PRAGMA table_info({table})")
        return any(row["name"] == colonne for row in cursor.fetchall())

    def s_assurer_schema_a_jour(self):
        for colonne, type_sql in NOUVELLES_COLONNES.items():
            if not self._colonne_existe("entreprises", colonne):
                self.connexion.execute(f"ALTER TABLE entreprises ADD COLUMN {colonne} {type_sql}")
        self.connexion.execute("""
            CREATE TABLE IF NOT EXISTS enrichment_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entreprise_id INTEGER,
                etape TEXT,
                statut TEXT,
                detail TEXT,
                cout_estime_usd REAL DEFAULT 0,
                date TEXT DEFAULT (datetime('now'))
            )
        """)
        self.connexion.execute("""
          CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            nom_complet TEXT,
            date_creation TEXT DEFAULT (datetime('now'))
           )
         """)
        self.connexion.execute("""
          CREATE TABLE IF NOT EXISTS interactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entreprise_id INTEGER,
            type TEXT,
            contenu TEXT,
            date TEXT DEFAULT (datetime('now'))
           )
         """)
        self.connexion.commit()

    def maj_sources_discovery(self, entreprise_id: int, sources_dict: dict):
        """Contrairement à maj_profil, on écrase délibérément les valeurs
        existantes : une source validée par le Critic est plus fiable qu'une
        valeur historique (ex: site_web scrapé depuis Overpass/OSM, jamais vérifié)."""
        import json
        self.connexion.execute("""
            UPDATE entreprises
            SET site_web = COALESCE(?, site_web),
                facebook = COALESCE(?, facebook),
                linkedin = COALESCE(?, linkedin),
                google_business = ?,
                pages_jaunes = ?,
                annuaires = ?,
                sources_confidence = ?,
                critic_valide = ?,
                recherche_payante_utilisee = ?
            WHERE id = ?
        """, (
            sources_dict.get("website"),
            sources_dict.get("facebook"),
            sources_dict.get("linkedin"),
            sources_dict.get("google_business"),
            sources_dict.get("pages_jaunes"),
            json.dumps(sources_dict.get("annuaires", [])),
            json.dumps(sources_dict.get("confidence", {})),
            int(sources_dict.get("critic_valide", False)),
            int(sources_dict.get("recherche_payante_utilisee", False)),
            entreprise_id,
        ))
        self.connexion.commit() 

    # ---------- lecture ----------

    def get_par_id(self, entreprise_id: int) -> Optional[dict]:
        cursor = self.connexion.execute(
            "SELECT * FROM entreprises WHERE id = ?", (entreprise_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_echantillon(self, ids: list[int]) -> list[dict]:
        placeholders = ",".join("?" * len(ids))
        cursor = self.connexion.execute(
            f"SELECT * FROM entreprises WHERE id IN ({placeholders})", ids
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_lot_a_enrichir(self, secteur: str, limite: int, seulement_non_traites: bool = True) -> list[dict]:
        condition = "AND effectif IS NULL" if seulement_non_traites else ""
        cursor = self.connexion.execute(
            f"SELECT * FROM entreprises WHERE secteur = ? {condition} LIMIT ?",
            (secteur, limite),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_densite_communes(self) -> dict:
        cursor = self.connexion.execute("""
            SELECT commune_id, COUNT(*) as n FROM entreprises
            WHERE commune_id IS NOT NULL GROUP BY commune_id
        """)
        return {row["commune_id"]: row["n"] for row in cursor.fetchall()}

    # ---------- écriture ----------

    def maj_profil(self, entreprise_id: int, donnees: dict):
        """`donnees` ne doit contenir que des clés correspondant à des colonnes
        existantes ; on ignore silencieusement les None pour ne jamais écraser
        une valeur existante avec du vide, mais on écrase bien avec une nouvelle
        valeur non-null (une revalidation ultérieure doit pouvoir corriger une
        donnée fausse)."""
        colonnes_autorisees = {
          "telephone", "telephone2", "email", "facebook", "linkedin",
          "email_qualite", "site_web_qualite", "effectif",
          "reseau_groupe", "reseau_nom", "contact_nom", "contact_fonction",
          "contact_email_personnel", "contact_telephone_personnel", "contact_linkedin_personnel",
        }
        existant = self.get_par_id(entreprise_id) or {}

        a_ecrire = {}
        
        for cle, valeur in donnees.items():
         if cle not in colonnes_autorisees or valeur is None:
            continue
         a_ecrire[cle] = valeur

        if not a_ecrire:
            return

        set_clause = ", ".join(f"{c} = ?" for c in a_ecrire)
        valeurs = list(a_ecrire.values()) + [entreprise_id]
        self.connexion.execute(
            f"UPDATE entreprises SET {set_clause} WHERE id = ?", valeurs
        )
        self.connexion.commit()

    def maj_score(self, entreprise_id: int, score_dasec: float, score_completude: float, detail: dict | None = None):
      import json
      self.connexion.execute(
        "UPDATE entreprises SET score_dasec = ?, score_completude = ?, score_detail = ? WHERE id = ?",
        (score_dasec, score_completude, json.dumps(detail) if detail else None, entreprise_id),
      )
      self.connexion.commit()

    def logger_etape(self, entreprise_id: int, etape: str, statut: str,
                      detail: str = "", cout_estime_usd: float = 0.0):
        self.connexion.execute("""
            INSERT INTO enrichment_log(entreprise_id, etape, statut, detail, cout_estime_usd)
            VALUES (?, ?, ?, ?, ?)
        """, (entreprise_id, etape, statut, detail, cout_estime_usd))
        self.connexion.commit()

    def ajouter_au_crm(self, entreprise_id: int):
     existant = self.get_par_id(entreprise_id)
     statut_initial = existant.get("statut") if existant else None
     self.connexion.execute("""
        UPDATE entreprises
        SET dans_crm = 1,
            statut = COALESCE(?, 'NOUVEAU'),
            date_ajout_crm = COALESCE(date_ajout_crm, datetime('now'))
        WHERE id = ?
     """, (statut_initial, entreprise_id))
     self.connexion.commit()

    def maj_statut_crm(self, entreprise_id: int, statut: str):
     self.connexion.execute(
        "UPDATE entreprises SET statut = ? WHERE id = ?", (statut, entreprise_id)
     )
     self.connexion.commit()
     self.ajouter_interaction(entreprise_id, "statut", f"Statut changé vers {statut}")

    def resume_pipeline(self) -> list[dict]:
     cursor = self.connexion.execute("""
        SELECT COALESCE(statut, 'NOUVEAU') as statut, COUNT(*) as n
        FROM entreprises WHERE dans_crm = 1
        GROUP BY statut
     """)
     return [dict(row) for row in cursor.fetchall()]

    def top_opportunites(self, limite: int = 3) -> list[dict]:
     cursor = self.connexion.execute("""
        SELECT * FROM entreprises WHERE dans_crm = 1
        ORDER BY score_dasec DESC LIMIT ?
     """, (limite,))
     return [dict(row) for row in cursor.fetchall()]

    def prospects_jamais_contactes(self) -> int:
     return self.connexion.execute("""
        SELECT COUNT(*) FROM entreprises
        WHERE dans_crm = 1 AND (statut IS NULL OR statut = 'NOUVEAU')
     """).fetchone()[0]

    def ajoutes_ce_mois(self) -> int:
     return self.connexion.execute("""
        SELECT COUNT(*) FROM entreprises
        WHERE dans_crm = 1 AND date_ajout_crm >= date('now', 'start of month')
     """).fetchone()[0]  


    def ajouter_interaction(self, entreprise_id: int, type_: str, contenu: str):
        self.connexion.execute(
            "INSERT INTO interactions(entreprise_id, type, contenu) VALUES (?, ?, ?)",
            (entreprise_id, type_, contenu),
        )
        self.connexion.commit()

    def get_interactions(self, entreprise_id: int) -> list[dict]:
        cursor = self.connexion.execute(
            "SELECT * FROM interactions WHERE entreprise_id = ? ORDER BY date DESC", (entreprise_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_interactions_recentes(self, limite: int = 10) -> list[dict]:
        cursor = self.connexion.execute("""
            SELECT i.*, e.nom as entreprise_nom
            FROM interactions i JOIN entreprises e ON e.id = i.entreprise_id
            ORDER BY i.date DESC LIMIT ?
        """, (limite,))
        return [dict(row) for row in cursor.fetchall()]

    def get_historique_interactions(
        self,
        recherche: str | None = None,
        type_interaction: str | None = None,
        page: int = 1,
        limite: int = 25,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: list[str] = []

        if recherche:
            conditions.append("(e.nom LIKE ? OR i.contenu LIKE ?)")
            motif = f"%{recherche}%"
            params.extend([motif, motif])
        if type_interaction:
            conditions.append("i.type = ?")
            params.append(type_interaction)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self.connexion.execute(
            f"SELECT COUNT(*) FROM interactions i JOIN entreprises e ON e.id = i.entreprise_id {where}",
            params,
        ).fetchone()[0]
        rows = self.connexion.execute(
            f"""
            SELECT i.id, i.entreprise_id, i.type, i.contenu, i.date,
                   e.nom AS entreprise_nom, e.secteur, e.sous_secteur
            FROM interactions i
            JOIN entreprises e ON e.id = i.entreprise_id
            {where}
            ORDER BY i.date DESC, i.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [limite, (page - 1) * limite],
        ).fetchall()
        return [dict(row) for row in rows], total

    def maj_prochaine_action(self, entreprise_id: int, texte: str, date: str):
        self.connexion.execute(
            "UPDATE entreprises SET prochaine_action = ?, prochaine_action_date = ? WHERE id = ?",
            (texte, date, entreprise_id),
        )
        self.connexion.commit()

    def prospects_sans_prochaine_action(self) -> int:
        return self.connexion.execute("""
            SELECT COUNT(*) FROM entreprises
            WHERE dans_crm = 1 AND (prochaine_action_date IS NULL OR prochaine_action_date = '')
        """).fetchone()[0]

    def taches_en_retard(self) -> int:
        return self.connexion.execute("""
            SELECT COUNT(*) FROM entreprises
            WHERE dans_crm = 1 AND prochaine_action_date IS NOT NULL
            AND prochaine_action_date != '' AND prochaine_action_date < date('now')
        """).fetchone()[0]

    def opportunites_inactives(self) -> int:
        return self.connexion.execute("""
            SELECT COUNT(*) FROM entreprises e
            WHERE dans_crm = 1
            AND COALESCE(
                (SELECT MAX(date) FROM interactions i WHERE i.entreprise_id = e.id),
                e.date_ajout_crm
            ) < datetime('now', '-7 days')
        """).fetchone()[0]  

    def taches_du_jour(self) -> list[dict]:
      """Une 'tâche' = la prochaine_action de chaque prospect, dérivée du
      champ existant plutôt que d'une table séparée — on garde une seule
      action par prospect, comme décidé."""
      cursor = self.connexion.execute("""
        SELECT id, nom, prochaine_action, prochaine_action_date
        FROM entreprises
        WHERE dans_crm = 1
          AND prochaine_action_date IS NOT NULL AND prochaine_action_date != ''
          AND prochaine_action_date <= date('now')
      """)
      return [dict(row) for row in cursor.fetchall()]

    def completer_tache(self, entreprise_id: int):
     self.connexion.execute("""
        UPDATE entreprises SET prochaine_action = NULL, prochaine_action_date = NULL
        WHERE id = ?
     """, (entreprise_id,))
     self.connexion.commit()
     self.ajouter_interaction(entreprise_id, "relance", "Action complétée")

    def marquer_perdu(self, entreprise_id: int, motif: str):
     self.connexion.execute("""
        UPDATE entreprises
        SET statut = 'PERDU', motif_perte = ?, date_mise_a_jour = datetime('now')
        WHERE id = ?
     """, (motif, entreprise_id))
     self.connexion.commit()
     self.ajouter_interaction(entreprise_id, "statut", f"Marqué perdu : {motif}")

    def prospects_perdus_recents(self, limite: int = 5) -> list[dict]:
     cursor = self.connexion.execute("""
        SELECT id, nom, motif_perte, date_mise_a_jour
        FROM entreprises WHERE statut = 'PERDU'
        ORDER BY date_mise_a_jour DESC LIMIT ?
     """, (limite,))
     return [dict(row) for row in cursor.fetchall()]


    def get_candidats_contact_personnel(self, limite: int) -> list[dict]:
     cursor = self.connexion.execute("""
        SELECT * FROM entreprises
        WHERE contact_nom IS NOT NULL
          AND (contact_personnel_tente IS NULL OR contact_personnel_tente = 0)
        LIMIT ?
     """, (limite,))
     return [dict(row) for row in cursor.fetchall()]

    def maj_contact_personnel(self, entreprise_id: int, profil):
     donnees = {"contact_personnel_tente": 1}
     if profil.contact_email_personnel:
        donnees["contact_email_personnel"] = profil.contact_email_personnel
     if profil.contact_telephone_personnel:
        donnees["contact_telephone_personnel"] = profil.contact_telephone_personnel
     if profil.contact_linkedin_personnel:
        donnees["contact_linkedin_personnel"] = profil.contact_linkedin_personnel
     set_clause = ", ".join(f"{c} = ?" for c in donnees)
     valeurs = list(donnees.values()) + [entreprise_id]
     self.connexion.execute(f"UPDATE entreprises SET {set_clause} WHERE id = ?", valeurs)
     self.connexion.commit()
