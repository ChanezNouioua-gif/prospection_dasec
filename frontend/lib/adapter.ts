import { ProspectApi } from "./types";

export function toEtablissement(p: ProspectApi) {
  const ressources: { label: string; icon: "site" | "maps" | "linkedin" | "annuaire" | "facebook"; url: string }[] = [];
  if (p.site_web) ressources.push({ label: "Site web officiel", icon: "site", url: p.site_web });
  if (p.facebook) ressources.push({ label: "Facebook", icon: "facebook", url: p.facebook });
  if (p.linkedin) ressources.push({ label: "LinkedIn", icon: "linkedin", url: p.linkedin });
  if (p.pages_jaunes) ressources.push({ label: "Pages Jaunes", icon: "annuaire", url: p.pages_jaunes });
  if (p.latitude && p.longitude) {
    ressources.push({
      label: "Localisation (carte)",
      icon: "maps",
      url: `https://www.google.com/maps?q=${p.latitude},${p.longitude}`,
    });
  }
  if (p.annuaires) {
  try {
    const liens: string[] = JSON.parse(p.annuaires);
    liens.forEach((url, i) =>
      ressources.push({ label: `Annuaire ${i + 1}`, icon: "annuaire", url })
    );
  } catch {}
  }

  let scoreDetail: { sous_secteur: number; commune: number; effectif: number; maturite: number; reseau: number; bonus: number } | null = null;
  let scorePoids: { secteur: number; commune: number; effectif: number; maturite_digitale: number; reseau_groupe: number } | null = null;

  if (p.score_detail) {
    try {
      const parsed = JSON.parse(p.score_detail);
      scoreDetail = parsed.contributions ?? null;
      scorePoids = parsed.poids ?? null;
    } catch {}
  }


  return {
    id: String(p.id),
    nom: p.nom,
    wilaya: p.wilaya_name ?? "—",
    commune: p.commune_brute ?? "—",
    secteur: p.secteur,
    sousSecteur: p.sous_secteur ?? "—",
    score: Math.round(p.score_dasec ?? 0),
    dansCrm: p.dans_crm === 1,
    type: p.sous_secteur ?? p.secteur,
    statutJuridique: p.type_gestion ?? "—",
    effectif: p.effectif ?? "—",
    reseau: p.reseau_groupe ? (p.reseau_nom ?? "Oui") : "Non",
    adresse: p.adresse ?? "—",
    telephone: p.telephone ?? "—",
    email: p.email ?? "—",
    site: p.site_web ?? "—",
    contact: {
      nom: p.contact_nom ?? "—",
      role: p.contact_fonction ?? "—",
      telephone: p.telephone ?? "—",
      email: p.email ?? "—",
    },
    ressources,
    scoreDetail,
    scorePoids,
    statut: p.statut,
    prochaineAction: p.prochaine_action,
    prochaineActionDate: p.prochaine_action_date,
  };
}