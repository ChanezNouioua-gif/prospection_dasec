export interface ProspectApi {
  id: number;
  nom: string;
  secteur: string;
  sous_secteur: string | null;
  wilaya_name: string | null;
  commune_brute: string | null;
  adresse: string | null;
  telephone: string | null;
  email: string | null;
  site_web: string | null;
  facebook: string | null;
  linkedin: string | null;
  google_business: string | null;
  pages_jaunes: string | null;
  effectif: string | null;
  reseau_groupe: number | null;
  reseau_nom: string | null;
  contact_nom: string | null;
  contact_fonction: string | null;
  statut: string | null;
  type_gestion: string | null;
  score_dasec: number | null;
  dans_crm: number | null;
  latitude: number | null;
  longitude: number | null;
  annuaires: string | null; 
  score_detail: string | null;
  prochaine_action: string | null;
  prochaine_action_date: string | null;
}

export interface ProspectsResponse {
  items: ProspectApi[];
  total: number;
  page: number;
}