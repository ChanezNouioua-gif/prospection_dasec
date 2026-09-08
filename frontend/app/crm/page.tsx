"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Search,
  Radar,
  Building2,
  Megaphone,
  History,
  Settings,
  LogOut,
  Bell,
  UserSearch,
  Plus,
  ShieldCheck,
  ArrowRight,
  Users,
  Activity,
  Sparkles,
  Phone,
  Mail,
  CalendarClock,
  CircleAlert,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Filter,
  StickyNote,
  TrendingUp,
  TrendingDown,
  MapPin,
} from "lucide-react";

import * as XLSX from "xlsx";

/* ---------------------------------------------------------------- */
/* Types                                                             */
/* ---------------------------------------------------------------- */

const STATUTS_PIPELINE = [
  { code: "NOUVEAU", label: "Nouveaux" },
  { code: "A_CONTACTER", label: "À contacter" },
  { code: "CONTACTE", label: "Contactés" },
  { code: "ECHANGE", label: "Échange" },
  { code: "RDV", label: "RDV" },
  { code: "PROPOSITION", label: "Proposition" },
  { code: "GAGNE", label: "Gagné" },
  { code: "PERDU", label: "Perdu" },
] as const;

type TypeTache = "appel" | "email" | "relance" | "rdv";
type TypeActivite = "appel" | "email" | "rdv" | "note" | "statut";

interface Contact {
  nom: string;
  fonction: string | null;
  telephone: string | null;
  email: string | null;
}

interface Opportunite {
  id: number;
  nom: string;
  secteur: string | null;
  sous_secteur: string | null;
  wilaya: string | null;
  score_dasec: number | null;
  score_raison: string | null;
  statut: string | null;
  commercial: string | null;
  contacts: Contact[] | null;
  prochaine_action: string | null; // date ISO
  contact_nom: string | null;
  contact_fonction: string | null;
  jamais_contacte: boolean; // NOUVEAU : nécessaire pour le filtre "jamais contactés"
}

interface Tache {
  id: number;
  prospect_id: number;
  prospect_nom: string;
  type: TypeTache;
  description: string;
  date_echeance: string; // ISO
  en_retard: boolean;
  fait: boolean; // NOUVEAU : reflète l'état persisté côté backend
}

interface ProspectPerdu {
  id: number;
  nom: string;
  motif: string | null;
  date: string | null; // was `string` — backend can send null
}

interface Activite {
  id: number;
  prospect_id: number;
  prospect_nom: string;
  type: TypeActivite;
  description: string;
  date: string | null; // same issue
  auteur: string | null;
}

interface MembreEquipe {
  nom: string;
  nb_prospects: number;
  nb_gagnes: number;
}

interface ResumeCrm {
  pipeline: { statut: string; total: number }[];
  total_crm: number;
  opportunites: Opportunite[];
  jamais_contactes: number;
  ajoutes_ce_mois: number;
  taches_du_jour: Tache[];
  taches_en_retard: number;
  prospects_sans_action: number;
  activites_recentes: Activite[];
  perdus_recents: ProspectPerdu[];
  equipe: MembreEquipe[];
}

/* ---------------------------------------------------------------- */
/* Page                                                               */
/* ---------------------------------------------------------------- */

