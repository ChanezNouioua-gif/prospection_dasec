"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Search,
  Radar,
  Building2,
  Megaphone,
  History,
  Settings,
  LogOut,
  ShieldCheck,
  UserSearch,
  User,
  Mail,
  Phone,
  ChevronDown,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";

function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

/* ---------------------------------------------------------------- */
/* Types                                                             */
/* ---------------------------------------------------------------- */

interface Raison {
  label: string;
  ok: boolean;
}

interface Confiance {
  label: "Élevée" | "Moyenne" | "Faible" | "Aucun contact";
  score: number;
  raisons: Raison[];
}

interface Decideur {
  id: number;
  nom: string;
  secteur: string;
  sous_secteur: string | null;
  wilaya_name: string | null;
  contact_nom: string | null;
  contact_fonction: string | null;
  email: string | null;
  telephone: string | null;
  linkedin: string | null;
  site_web: string | null;
  confiance: Confiance;
}

interface ResumeDecideurs {
  analyses: number;
  decideurs_trouves: number;
  a_verifier: number;
  a_retraiter: number | null;
}

const CONFIANCE_STYLE: Record<Confiance["label"], string> = {
  Élevée: "bg-emerald-50 text-emerald-700",
  Moyenne: "bg-amber-50 text-amber-700",
  Faible: "bg-slate-100 text-slate-500",
  "Aucun contact": "bg-rose-50 text-rose-600",
};

/* ---------------------------------------------------------------- */
/* Page                                                               */
/* ---------------------------------------------------------------- */

