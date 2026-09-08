"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  Users,
  Calendar,
  CircleAlert,
  Send,
  Loader2,
  XCircle,
  ExternalLink,
  Globe2,
} from "lucide-react";
import { toEtablissement } from "@/lib/adapter";

function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}
function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M22.675 0h-21.35C.6 0 0 .6 0 1.325v21.351C0 23.4.6 24 1.325 24H12.82v-9.294H9.692v-3.622h3.128V8.413c0-3.1 1.893-4.788 4.659-4.788 1.325 0 2.463.099 2.795.143v3.24h-1.918c-1.504 0-1.795.715-1.795 1.763v2.313h3.587l-.467 3.622h-3.12V24h6.116C23.4 24 24 23.4 24 22.675V1.325C24 .6 23.4 0 22.675 0z" />
    </svg>
  );
}

type Etablissement = ReturnType<typeof toEtablissement>;
const RESSOURCE_ICON = {
  site: Globe2,
  maps: MapPin,
  linkedin: LinkedinIcon,
  annuaire: ExternalLink,
  facebook: FacebookIcon,
};

const STATUTS_PIPELINE = [
  "NOUVEAU", "A_CONTACTER", "CONTACTE", "ECHANGE", "RDV", "PROPOSITION", "GAGNE", "PERDU",
] as const;

const LABEL_STATUT: Record<string, string> = {
  NOUVEAU: "Nouveau",
  A_CONTACTER: "À contacter",
  CONTACTE: "Contacté",
  ECHANGE: "Échange",
  RDV: "RDV",
  PROPOSITION: "Proposition",
  GAGNE: "Gagné",
  PERDU: "Perdu",
};

interface ProspectDetail {
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
  score_dasec: number | null;
  score_completude: number | null;
  score_detail: string | null;
  prochaine_action: string | null;
  prochaine_action_date: string | null;
  motif_perte: string | null;
  date_mise_a_jour: string | null;
}

interface Interaction {
  id: number;
  entreprise_id: number;
  type: string;
  contenu: string;
  date: string;
}

const TYPES_ACTIVITE = [
  { value: "appel", label: "Appel" },
  { value: "email", label: "Email" },
  { value: "rdv", label: "RDV" },
  { value: "note", label: "Note" },
] as const;