export default function CrmPage() {
  const searchParams = useSearchParams();

  const [resume, setResume] = useState<ResumeCrm | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  const [recherche, setRecherche] = useState("");
  const [filtreSecteur, setFiltreSecteur] = useState<string>("TOUS");
  const [filtreStatut, setFiltreStatut] = useState<string>("TOUS");

  const tachesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function charger() {
      setLoading(true);
      setErreur(null);
      try {
        const res = await fetch("http://localhost:8000/crm/resume", {
          credentials: "include",
          cache: "no-store",
        });
        if (!res.ok) throw new Error("Erreur lors du chargement du CRM");
        const data: ResumeCrm = await res.json();
          setResume({
          ...data,
          taches_du_jour: data.taches_du_jour ?? [],
          activites_recentes: data.activites_recentes ?? [],
          equipe: data.equipe ?? [],
          perdus_recents: data.perdus_recents ?? [],
          prospects_sans_action: data.prospects_sans_action ?? 0,
          taches_en_retard: data.taches_en_retard ?? 0,
       });
      } catch (e) {
        setErreur(e instanceof Error ? e.message : "Erreur inconnue");
      } finally {
        setLoading(false);
      }
    }
    charger();
  }, []);

  // Synchronise les filtres avec les paramètres d'URL (liens venant des
  // cartes "Ce qui nécessite votre attention" et du pipeline). Avant ce
  // correctif, ces liens naviguaient vers /crm?... sans que la page ne
  // lise jamais ces paramètres : les clics ne filtraient rien.
  useEffect(() => {
    const statut = searchParams.get("statut");
    if (statut) setFiltreStatut(statut);

    const filtre = searchParams.get("filtre");
    if (filtre === "taches_retard") {
      // "Tâches en retard" est une propriété des tâches, pas des opportunités :
      // filtrer la liste d'opportunités par ça n'aurait pas de sens. On amène
      // plutôt l'utilisateur directement sur la section concernée.
      tachesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [searchParams]);

  const filtreSpecial = searchParams.get("filtre");

  const secteurs = useMemo(() => {
    if (!resume) return [];
    const s = new Set(resume.opportunites.map((o) => o.secteur).filter(Boolean) as string[]);
    return Array.from(s);
  }, [resume]);

  const opportunitesFiltrees = useMemo(() => {
    if (!resume) return [];
    return resume.opportunites.filter((o) => {
      const matchRecherche =
        recherche.trim() === "" ||
        o.nom.toLowerCase().includes(recherche.toLowerCase()) ||
        (o.wilaya ?? "").toLowerCase().includes(recherche.toLowerCase());
      const matchSecteur = filtreSecteur === "TOUS" || o.secteur === filtreSecteur;
      const matchStatut = filtreStatut === "TOUS" || o.statut === filtreStatut;
      const matchSpecial =
        filtreSpecial === "sans_action"
          ? !o.prochaine_action
          : filtreSpecial === "jamais_contactes"
          ? o.jamais_contacte
          : true; // "taches_retard" ne filtre pas cette liste (cf. useEffect ci-dessus)
      return matchRecherche && matchSecteur && matchStatut && matchSpecial;
    });
  }, [resume, recherche, filtreSecteur, filtreStatut, filtreSpecial]);
  

  function exporterExcel() {
    const feuille = XLSX.utils.json_to_sheet(opportunitesFiltrees);
    const classeur = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(classeur, feuille, "Prospects");
    const date = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(classeur, `prospects_crm_${date}.xlsx`);
  }

  return (
    <main className="flex min-h-screen bg-slate-50/60 text-slate-900">
      <Sidebar />
      <div className="flex-1">
        <TopBar recherche={recherche} onRechercheChange={setRecherche} onExporter={exporterExcel} />
        <div className="mx-auto max-w-[1500px] px-6 pb-12 pt-6">
          <PageHeader />

          {erreur && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm font-medium text-rose-600">
              {erreur} — vérifie que le backend tourne bien sur localhost:8000.
            </div>
          )}

          {!erreur && loading && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
              Chargement du pilotage commercial...
            </div>
          )}

          {!erreur && !loading && resume && (
            <>
              <AttentionSection resume={resume} />

              <div className="mt-6 grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
                <div ref={tachesRef}>
                  <TachesDuJourSection
                    taches={resume.taches_du_jour}
                    onTacheMiseAJour={(id, fait) => {
                      setResume((prev) =>
                        prev
                          ? {
                              ...prev,
                              taches_du_jour: prev.taches_du_jour.map((t) =>
                                t.id === id ? { ...t, fait } : t
                              ),
                            }
                          : prev
                      );
                    }}
                  />
                </div>
                <ActiviteSection activites={resume.activites_recentes} />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
                <OpportunitesSection
                  opportunites={opportunitesFiltrees}
                  totalNonFiltre={resume.opportunites.length}
                  secteurs={secteurs}
                  filtreSecteur={filtreSecteur}
                  onFiltreSecteurChange={setFiltreSecteur}
                  filtreStatut={filtreStatut}
                  onFiltreStatutChange={setFiltreStatut}
                />
                <PipelineSection pipeline={resume.pipeline} total={resume.total_crm} />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1fr_360px]">
                <EquipeSection equipe={resume.equipe} />
                <PerdusSection perdus={resume.perdus_recents} />
                <InsightsSection resume={resume} />
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

/* ---------------------------------------------------------------- */
/* Sidebar / TopBar                                                   */
/* ---------------------------------------------------------------- */
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";

/* ---------------------------------------------------------------- */
/* Header de page                                                    */
/* ---------------------------------------------------------------- */

function PageHeader() {
  const [aujourdhui, setAujourdhui] = useState<string | null>(null);

  useEffect(() => {
    setAujourdhui(
      new Date().toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    );
  }, []);

  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Pilotage commercial</h1>
        <p className="mt-1 text-sm text-slate-500">
          Concentrez votre effort sur les bonnes opportunités et faites progresser votre pipeline.
        </p>
      </div>
      <span className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-500">
        {aujourdhui ?? "—"}
      </span>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Ce qui nécessite votre attention                                  */
/* ---------------------------------------------------------------- */

function AttentionSection({ resume }: { resume: ResumeCrm }) {
  return (
    <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <CircleAlert className="h-4 w-4 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ce qui nécessite votre attention
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <AttentionCard
          valeur={resume.jamais_contactes}
          label="Prospects jamais contactés"
          couleur="rose"
          href="/crm?filtre=jamais_contactes"
        />
        <AttentionCard
          valeur={resume.prospects_sans_action}
          label="Prospects sans prochaine action"
          couleur="amber"
          href="/crm?filtre=sans_action"
        />
        <AttentionCard
          valeur={resume.taches_en_retard}
          label="Tâches en retard"
          couleur="rose"
          href="/crm?filtre=taches_retard"
        />
        <AttentionCard
          valeur={resume.ajoutes_ce_mois}
          label="Nouveaux prospects ce mois-ci"
          couleur="blue"
          href="/crm?statut=NOUVEAU"
        />
      </div>
    </div>
  );
}

function AttentionCard({
  valeur,
  label,
  couleur,
  href,
}: {
  valeur: number;
  label: string;
  couleur: "rose" | "amber" | "blue";
  href: string;
}) {
  const styles = {
    rose: "bg-rose-50 text-rose-600",
    amber: "bg-amber-50 text-amber-600",
    blue: "bg-blue-50 text-blue-600",
  }[couleur];

  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/60 p-4 transition hover:border-slate-200 hover:bg-white hover:shadow-sm"
    >
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg font-bold ${styles}`}>
        {valeur}
      </div>
      <p className="text-sm font-medium leading-snug text-slate-700">{label}</p>
    </Link>
  );
}

/* ---------------------------------------------------------------- */
/* À faire aujourd'hui — tâches & relances                           */
/* ---------------------------------------------------------------- */

const ICONE_TACHE: Record<TypeTache, typeof Phone> = {
  appel: Phone,
  email: Mail,
  relance: CalendarClock,
  rdv: Users,
};

const LABEL_TACHE: Record<TypeTache, string> = {
  appel: "Appel",
  email: "Email",
  relance: "Relance",
  rdv: "RDV",
};

function TachesDuJourSection({
  taches,
  onTacheMiseAJour,
}: {
  taches: Tache[];
  onTacheMiseAJour: (id: number, fait: boolean) => void;
}) {
  // "enVol" évite de renvoyer deux requêtes si l'utilisateur double-clique
  // pendant que la première requête est encore en cours.
  const [enVol, setEnVol] = useState<Set<number>>(new Set());

  const marquerFait = async (id: number) => {
    if (enVol.has(id)) return;
    setEnVol((prev) => new Set(prev).add(id));

    // Mise à jour optimiste : l'UI réagit immédiatement, on annule si l'appel échoue.
    onTacheMiseAJour(id, true);

    try {
      const res = await fetch(`http://localhost:8000/crm/taches/${id}/complete`, {
        method: "PATCH",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Échec de la mise à jour");
    } catch {
      onTacheMiseAJour(id, false); // rollback si le backend refuse/échoue
    } finally {
      setEnVol((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const tachesTriees = [...(taches ?? [])].sort((a, b) => {
    if (a.en_retard !== b.en_retard) return a.en_retard ? -1 : 1;
    return new Date(a.date_echeance).getTime() - new Date(b.date_echeance).getTime();
  });

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-slate-400" />
          <p className="text-sm font-semibold text-slate-900">À faire aujourd&apos;hui</p>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
          {taches.length} tâche{taches.length > 1 ? "s" : ""}
        </span>
      </div>

      {tachesTriees.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 p-8 text-center">
          <CheckCircle2 className="mx-auto h-6 w-6 text-emerald-400" />
          <p className="mt-2 text-sm font-medium text-slate-500">Rien en attente pour le moment</p>
          <p className="mt-1 text-xs text-slate-400">
            Les relances et RDV à venir apparaîtront automatiquement ici.
          </p>
        </div>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto pr-1">
          {tachesTriees.map((t) => {
            const Icone = ICONE_TACHE[t.type];
            return (
              <div
                key={t.id}
                className={`flex items-center gap-3 rounded-xl border p-3 transition ${
                  t.fait
                    ? "border-slate-100 bg-slate-50/40 opacity-50"
                    : t.en_retard
                    ? "border-rose-100 bg-rose-50/50"
                    : "border-slate-100 bg-slate-50/60"
                }`}
              >
                <button
                  onClick={() => marquerFait(t.id)}
                  disabled={t.fait || enVol.has(t.id)}
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition ${
                    t.fait
                      ? "bg-emerald-100 text-emerald-600"
                      : t.en_retard
                      ? "bg-rose-100 text-rose-600"
                      : "bg-blue-50 text-blue-600"
                  }`}
                  title="Marquer comme fait"
                >
                  <Icone className="h-4 w-4" />
                </button>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-semibold text-slate-800 ${t.fait ? "line-through" : ""}`}>
                    {t.prospect_nom}
                  </p>
                  <p className="truncate text-xs text-slate-400">
                    {LABEL_TACHE[t.type]} · {t.description}
                  </p>
                </div>
                <div className="text-right">
                  {t.en_retard && !t.fait && (
                    <span className="mb-0.5 inline-block rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-600">
                      En retard
                    </span>
                  )}
                  <p className="text-xs text-slate-400">
                    {new Date(t.date_echeance).toLocaleDateString("fr-FR", {
                      day: "numeric",
                      month: "short",
                    })}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Activité récente                                                  */
/* ---------------------------------------------------------------- */

const ICONE_ACTIVITE: Record<TypeActivite, typeof Phone> = {
  appel: Phone,
  email: Mail,
  rdv: Users,
  note: StickyNote,
  statut: ArrowRight,
};

function tempsRelatif(dateIso: string | null | undefined): string {
  if (!dateIso) return "date inconnue";

  // SQLite renvoie "YYYY-MM-DD HH:MM:SS" en UTC, sans indicateur de zone —
  // JS l'interprète par défaut comme heure locale, d'où le décalage.
  // On force l'interprétation UTC en remplaçant l'espace par "T" + "Z".
  const dateUtc = new Date(dateIso.replace(" ", "T") + "Z");
  if (Number.isNaN(dateUtc.getTime())) return "date inconnue";

  const diffMs = Date.now() - dateUtc.getTime();
  const diffH = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffH < 1) return "à l'instant";
  if (diffH < 24) return `il y a ${diffH} h`;
  const diffJ = Math.floor(diffH / 24);
  if (diffJ === 1) return "hier";
  return `il y a ${diffJ} j`;
}

function ActiviteSection({ activites }: { activites: Activite[] }) {
  return (
    <div className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100 xl:h-[470px]">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <p className="text-sm font-semibold text-slate-900">Activité récente</p>
        </div>
        {activites.length > 0 && (
          <Link href="/historique" className="text-xs font-medium text-blue-600 hover:underline">
            Voir tout
          </Link>
        )}
      </div>

      {activites.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <Activity className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-500">Aucune activité enregistrée</p>
          <p className="mt-1 max-w-[260px] text-xs text-slate-400">
            Chaque appel, email ou RDV loggé sur une fiche prospect apparaîtra dans ce fil.
          </p>
        </div>
      ) : (
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {activites.map((a) => {
            const Icone = ICONE_ACTIVITE[a.type];
            return (
              <div key={a.id} className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
                  <Icone className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1 border-b border-slate-50 pb-4 last:border-0 last:pb-0">
                  <p className="text-sm text-slate-700">
                    <span className="font-semibold text-slate-900">{a.prospect_nom}</span> — {a.description}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {tempsRelatif(a.date)}
                    {a.auteur ? ` · ${a.auteur}` : ""}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Opportunités — avec filtres, score expliqué, multi-contacts       */
/* ---------------------------------------------------------------- */

function OpportunitesSection({
  opportunites,
  totalNonFiltre,
  secteurs,
  filtreSecteur,
  onFiltreSecteurChange,
  filtreStatut,
  onFiltreStatutChange,
}: {
  opportunites: Opportunite[];
  totalNonFiltre: number;
  secteurs: string[];
  filtreSecteur: string;
  onFiltreSecteurChange: (v: string) => void;
  filtreStatut: string;
  onFiltreStatutChange: (v: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-900">
          Opportunités à ne pas manquer
          {totalNonFiltre > 0 && (
            <span className="ml-2 text-xs font-normal text-slate-400">
              {opportunites.length}/{totalNonFiltre}
            </span>
          )}
        </p>
        <Link href="/dashboard" className="text-xs font-medium text-blue-600 hover:underline">
          Voir dans Prospection
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Filter className="h-3.5 w-3.5 text-slate-400" />
        <select
          value={filtreSecteur}
          onChange={(e) => onFiltreSecteurChange(e.target.value)}
          className="rounded-lg border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs font-medium text-slate-600 outline-none focus:border-blue-500"
        >
          <option value="TOUS">Tous les secteurs</option>
          {secteurs.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={filtreStatut}
          onChange={(e) => onFiltreStatutChange(e.target.value)}
          className="rounded-lg border border-slate-200 bg-slate-50/60 px-2.5 py-1.5 text-xs font-medium text-slate-600 outline-none focus:border-blue-500"
        >
          <option value="TOUS">Tous les statuts</option>
          {STATUTS_PIPELINE.map((s) => (
            <option key={s.code} value={s.code}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {opportunites.length === 0 ? (
        <EtatVideOpportunites />
      ) : (
        <div className="space-y-2">
          {opportunites.map((o) => (
            <OpportuniteCard key={o.id} o={o} />
          ))}
        </div>
      )}
    </div>
  );
}

function OpportuniteCard({ o }: { o: Opportunite }) {
  const nbContacts = o.contacts?.length ?? 0;
  const score = Math.round(o.score_dasec ?? 0);
  const scoreCouleur =
    score >= 80 ? "text-emerald-600 bg-emerald-50" : score >= 50 ? "text-amber-600 bg-amber-50" : "text-slate-500 bg-slate-50";

  return (
    <Link
      href={`/crm/prospect/${o.id}`}
      className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/60 p-3 transition hover:border-blue-200 hover:bg-white hover:shadow-sm"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <Building2 className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-semibold text-slate-800">{o.nom}</p>
            {nbContacts > 1 && (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
                <Users className="h-2.5 w-2.5" />
                {nbContacts}
              </span>
            )}
          </div>
          <p className="flex items-center gap-1 truncate text-xs text-slate-400">
            {o.sous_secteur ?? "—"}
            {o.wilaya && (
              <>
                <span className="text-slate-300">·</span>
                <MapPin className="h-2.5 w-2.5" />
                {o.wilaya}
              </>
            )}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-4">
        <div className="text-right">
          <p className="text-xs text-slate-400">
            {o.contact_nom ? `${o.contact_nom}${o.contact_fonction ? ` · ${o.contact_fonction}` : ""}` : "Contact non renseigné"}
          </p>
          {o.commercial && <p className="text-[10px] text-slate-300">Suivi par {o.commercial}</p>}
        </div>
        <div
          className={`flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded-xl text-sm font-bold ${scoreCouleur}`}
          title={o.score_raison ?? "Score DASEC"}
        >
          {score}
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
      </div>
    </Link>
  );
}

function EtatVideOpportunites() {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
      <p className="text-sm font-medium text-slate-500">Aucun prospect ne correspond à ces filtres</p>
      <p className="mt-1 text-xs text-slate-400">
        Ajustez les filtres ou ajoutez des prospects depuis la page Prospection.
      </p>
      <Link
        href="/dashboard"
        className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:underline"
      >
        Aller à la Prospection
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Pipeline commercial — barres cliquables + taux de conversion      */
/* ---------------------------------------------------------------- */

function PipelineSection({
  pipeline,
  total,
}: {
  pipeline: { statut: string; total: number }[];
  total: number;
}) {
  const parStatut = Object.fromEntries(pipeline.map((p) => [p.statut, p.total]));
  const gagnes = parStatut["GAGNE"] ?? 0;
  const tauxConversion = total > 0 ? Math.round((gagnes / total) * 100) : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900">Pipeline commercial</p>
        <Link href="/crm/pipeline" className="text-xs font-medium text-blue-600 hover:underline">
          Vue Kanban
        </Link>
      </div>

      {total === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">
          Aucun prospect dans le CRM pour l&apos;instant.
        </p>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between rounded-xl bg-emerald-50 px-4 py-3">
            <span className="text-xs font-medium text-emerald-700">Taux de conversion global</span>
            <span className="text-lg font-bold text-emerald-600">{tauxConversion}%</span>
          </div>
          <div className="space-y-3">
            {STATUTS_PIPELINE.map(({ code, label }) => {
              const n = parStatut[code] ?? 0;
              const pct = total > 0 ? Math.round((n / total) * 100) : 0;
              return (
                <Link
                  key={code}
                  href={`/crm?statut=${code}`}
                  className="block rounded-lg transition hover:bg-slate-50"
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-600">{label}</span>
                    <span className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{n}</span>
                      <span className="w-10 text-right text-xs text-slate-400">{pct}%</span>
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${
                        code === "GAGNE" ? "bg-emerald-500" : code === "PERDU" ? "bg-rose-400" : "bg-blue-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Équipe                                                             */
/* ---------------------------------------------------------------- */

function EquipeSection({ equipe }: { equipe: MembreEquipe[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900">Répartition de l&apos;équipe</p>
      </div>

      {equipe.length <= 1 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <Users className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-500">Un seul commercial pour l&apos;instant</p>
          <p className="mt-1 max-w-[220px] text-xs text-slate-400">
            Ce module s&apos;activera automatiquement quand d&apos;autres membres rejoindront la plateforme.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {equipe.map((m) => {
            const taux = m.nb_prospects > 0 ? Math.round((m.nb_gagnes / m.nb_prospects) * 100) : 0;
            return (
              <div key={m.nom} className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                  {m.nom.charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{m.nom}</span>
                    <span className="text-xs text-slate-400">
                      {m.nb_prospects} prospects · {taux}%
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${taux}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Prospects perdus récemment — avec motif                           */
/* ---------------------------------------------------------------- */

function PerdusSection({ perdus }: { perdus: ProspectPerdu[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <XCircle className="h-4 w-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-900">Perdus récemment</p>
      </div>

      {perdus.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <XCircle className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-500">Aucun prospect perdu récemment</p>
          <p className="mt-1 max-w-[220px] text-xs text-slate-400">
            Le motif de perte saisi sur chaque fiche apparaîtra ici pour analyser les causes.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {perdus.map((p) => (
            <div key={p.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
              <p className="text-sm font-semibold text-slate-800">{p.nom}</p>
              <p className="mt-0.5 text-xs text-slate-400">
                {p.motif ?? "Motif non renseigné"} · {tempsRelatif(p.date)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Insights commerciaux — calculés à partir des données disponibles  */
/* ---------------------------------------------------------------- */

function InsightsSection({ resume }: { resume: ResumeCrm }) {
  const total = resume.total_crm;
  const parStatut = Object.fromEntries(resume.pipeline.map((p) => [p.statut, p.total]));
  const gagnes = parStatut["GAGNE"] ?? 0;
  const perdus = parStatut["PERDU"] ?? 0;
  const enCours = total - gagnes - perdus;

  const assezDeDonnees = total >= 5;

  const meilleurSecteur = useMemo(() => {
    const scoresParSecteur: Record<string, { somme: number; n: number }> = {};
    resume.opportunites.forEach((o) => {
      if (!o.secteur || o.score_dasec == null) return;
      if (!scoresParSecteur[o.secteur]) scoresParSecteur[o.secteur] = { somme: 0, n: 0 };
      scoresParSecteur[o.secteur].somme += o.score_dasec;
      scoresParSecteur[o.secteur].n += 1;
    });

    return Object.entries(scoresParSecteur).reduce<{ secteur: string; moyenne: number } | null>(
      (meilleur, [secteur, { somme, n }]) => {
        const moyenne = somme / n;
        return !meilleur || moyenne > meilleur.moyenne ? { secteur, moyenne } : meilleur;
      },
      null
    );
  }, [resume.opportunites]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-900">Insights commerciaux</p>
      </div>

      {!assezDeDonnees ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-500">Pas encore assez de données</p>
          <p className="mt-1 max-w-[260px] text-xs text-slate-400">
            Les tendances apparaîtront dès qu&apos;au moins 5 prospects seront suivis dans le CRM.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3 rounded-xl bg-slate-50/60 p-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <Activity className="h-4 w-4" />
            </div>
            <p className="text-xs text-slate-600">
              <span className="font-semibold text-slate-800">{enCours}</span> prospects actifs en cours de traitement
            </p>
          </div>

          {meilleurSecteur && (
            <div className="flex items-center gap-3 rounded-xl bg-slate-50/60 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                <TrendingUp className="h-4 w-4" />
              </div>
              <p className="text-xs text-slate-600">
                <span className="font-semibold text-slate-800">{meilleurSecteur.secteur}</span> est le secteur
                le mieux scoré (moy. {meilleurSecteur.moyenne.toFixed(1)}/100)
              </p>
            </div>
          )}

          {perdus > 0 && (
            <div className="flex items-center gap-3 rounded-xl bg-slate-50/60 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-rose-50 text-rose-600">
                <TrendingDown className="h-4 w-4" />
              </div>
              <p className="text-xs text-slate-600">
                <span className="font-semibold text-slate-800">{perdus}</span> prospects perdus —
                consultez leurs motifs pour ajuster l&apos;approche
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