export default function DecideursPage() {
  const [resume, setResume] = useState<ResumeDecideurs | null>(null);
  const [decideurs, setDecideurs] = useState<Decideur[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  const [filtreWilaya, setFiltreWilaya] = useState("Tous");
  const [filtreSecteur, setFiltreSecteur] = useState("Tous");
  const [filtreConfiance, setFiltreConfiance] = useState("Tous");

  useEffect(() => {
    async function charger() {
      setLoading(true);
      setErreur(null);
      try {
        const params = new URLSearchParams({ page: String(page), limite: "20" });
        if (filtreWilaya !== "Tous") params.set("wilaya", filtreWilaya);
        if (filtreSecteur !== "Tous") params.set("secteur", filtreSecteur);
        if (filtreConfiance !== "Tous") params.set("confiance", filtreConfiance);

        const [resListe, resResume] = await Promise.all([
          fetch(`http://localhost:8000/decideurs?${params}`, { credentials: "include", cache: "no-store" }),
          fetch("http://localhost:8000/decideurs/resume", { credentials: "include", cache: "no-store" }),
        ]);
        if (!resListe.ok || !resResume.ok) throw new Error("Erreur lors du chargement des décideurs");

        const dataListe = await resListe.json();
        const dataResume: ResumeDecideurs = await resResume.json();

        setDecideurs(dataListe.items);
        setTotal(dataListe.total);
        setResume(dataResume);
        setSelectedId((prev) => prev ?? dataListe.items[0]?.id ?? null);
      } catch (e) {
        setErreur(e instanceof Error ? e.message : "Erreur inconnue");
      } finally {
        setLoading(false);
      }
    }
    charger();
  }, [page, filtreWilaya, filtreSecteur, filtreConfiance]);

  const selected = useMemo(
    () => decideurs.find((d) => d.id === selectedId) ?? decideurs[0],
    [decideurs, selectedId]
  );

  return (
    <main className="flex min-h-screen bg-slate-50/60 text-slate-900">
      <Sidebar />
      <div className="flex-1">
        <TopBar />
        <div className="mx-auto max-w-[1500px] px-6 pb-12 pt-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Décideurs</h1>
            <p className="mt-1 text-sm text-slate-500">
              Identifiez et vérifiez les bons interlocuteurs pour vos prospects.
            </p>
          </div>

          {resume && <StatsBar resume={resume} />}

          <FiltersBar
            wilaya={filtreWilaya} setWilaya={setFiltreWilaya}
            secteur={filtreSecteur} setSecteur={setFiltreSecteur}
            confiance={filtreConfiance} setConfiance={setFiltreConfiance}
          />

          {erreur && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm font-medium text-rose-600">
              {erreur} — vérifie que le backend tourne bien sur localhost:8000.
            </div>
          )}

          {!erreur && loading && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
              Chargement des décideurs...
            </div>
          )}

          {!erreur && !loading && decideurs.length > 0 && selected && (
            <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_420px]">
              <ListeDecideurs
                decideurs={decideurs}
                total={total}
                selectedId={selected.id}
                onSelect={setSelectedId}
                page={page}
                setPage={setPage}
              />
              <DetailDecideur decideur={selected} />
            </div>
          )}

          {!erreur && !loading && decideurs.length === 0 && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
              Aucun prospect ne correspond à ces filtres.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

/* ---------------------------------------------------------------- */
/* Sidebar / TopBar                                                   */
/* ---------------------------------------------------------------- */

function Sidebar() {
  const items = [
    { label: "Prospection", icon: Radar, href: "/dashboard", active: false },
    { label: "Décideurs", icon: UserSearch, href: "/decideurs", active: true },
    { label: "CRM", icon: Building2, href: "/crm", active: false },
    { label: "Campagnes", icon: Megaphone, href: "#", active: false },
    { label: "Historique", icon: History, href: "#", active: false },
    { label: "Paramètres", icon: Settings, href: "#", active: false },
  ];

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col justify-between border-r border-slate-200/70 bg-white px-4 py-6">
      <div>
        <div className="flex items-center gap-2.5 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <ShieldCheck className="h-4.5 w-4.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight text-slate-900">DASEC</p>
            <p className="text-[11px] text-slate-400">Prospect Intelligence</p>
          </div>
        </div>

        <nav className="mt-8 flex flex-col gap-1">
          {items.map(({ label, icon: Icon, href, active }) => (
            <Link
              key={label}
              href={href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex flex-col gap-1 border-t border-slate-100 pt-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
            H
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Hanane</p>
            <p className="text-[11px] text-slate-400">Commerciale</p>
          </div>
        </div>
        <button className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-slate-50 hover:text-slate-700">
          <LogOut className="h-4 w-4" />
          Déconnexion
        </button>
      </div>
    </aside>
  );
}

function TopBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-[1500px] items-center gap-4 px-6">
        <div className="relative flex-1 max-w-xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Rechercher un prospect ou un décideur..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-11 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
      </div>
    </header>
  );
}

/* ---------------------------------------------------------------- */
/* Stats                                                              */
/* ---------------------------------------------------------------- */

function StatsBar({ resume }: { resume: ResumeDecideurs }) {
  return (
    <div className="mt-6 grid grid-cols-2 gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100 sm:grid-cols-4">
      <Stat valeur={resume.analyses} label="Prospects analysés" />
      <Stat valeur={resume.decideurs_trouves} label="Décideurs trouvés" />
      <Stat valeur={resume.a_verifier} label="À vérifier" />
      {resume.a_retraiter === null ? (
        <div className="flex flex-col justify-center rounded-xl border border-dashed border-slate-200 px-3 py-2">
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500 w-fit">
            Bientôt disponible
          </span>
          <p className="mt-1 text-xs text-slate-400">À retraiter — file d&apos;attente pas encore active</p>
        </div>
      ) : (
        <Stat valeur={resume.a_retraiter} label="À retraiter" />
      )}
    </div>
  );
}

function Stat({ valeur, label }: { valeur: number; label: string }) {
  return (
    <div>
      <p className="text-2xl font-bold text-slate-900">{valeur.toLocaleString("fr-FR")}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Filters                                                            */
/* ---------------------------------------------------------------- */

function FiltersBar({
  wilaya, setWilaya,
  secteur, setSecteur,
  confiance, setConfiance,
}: {
  wilaya: string; setWilaya: (v: string) => void;
  secteur: string; setSecteur: (v: string) => void;
  confiance: string; setConfiance: (v: string) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <SimpleSelect value={wilaya} onChange={setWilaya} label="Wilaya" options={["Tous"]} />
      <SimpleSelect value={secteur} onChange={setSecteur} label="Secteur" options={["Tous", "santé", "assurance", "juridique", "industrie", "étatique"]} />
      <SimpleSelect
        value={confiance}
        onChange={setConfiance}
        label="Confiance"
        options={["Tous", "Élevée", "Moyenne", "Faible", "Aucun contact"]}
      />
      {(wilaya !== "Tous" || secteur !== "Tous" || confiance !== "Tous") && (
        <button
          onClick={() => { setWilaya("Tous"); setSecteur("Tous"); setConfiance("Tous"); }}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Réinitialiser
        </button>
      )}
    </div>
  );
}

function SimpleSelect({
  value, onChange, label, options,
}: {
  value: string; onChange: (v: string) => void; label: string; options: string[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-700 transition hover:border-slate-300"
      >
        <span className="text-xs text-slate-400">{label}:</span>
        {value}
        <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 min-w-full overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false); }}
              className="block w-full whitespace-nowrap px-3.5 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Liste                                                              */
/* ---------------------------------------------------------------- */

function ListeDecideurs({
  decideurs, total, selectedId, onSelect, page, setPage,
}: {
  decideurs: Decideur[]; total: number; selectedId: number; onSelect: (id: number) => void;
  page: number; setPage: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <p className="mb-4 text-sm font-semibold text-slate-900">
        Décideurs identifiés <span className="font-normal text-slate-400">— {total} résultats</span>
      </p>

      <div className="space-y-2">
        {decideurs.map((d) => {
          const isSelected = d.id === selectedId;
          const aucunContact = d.confiance.label === "Aucun contact";
          return (
            <button
              key={d.id}
              onClick={() => onSelect(d.id)}
              className={`block w-full rounded-xl border p-4 text-left transition ${
                isSelected ? "border-blue-200 bg-blue-50/50" : "border-slate-100 bg-slate-50/60 hover:bg-white hover:shadow-sm"
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">{d.nom}</p>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${CONFIANCE_STYLE[d.confiance.label]}`}>
                  {d.confiance.label}
                </span>
              </div>

              {aucunContact ? (
                <p className="mt-1.5 text-xs text-slate-400">Aucun décideur identifié pour l&apos;instant.</p>
              ) : (
                <div className="mt-1.5 flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  <p className="text-xs text-slate-600">
                    {d.contact_nom}
                    {d.contact_fonction && <span className="text-slate-400"> · {d.contact_fonction}</span>}
                  </p>
                </div>
              )}

              <p className="mt-1 text-[11px] text-slate-400">
                {d.sous_secteur ?? d.secteur} {d.wilaya_name ? `· ${d.wilaya_name}` : ""}
              </p>
            </button>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-1 border-t border-slate-100 pt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-50 hover:text-slate-700 disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              onClick={() => setPage(n)}
              className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-medium transition ${
                page === n ? "bg-blue-600 text-white" : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              {n}
            </button>
          ))}
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-50 hover:text-slate-700 disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Détail                                                             */
/* ---------------------------------------------------------------- */

function DetailDecideur({ decideur }: { decideur: Decideur }) {
  const aucunContact = decideur.confiance.label === "Aucun contact";

  return (
    <div className="h-fit rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-100">
      {aucunContact ? (
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 text-rose-500">
            <XCircle className="h-6 w-6" />
          </div>
          <p className="mt-3 text-base font-semibold text-slate-900">{decideur.nom}</p>
          <p className="mt-1 text-sm text-slate-500">Aucun décideur identifié pour l&apos;instant.</p>
          <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-400">
            La file de retraitement automatique n&apos;est pas encore active — cette fonctionnalité
            arrive avec le prochain bloc du système d&apos;enrichissement.
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <User className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">{decideur.contact_nom}</h3>
              <p className="text-xs text-slate-400">{decideur.contact_fonction ?? "Fonction non renseignée"}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            {decideur.nom} {decideur.wilaya_name ? `· ${decideur.wilaya_name}` : ""}
          </p>

          {/* Confiance */}
          <div className="mt-5">
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-500">Confiance du contact</span>
              <span className={`rounded-full px-2 py-0.5 font-semibold ${CONFIANCE_STYLE[decideur.confiance.label]}`}>
                {decideur.confiance.label}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full ${
                  decideur.confiance.label === "Élevée" ? "bg-emerald-500" :
                  decideur.confiance.label === "Moyenne" ? "bg-amber-500" : "bg-slate-400"
                }`}
                style={{ width: `${decideur.confiance.score}%` }}
              />
            </div>

            <div className="mt-3 space-y-1.5">
              {decideur.confiance.raisons.map((r) => (
                <div key={r.label} className="flex items-center gap-2 text-xs">
                  {r.ok ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                  )}
                  <span className={r.ok ? "text-slate-700" : "text-slate-400"}>{r.label}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 text-xs">
                <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-dashed border-slate-300" />
                <span className="text-slate-400">
                  Fonction cohérente avec le secteur — non évalué pour l&apos;instant
                </span>
              </div>
            </div>
          </div>

          {/* Coordonnées */}
          <div className="mt-5 space-y-2 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-semibold text-slate-500">Coordonnées</p>
            <div className="flex items-center gap-2.5 text-sm text-slate-600">
              <Mail className="h-4 w-4 text-slate-400" />
              {decideur.email ?? "Non trouvé"}
            </div>
            <div className="flex items-center gap-2.5 text-sm text-slate-600">
              <Phone className="h-4 w-4 text-slate-400" />
              {decideur.telephone ?? "Non trouvé"}
            </div>
            <div className="flex items-center gap-2.5 text-sm text-slate-600">
              <LinkedinIcon className="h-4 w-4 text-slate-400" />
              {decideur.linkedin ? (
                <a href={decideur.linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  Voir le profil
                </a>
              ) : (
                "Non trouvé"
              )}
            </div>
          </div>

          <Link
            href="/dashboard"
            className="mt-5 block rounded-full border border-slate-200 py-2.5 text-center text-sm font-semibold text-slate-600 transition hover:border-slate-900 hover:text-slate-900"
          >
            Voir la fiche complète
          </Link>
        </>
      )}
    </div>
  );
}