export default function ProspectPage() {
  const params = useParams();
  const prospectId = params.id as string;

  const [prospect, setProspect] = useState<ProspectDetail | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  const [nouvelleActivite, setNouvelleActivite] = useState("");
  const [typeActivite, setTypeActivite] = useState<string>("note");
  const [envoiEnCours, setEnvoiEnCours] = useState(false);

  const [motifPerte, setMotifPerte] = useState("");
  const [afficherFormPerdu, setAfficherFormPerdu] = useState(false);

  const [prochaineActionTexte, setProchaineActionTexte] = useState("");
  const [prochaineActionDate, setProchaineActionDate] = useState("");

  async function charger() {
    setLoading(true);
    setErreur(null);
    try {
      const [resProspect, resInteractions] = await Promise.all([
        fetch(`http://localhost:8000/prospects/${prospectId}`, { credentials: "include", cache: "no-store" }),
        fetch(`http://localhost:8000/prospects/${prospectId}/interactions`, { credentials: "include", cache: "no-store" }),
      ]);
      if (!resProspect.ok) throw new Error("Prospect introuvable");
      const dataProspect: ProspectDetail = await resProspect.json();
      const dataInteractions: Interaction[] = resInteractions.ok ? await resInteractions.json() : [];

      setProspect(dataProspect);
      setInteractions(dataInteractions);
      setProchaineActionTexte(dataProspect.prochaine_action ?? "");
      setProchaineActionDate(dataProspect.prochaine_action_date ?? "");
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prospectId]);

  async function changerStatut(statut: string) {
    if (!prospect) return;
    setProspect({ ...prospect, statut }); // optimiste
    try {
      const res = await fetch(`http://localhost:8000/prospects/${prospectId}/statut?statut=${statut}`, {
        method: "PATCH",
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      charger();
    } catch {
      charger(); // rollback en rechargeant l'état réel
    }
  }

  async function envoyerActivite() {
    if (!nouvelleActivite.trim() || envoiEnCours) return;
    setEnvoiEnCours(true);
    try {
      const res = await fetch(`http://localhost:8000/prospects/${prospectId}/notes`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contenu: nouvelleActivite, type: typeActivite }),
      });
      if (!res.ok) throw new Error();
      setNouvelleActivite("");
      await charger();
    } catch {
      setErreur("Échec de l'envoi de l'activité");
    } finally {
      setEnvoiEnCours(false);
    }
  }

  async function enregistrerProchaineAction() {
    if (!prochaineActionTexte.trim() || !prochaineActionDate) return;
    try {
      const res = await fetch(`http://localhost:8000/prospects/${prospectId}/prochaine-action`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texte: prochaineActionTexte, date: prochaineActionDate }),
      });
      if (!res.ok) throw new Error();
      charger();
    } catch {
      setErreur("Échec de la mise à jour de la prochaine action");
    }
  }

  async function confirmerPerdu() {
    if (!motifPerte.trim()) return;
    try {
      const res = await fetch(`http://localhost:8000/prospects/${prospectId}/perdu`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motif: motifPerte }),
      });
      if (!res.ok) throw new Error();
      setAfficherFormPerdu(false);
      setMotifPerte("");
      charger();
    } catch {
      setErreur("Échec du marquage comme perdu");
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50/60">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </main>
    );
  }

  if (erreur && !prospect) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50/60">
        <p className="text-sm font-medium text-rose-600">{erreur}</p>
        <Link href="/crm" className="text-sm font-medium text-blue-600 hover:underline">
          Retour au CRM
        </Link>
      </main>
    );
  }

  if (!prospect) return null;

  let scoreDetail: Record<string, number> | null = null;
  if (prospect.score_detail) {
    try {
      const parsed: unknown = JSON.parse(prospect.score_detail);
      const values =
        parsed && typeof parsed === "object" && !Array.isArray(parsed) &&
        "contributions" in parsed &&
        parsed.contributions && typeof parsed.contributions === "object" && !Array.isArray(parsed.contributions)
          ? parsed.contributions
          : parsed;

      if (values && typeof values === "object" && !Array.isArray(values)) {
        scoreDetail = Object.fromEntries(
          Object.entries(values).filter(([, value]) => typeof value === "number")
        );
      }
    } catch {
      scoreDetail = null;
    }
  }

  return (
    <main className="min-h-screen bg-slate-50/60 text-slate-900">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <Link href="/crm" className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" />
          Retour au CRM
        </Link>

        {erreur && (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600">
            {erreur}
          </div>
        )}

        {/* En-tête */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Building2 className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">{prospect.nom}</h1>
                <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
                  {prospect.sous_secteur ?? prospect.secteur}
                  {prospect.wilaya_name && (
                    <>
                      <span className="text-slate-300">·</span>
                      <MapPin className="h-3 w-3" />
                      {prospect.commune_brute ? `${prospect.commune_brute}, ` : ""}
                      {prospect.wilaya_name}
                    </>
                  )}
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <span className="rounded-full bg-blue-50 px-3 py-1 text-lg font-bold text-blue-600">
                {Math.round(prospect.score_dasec ?? 0)}
              </span>
              <span className="text-xs text-slate-400">Score DASEC</span>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-1.5">
            {STATUTS_PIPELINE.map((s) => (
              <button
                key={s}
                onClick={() => (s === "PERDU" ? setAfficherFormPerdu(true) : changerStatut(s))}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                  prospect.statut === s
                    ? s === "GAGNE"
                      ? "bg-emerald-600 text-white"
                      : s === "PERDU"
                      ? "bg-rose-600 text-white"
                      : "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                }`}
              >
                {LABEL_STATUT[s]}
              </button>
            ))}
          </div>

          {afficherFormPerdu && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-100 bg-rose-50/60 p-3">
              <XCircle className="h-4 w-4 shrink-0 text-rose-500" />
              <input
                type="text"
                value={motifPerte}
                onChange={(e) => setMotifPerte(e.target.value)}
                placeholder="Motif de la perte..."
                className="flex-1 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-rose-400"
              />
              <button
                onClick={confirmerPerdu}
                className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
              >
                Confirmer
              </button>
              <button
                onClick={() => setAfficherFormPerdu(false)}
                className="rounded-lg px-2 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-600"
              >
                Annuler
              </button>
            </div>
          )}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
          <div className="space-y-6">
            {/* Avancement de la prospection */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <CircleAlert className="h-4 w-4 text-slate-400" />
                <p className="text-sm font-semibold text-slate-900">Avancement de la prospection</p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-slate-400">Statut actuel</p>
                  <p className="font-semibold text-slate-800">
                    {prospect.statut ? LABEL_STATUT[prospect.statut] ?? prospect.statut : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Dernière mise à jour</p>
                  <p className="font-semibold text-slate-800">
                    {prospect.date_mise_a_jour
                      ? new Date(prospect.date_mise_a_jour.replace(" ", "T") + "Z").toLocaleDateString("fr-FR")
                      : "—"}
                  </p>
                </div>
              </div>

              {prospect.statut === "PERDU" && prospect.motif_perte && (
                <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">
                  Motif de perte : {prospect.motif_perte}
                </p>
              )}

              <div className="mt-4 border-t border-slate-100 pt-4">
                <p className="mb-2 text-xs font-medium text-slate-500">Prochaine action</p>
                <div className="flex flex-wrap gap-2">
                  <input
                    type="text"
                    value={prochaineActionTexte}
                    onChange={(e) => setProchaineActionTexte(e.target.value)}
                    placeholder="Ex : Relancer par email"
                    className="flex-1 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 text-sm outline-none focus:border-blue-500"
                  />
                  <input
                    type="date"
                    value={prochaineActionDate}
                    onChange={(e) => setProchaineActionDate(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 text-sm outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={enregistrerProchaineAction}
                    className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-700"
                  >
                    Enregistrer
                  </button>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="mb-4 text-sm font-semibold text-slate-900">Historique complet</p>

              <div className="mb-4 flex items-center gap-2">
                <select
                  value={typeActivite}
                  onChange={(e) => setTypeActivite(e.target.value)}
                  className="rounded-lg border border-slate-200 bg-slate-50/60 px-2.5 py-2 text-xs font-medium text-slate-600 outline-none focus:border-blue-500"
                >
                  {TYPES_ACTIVITE.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={nouvelleActivite}
                  onChange={(e) => setNouvelleActivite(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && envoyerActivite()}
                  placeholder="Ajouter une note ou logger une activité..."
                  className="flex-1 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 text-sm outline-none focus:border-blue-500"
                />
                <button
                  onClick={envoyerActivite}
                  disabled={envoiEnCours || !nouvelleActivite.trim()}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:opacity-40"
                >
                  {envoiEnCours ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </button>
              </div>

              {interactions.length === 0 ? (
                <p className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-400">
                  Aucune activité enregistrée pour ce prospect.
                </p>
              ) : (
                <div className="space-y-3">
                  {interactions.map((i) => (
                    <div key={i.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
                      <div className="flex items-center justify-between">
                        <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                          {i.type}
                        </span>
                        <span className="text-xs text-slate-400">
                          {new Date(i.date.replace(" ", "T") + "Z").toLocaleString("fr-FR")}
                        </span>
                      </div>
                      <p className="mt-1.5 text-sm text-slate-700">{i.contenu}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            {/* Coordonnées */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="mb-3 text-sm font-semibold text-slate-900">Coordonnées</p>
              <div className="space-y-2.5 text-sm">
                {prospect.contact_nom && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <Users className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    {prospect.contact_nom}
                    {prospect.contact_fonction ? ` · ${prospect.contact_fonction}` : ""}
                  </div>
                )}
                {prospect.telephone && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <Phone className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    {prospect.telephone}
                  </div>
                )}
                {prospect.email && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <Mail className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    {prospect.email}
                  </div>
                )}
                {prospect.site_web && (
                  <a href={prospect.site_web} target="_blank" className="flex items-center gap-2 text-blue-600 hover:underline">
                    <Globe className="h-3.5 w-3.5 shrink-0" />
                    Site web
                  </a>
                )}
                {prospect.linkedin && (
                  <a href={prospect.linkedin} target="_blank" className="flex items-center gap-2 text-blue-600 hover:underline">
                    <LinkedinIcon className="h-3.5 w-3.5 shrink-0" />
                    LinkedIn
                  </a>
                )}
                {prospect.facebook && (
                  <a href={prospect.facebook} target="_blank" className="flex items-center gap-2 text-blue-600 hover:underline">
                    <FacebookIcon className="h-3.5 w-3.5 shrink-0" />
                    Facebook
                  </a>
                )}
                {prospect.adresse && (
                  <div className="flex items-start gap-2 text-slate-500">
                    <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span className="text-xs">{prospect.adresse}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Profil */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="mb-3 text-sm font-semibold text-slate-900">Profil</p>
              <div className="space-y-2 text-sm text-slate-600">
                {prospect.effectif && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Effectif</span>
                    <span className="font-medium">{prospect.effectif}</span>
                  </div>
                )}
                {prospect.reseau_groupe === 1 && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Réseau</span>
                    <span className="font-medium">{prospect.reseau_nom ?? "Oui"}</span>
                  </div>
                )}
                {prospect.score_completude != null && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Complétude</span>
                    <span className="font-medium">{Math.round(prospect.score_completude)}%</span>
                  </div>
                )}
              </div>

              {scoreDetail && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <p className="mb-2 text-xs font-medium text-slate-500">Détail du score</p>
                  <div className="space-y-1.5">
                    {Object.entries(scoreDetail).map(([cle, val]) => (
                      <div key={cle} className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">{cle}</span>
                        <span className="font-semibold text-slate-700">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
