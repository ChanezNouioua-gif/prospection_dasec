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
  Download,
  Plus,
  Bell,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  RotateCcw,
  UserSearch,
  X,
  MoreVertical,
  Phone,
  Mail,
  Globe2,
  User,
  ShieldCheck,
  ExternalLink,
  MapPin,

} from "lucide-react";
import { toEtablissement } from "@/lib/adapter";
import { ProspectsResponse } from "@/lib/types";


/* ---------------------------------------------------------------- */
/* LinkedIn — retiré de lucide-react (v1) et de simple-icons (v14)   */
/* pour raisons de marque, donc SVG maison                          */
/* ---------------------------------------------------------------- */

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


/* ---------------------------------------------------------------- */
/* Types                                                             */
/* ---------------------------------------------------------------- */

type Etablissement = ReturnType<typeof toEtablissement>;
const RESSOURCE_ICON = {
  site: Globe2,
  maps: MapPin,
  linkedin: LinkedinIcon,
  annuaire: ExternalLink,
  facebook: FacebookIcon,
};


/* ---------------------------------------------------------------- */
/* Page                                                               */
/* ---------------------------------------------------------------- */

export default function DashboardPage() {
  const [etablissements, setEtablissements] = useState<Etablissement[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"Informations" | "Contacts" | "Ressources">(
    "Informations"
  );
  const [filtreWilaya, setFiltreWilaya] = useState("Tous");
  const [filtreCommune, setFiltreCommune] = useState("Toutes");
  const [filtreSecteur, setFiltreSecteur] = useState("Tous");
  const [filtreSousSecteur, setFiltreSousSecteur] = useState("Tous");
  const [filtreScore, setFiltreScore] = useState("Tous");
  const [filtreCrm, setFiltreCrm] = useState("Tous");
  const [options, setOptions] = useState<FiltresOptions>({
  wilayas: [], secteurs: [], communes: [], sous_secteurs: [],
  });
  const [ajoutEnCours, setAjoutEnCours] = useState(false);

  async function ajouterAuCrm(id: string) {
   setAjoutEnCours(true);
   try {
    const res = await fetch(`http://localhost:8000/prospects/${id}/crm`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Échec de l'ajout au CRM");
    setEtablissements((prev) =>
      prev.map((e) => (e.id === id ? { ...e, dansCrm: true } : e))
    );
   } catch (e) {
    console.error(e);
   } finally {
    setAjoutEnCours(false);
   }
  }

  const SCORE_MIN: Record<string, number> = { "80 et plus": 80, "60 et plus": 60, "40 et plus": 40 };

  function resetFiltres() {
   setFiltreWilaya("Tous");
   setFiltreCommune("Toutes");
   setFiltreSecteur("Tous");
   setFiltreSousSecteur("Tous");
   setFiltreScore("Tous");
   setFiltreCrm("Tous");
   }   

  useEffect(() => {
   async function chargerFiltres() {
    const params = new URLSearchParams();
    if (filtreWilaya !== "Tous") params.set("wilaya", filtreWilaya);
    if (filtreSecteur !== "Tous") params.set("secteur", filtreSecteur);
    const res = await fetch(`http://localhost:8000/filtres?${params}`, { cache: "no-store" });
    const data: FiltresOptions = await res.json();
    setOptions(data);
   }
   chargerFiltres();
   }, [filtreWilaya, filtreSecteur]);

  useEffect(() => { setFiltreCommune("Toutes"); }, [filtreWilaya]);
  useEffect(() => { setFiltreSousSecteur("Tous"); }, [filtreSecteur]);
  useEffect(() => { setPage(1); }, [filtreWilaya, filtreCommune, filtreSecteur, filtreSousSecteur, filtreScore, filtreCrm]);

  useEffect(() => {
  async function charger() {
    setLoading(true);
    setErreur(null);
    try {
      const params = new URLSearchParams({ page: String(page), limite: "10" });
      if (filtreWilaya !== "Tous") params.set("wilaya", filtreWilaya);
      if (filtreCommune !== "Toutes") params.set("commune", filtreCommune);
      if (filtreSecteur !== "Tous") params.set("secteur", filtreSecteur);
      if (filtreSousSecteur !== "Tous") params.set("sous_secteur", filtreSousSecteur);
      if (filtreScore !== "Tous") params.set("score_min", String(SCORE_MIN[filtreScore]));
      if (filtreCrm !== "Tous") params.set("dans_crm", filtreCrm === "Ajoutés" ? "1" : "0");

      const res = await fetch(`http://localhost:8000/prospects?${params}`, {
        credentials: "include",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("Erreur lors du chargement des prospects");
      const data: ProspectsResponse = await res.json();
      const mapped = data.items.map(toEtablissement);
      setEtablissements(mapped);
      setTotal(data.total);
      setSelectedId((prev) => prev ?? mapped[0]?.id ?? null);
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
    }
   charger();
  }, [page, filtreWilaya, filtreCommune, filtreSecteur, filtreSousSecteur, filtreScore, filtreCrm]);

  const selected = useMemo(
    () => etablissements.find((e) => e.id === selectedId) ?? etablissements[0],
    [selectedId, etablissements]
  );

  const totalPages = Math.max(1, Math.ceil(total / 10));

  return (
    <main className="flex min-h-screen bg-slate-50/60 text-slate-900">
      <Sidebar />
      <div className="flex-1">
        <TopBar />
        <div className="mx-auto max-w-[1500px] px-6 pb-12 pt-6">
          <Filters
            total={total}
            wilaya={filtreWilaya} setWilaya={setFiltreWilaya}
            commune={filtreCommune} setCommune={setFiltreCommune}
            secteur={filtreSecteur} setSecteur={setFiltreSecteur}
            sousSecteur={filtreSousSecteur} setSousSecteur={setFiltreSousSecteur}
            score={filtreScore} setScore={setFiltreScore}
            crm={filtreCrm} setCrm={setFiltreCrm}
            options={options}
            onReset={resetFiltres}
            />

          {erreur && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm font-medium text-rose-600">
              {erreur} — vérifie que le backend tourne bien sur localhost:8000.
            </div>
          )}

          {!erreur && loading && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
              Chargement des prospects...
            </div>
          )}

          {!erreur && !loading && etablissements.length === 0 && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
              Aucun établissement trouvé.
            </div>
          )}

          {!erreur && !loading && etablissements.length > 0 && selected && (
            <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_420px]">
              <EtablissementsTable
                etablissements={etablissements}
                selectedId={selected.id}
                onSelect={(id) => {
                  setSelectedId(id);
                  setActiveTab("Informations");
                }}
                page={page}
                setPage={setPage}
                totalPages={totalPages}
              />
              <DetailPanel
                etablissement={selected}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                onAjouterCrm={ajouterAuCrm}
                ajoutEnCours={ajoutEnCours}
              />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

/* ---------------------------------------------------------------- */
/* Sidebar                                                            */
/* ---------------------------------------------------------------- */

function Sidebar() {
  const items = [
    { label: "Prospection", icon: Radar, href: "/dashboard", active: true },
    { label: "Décideurs", icon: UserSearch, href: "/decideurs", active: false },
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

/* ---------------------------------------------------------------- */
/* Top bar                                                            */
/* ---------------------------------------------------------------- */

function TopBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-[1500px] items-center gap-4 px-6">
        <div className="relative flex-1 max-w-xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Rechercher un établissement, une commune, une wilaya..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-11 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
        <div className="ml-auto flex items-center gap-3">
          <button className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-900 hover:text-slate-900">
            <Download className="h-4 w-4" />
            Exporter
          </button>
          <button className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:-translate-y-0.5 hover:bg-blue-700">
            <Plus className="h-4 w-4" />
            Nouvelle recherche
          </button>
          <button className="relative flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:border-slate-900 hover:text-slate-900">
            <Bell className="h-4 w-4" />
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
              2
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}

/* ---------------------------------------------------------------- */
/* Filters                                                            */
/* ---------------------------------------------------------------- */

function FilterSelect({
  label,
  value,
  options,
  onChange,
  allLabel = "Tous",
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  allLabel?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative min-w-[140px] flex-1">
      <p className="mb-1.5 text-xs font-medium text-slate-500">{label}</p>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-700 transition hover:border-slate-300"
      >
        {value}
        <ChevronDown className="h-4 w-4 text-slate-400" />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
          <button
            onClick={() => { onChange(allLabel); setOpen(false); }}
            className="block w-full px-3.5 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
          >
            {allLabel}
          </button>
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false); }}
              className="block w-full px-3.5 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

type FiltresOptions = { wilayas: string[]; secteurs: string[]; communes: string[]; sous_secteurs: string[] };

function Filters({
  total,
  wilaya, setWilaya,
  commune, setCommune,
  secteur, setSecteur,
  sousSecteur, setSousSecteur,
  score, setScore,
  crm, setCrm,
  options,
  onReset,
}: {
  total: number;
  wilaya: string; setWilaya: (v: string) => void;
  commune: string; setCommune: (v: string) => void;
  secteur: string; setSecteur: (v: string) => void;
  sousSecteur: string; setSousSecteur: (v: string) => void;
  score: string; setScore: (v: string) => void;
  crm: string; setCrm: (v: string) => void;
  options: FiltresOptions;
  onReset: () => void;
}) {
  const chips: { key: string; label: string; onRemove: () => void }[] = [];
  if (wilaya !== "Tous") chips.push({ key: "w", label: `Wilaya : ${wilaya}`, onRemove: () => setWilaya("Tous") });
  if (commune !== "Toutes") chips.push({ key: "c", label: `Commune : ${commune}`, onRemove: () => setCommune("Toutes") });
  if (secteur !== "Tous") chips.push({ key: "s", label: `Secteur : ${secteur}`, onRemove: () => setSecteur("Tous") });
  if (sousSecteur !== "Tous") chips.push({ key: "ss", label: `Sous-secteur : ${sousSecteur}`, onRemove: () => setSousSecteur("Tous") });
  if (score !== "Tous") chips.push({ key: "sc", label: `Score : ${score}`, onRemove: () => setScore("Tous") });
  if (crm !== "Tous") chips.push({ key: "crm", label: `CRM : ${crm}`, onRemove: () => setCrm("Tous") });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="flex flex-wrap items-end gap-4">
        <FilterSelect label="Wilaya" value={wilaya} options={options.wilayas} onChange={setWilaya} />
        <FilterSelect label="Commune" value={commune} options={options.communes} onChange={setCommune} allLabel="Toutes" />
        <FilterSelect label="Secteur" value={secteur} options={options.secteurs} onChange={setSecteur} />
        <FilterSelect label="Sous-secteur" value={sousSecteur} options={options.sous_secteurs} onChange={setSousSecteur} />
        <FilterSelect label="Score DASEC" value={score} options={["80 et plus", "60 et plus", "40 et plus"]} onChange={setScore} />
        <FilterSelect label="Dans le CRM" value={crm} options={["Ajoutés", "Non ajoutés"]} onChange={setCrm} />
        <button
          onClick={onReset}
          className="mb-0.5 flex items-center gap-1.5 whitespace-nowrap px-1 py-2.5 text-sm font-medium text-slate-500 transition hover:text-slate-900"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Réinitialiser
        </button>
      </div>

      {chips.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          {chips.map((chip) => (
            <span key={chip.key} className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
              {chip.label}
              <X onClick={chip.onRemove} className="h-3 w-3 cursor-pointer text-blue-400 hover:text-blue-700" />
            </span>
          ))}
          <span className="ml-2 text-sm font-medium text-blue-600">
            {total} résultat{total > 1 ? "s" : ""} trouvé{total > 1 ? "s" : ""}
          </span>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Table                                                              */
/* ---------------------------------------------------------------- */

function EtablissementsTable({
  etablissements,
  selectedId,
  onSelect,
  page,
  setPage,
  totalPages,
}: {
  etablissements: Etablissement[];
  selectedId: string;
  onSelect: (id: string) => void;
  page: number;
  setPage: (p: number) => void;
  totalPages: number;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-100">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-xs font-medium text-slate-400">
            <th className="px-5 py-3.5 font-medium">Nom de l&apos;établissement</th>
            <th className="px-3 py-3.5 font-medium">Wilaya</th>
            <th className="px-3 py-3.5 font-medium">Commune</th>
            <th className="px-3 py-3.5 font-medium">Secteur</th>
            <th className="px-3 py-3.5 font-medium">Sous-secteur</th>
            <th className="px-3 py-3.5 font-medium">Score DASEC</th>
            <th className="px-3 py-3.5 font-medium">CRM</th>
            <th className="px-3 py-3.5" />
          </tr>
        </thead>
        <tbody>
          {etablissements.map((e) => {
            const isSelected = e.id === selectedId;
            return (
              <tr
                key={e.id}
                onClick={() => onSelect(e.id)}
                className={`cursor-pointer border-b border-slate-50 border-l-2 transition last:border-0 ${
                  isSelected
                    ? "border-l-blue-600 bg-blue-50/50"
                    : "border-l-transparent hover:bg-slate-50/70"
                }`}
              >
                <td
                  className={`px-5 py-3.5 font-semibold ${
                    isSelected ? "text-blue-600" : "text-slate-800"
                  }`}
                >
                  {e.nom}
                </td>
                <td className="px-3 py-3.5 text-slate-500">{e.wilaya}</td>
                <td className="px-3 py-3.5 text-slate-500">{e.commune}</td>
                <td className="px-3 py-3.5 text-slate-500">{e.secteur}</td>
                <td className="px-3 py-3.5 text-slate-500">{e.sousSecteur}</td>
                <td className="px-3 py-3.5">
                  <span className="inline-flex items-center justify-center rounded-lg bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">
                    {e.score}
                  </span>
                </td>
                <td className="px-3 py-3.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                      e.dansCrm
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {e.dansCrm ? "Ajouté" : "Non ajouté"}
                  </span>
                </td>
                <td className="px-3 py-3.5 text-right">
                  <MoreVertical className="ml-auto h-4 w-4 text-slate-300" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((n) => (
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
          {totalPages > 5 && (
            <>
              <span className="px-1 text-sm text-slate-400">…</span>
              <button
                onClick={() => setPage(totalPages)}
                className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-medium transition ${
                  page === totalPages
                    ? "bg-blue-600 text-white"
                    : "text-slate-500 hover:bg-slate-50"
                }`}
              >
                {totalPages}
              </button>
            </>
          )}
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          Lignes par page :
          <button className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-slate-700">
            10
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Detail panel                                                      */
/* ---------------------------------------------------------------- */

function DetailPanel({
  etablissement,
  activeTab,
  onTabChange,
  onAjouterCrm,
  ajoutEnCours,
}: {
  etablissement: Etablissement;
  activeTab: "Informations" | "Contacts" | "Ressources";
  onTabChange: (tab: "Informations" | "Contacts" | "Ressources") => void;
  onAjouterCrm: (id: string) => void;
  ajoutEnCours: boolean;
}) {
  const tabs: ("Informations" | "Contacts" | "Ressources")[] = [
    "Informations",
    "Contacts",
    "Ressources",
  ];

  return (
    <div className="h-fit rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-100">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">{etablissement.nom}</h3>
            <p className="text-xs text-slate-400">{etablissement.type}</p>
          </div>
        </div>
        <div className="flex flex-col items-end rounded-xl bg-emerald-50 px-3 py-2 text-right">
          <span className="text-lg font-bold text-emerald-700">
            {etablissement.score}
            <span className="text-xs font-medium text-emerald-500">/100</span>
          </span>
          <span className="text-[10px] font-medium text-emerald-600">Score DASEC</span>
        </div>
      </div>

      <div className="mt-5 flex gap-5 border-b border-slate-100 text-sm font-medium">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`relative pb-3 transition ${
              activeTab === tab ? "text-blue-600" : "text-slate-400 hover:text-slate-700"
            }`}
          >
            {tab}
            {activeTab === tab && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-blue-600" />
            )}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {activeTab === "Informations" && (
          <div className="grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
            {/* Colonne gauche : infos générales */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-3.5 text-sm min-w-0">
              <Field label="Secteur" value={etablissement.secteur} />
              <Field label="Sous-secteur" value={etablissement.sousSecteur} />
              <Field label="Statut" value={etablissement.statutJuridique} />
              <Field label="Effectif" value={etablissement.effectif} />
              <Field label="Réseau / Groupe" value={etablissement.reseau} />
              <Field label="Wilaya" value={etablissement.wilaya} />
              <Field label="Commune" value={etablissement.commune} />
              <div className="col-span-2">
                <Field label="Adresse" value={etablissement.adresse} />
              </div>
            </div>

            {/* Colonne droite : coordonnées + contact principal */}
            <div className="space-y-4 min-w-0">
              <div>
                <p className="mb-2 text-xs font-semibold text-slate-500">Coordonnées</p>
                <div className="space-y-2 text-sm">
                  <ContactLine icon={Phone} value={etablissement.telephone} />
                  <ContactLine icon={Mail} value={etablissement.email} />
                  <ContactLine icon={Globe2} value={etablissement.site} />
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold text-slate-500">Contact principal</p>
                <div className="flex items-start gap-3 rounded-xl bg-slate-50/70 p-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-slate-400">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="min-w-0" >
                    <p className="text-sm font-semibold text-slate-800">
                      {etablissement.contact.nom}
                    </p>
                    <p className="text-xs text-slate-400">{etablissement.contact.role}</p>
                    <p className="mt-1 text-xs text-slate-500">{etablissement.contact.telephone}</p>
                    <p className="text-xs text-slate-500 break-all">{etablissement.contact.email}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "Contacts" && (
          <div className="space-y-3 text-sm">
            <p className="text-xs font-semibold text-slate-500">Coordonnées générales</p>
            <ContactLine icon={Phone} value={etablissement.telephone} />
            <ContactLine icon={Mail} value={etablissement.email} />
            <ContactLine icon={Globe2} value={etablissement.site} />
            <p className="pt-2 text-xs font-semibold text-slate-500">Contact principal</p>
            <div className="flex items-start gap-3 rounded-xl bg-slate-50/70 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-slate-400">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-800">
                  {etablissement.contact.nom}
                </p>
                <p className="text-xs text-slate-400">{etablissement.contact.role}</p>
                <p className="mt-1 text-xs text-slate-500">{etablissement.contact.telephone}</p>
                <p className="text-xs text-slate-500 break-all">{etablissement.contact.email}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "Ressources" && (
          <div className="space-y-2">
            {etablissement.ressources.map((r) => {
              const Icon = RESSOURCE_ICON[r.icon];
              return (
                <a
                  key={r.label}
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 rounded-xl border border-slate-100 bg-slate-50/60 px-3.5 py-2.5 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50/60 hover:text-blue-700"
                >
                  <Icon className="h-4 w-4" />
                  {r.label}
                </a>
              );
            })}
            {etablissement.ressources.length === 0 && (
              <p className="text-sm text-slate-400">Aucune ressource trouvée pour le moment.</p>
            )}
          </div>
        )}
      </div>

      {/* Bloc persistant : ressources trouvées (boutons cliquables) + score */}
      <div className="mt-6 grid grid-cols-1 gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold text-slate-500">
            Ressources trouvées ({etablissement.ressources.length})
          </p>
          <div className="space-y-2">
            {etablissement.ressources.map((r) => {
              const Icon = RESSOURCE_ICON[r.icon];
              return (
                <a
                  key={r.label}
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50/60 hover:text-blue-700"
                >
                  <Icon className="h-3.5 w-3.5 text-blue-500" />
                  {r.label}
                </a>
              );
            })}
            {etablissement.ressources.length === 0 && (
              <p className="text-xs text-slate-400">Aucune ressource trouvée.</p>
            )}
          </div>
        </div>
<div>
          <p className="mb-2 text-xs font-semibold text-slate-500">Score</p>
          <div className="rounded-xl bg-slate-50/70 p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Score DASEC</span>
              <span className="font-semibold text-emerald-600">{etablissement.score} / 100</span>
            </div>

            {etablissement.scoreDetail && etablissement.scorePoids ? (
              <div className="mt-3 space-y-1.5 border-t border-slate-200 pt-3 text-xs">
                <ScoreLine
                  label="Sous-secteur"
                  value={etablissement.scoreDetail.sous_secteur}
                  max={etablissement.scorePoids.secteur}
                />
                <ScoreLine
                  label="Commune"
                  value={etablissement.scoreDetail.commune}
                  max={etablissement.scorePoids.commune}
                />
                <ScoreLine
                  label="Effectif"
                  value={etablissement.scoreDetail.effectif}
                  max={etablissement.scorePoids.effectif}
                />
                <ScoreLine
                  label="Maturité digitale"
                  value={etablissement.scoreDetail.maturite}
                  max={etablissement.scorePoids.maturite_digitale}
                />
                <ScoreLine
                  label="Réseau / Groupe"
                  value={etablissement.scoreDetail.reseau}
                  max={etablissement.scorePoids.reseau_groupe}
                />
                <div className="flex items-center justify-between text-slate-500">
                  <span>Bonus type de gestion</span>
                  <span className="font-medium text-slate-700">
                    +{etablissement.scoreDetail.bonus}
                  </span>
                </div>
              </div>
            ) : (
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
                Le détail par critère n&apos;est pas encore disponible pour cet
                établissement — il sera calculé au prochain passage du pipeline.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-3">
       <button
         onClick={() => onAjouterCrm(etablissement.id)}
         disabled={etablissement.dansCrm || ajoutEnCours}
         className="flex-1 rounded-full bg-blue-600 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:-translate-y-0.5 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
        >
        {etablissement.dansCrm ? "Déjà dans le CRM" : ajoutEnCours ? "Ajout..." : "+ Ajouter au CRM"}
       </button>
       <Link
         href="/crm"
         className="flex-1 rounded-full border border-slate-200 py-3 text-center text-sm font-semibold text-slate-600 transition hover:border-slate-900 hover:text-slate-900"
         >
        Voir dans le CRM
       </Link>
      </div>
      {etablissement.dansCrm && <SuiviCrm etablissement={etablissement} />}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 font-medium text-slate-800 break-words">{value}</p>
    </div>
  );
}

function ContactLine({ icon: Icon, value }: { icon: typeof Phone; value: string }) {
  return (
    <div className="flex items-center gap-2.5 text-slate-600 min-w-0">
      <Icon className="h-4 w-4 shrink-0 text-slate-400" />
      <span className="min-w-0 break-all">{value}</span>
    </div>
  );
}
function ScoreLine({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <div className="flex items-center justify-between text-slate-500">
      <span>{label}</span>
      <span className="font-medium text-slate-700">
        {value} / {max}
      </span>
    </div>
  );
}

const STATUTS_PIPELINE = [
  { code: "NOUVEAU", label: "Nouveau" },
  { code: "A_CONTACTER", label: "À contacter" },
  { code: "CONTACTE", label: "Contacté" },
  { code: "ECHANGE", label: "Échange" },
  { code: "RDV", label: "RDV" },
  { code: "PROPOSITION", label: "Proposition" },
  { code: "GAGNE", label: "Gagné" },
  { code: "PERDU", label: "Perdu" },
];

interface Interaction {
  id: number;
  type: string;
  contenu: string;
  date: string;
}

function SuiviCrm({ etablissement }: { etablissement: Etablissement }) {
  const [statut, setStatut] = useState(etablissement.statut ?? "NOUVEAU");
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [note, setNote] = useState("");
  const [prochaineTexte, setProchaineTexte] = useState(etablissement.prochaineAction ?? "");
  const [prochaineDate, setProchaineDate] = useState(etablissement.prochaineActionDate ?? "");
  const [chargement, setChargement] = useState(false);

  async function chargerInteractions() {
    const res = await fetch(`http://localhost:8000/prospects/${etablissement.id}/interactions`, {
      credentials: "include",
    });
    if (res.ok) setInteractions(await res.json());
  }

  useEffect(() => {
    setStatut(etablissement.statut ?? "NOUVEAU");
    setProchaineTexte(etablissement.prochaineAction ?? "");
    setProchaineDate(etablissement.prochaineActionDate ?? "");
    chargerInteractions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etablissement.id]);

  async function changerStatut(nouveauStatut: string) {
    if (nouveauStatut === "PERDU") {
      const motif = window.prompt("Motif de la perte (optionnel) :");
      setChargement(true);
      try {
        await fetch(`http://localhost:8000/prospects/${etablissement.id}/perdu`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ motif: motif || "Non renseigné" }),
        });
        setStatut(nouveauStatut);
        chargerInteractions();
      } finally {
        setChargement(false);
      }
      return;
    }

    setStatut(nouveauStatut);
    setChargement(true);
    try {
      await fetch(`http://localhost:8000/prospects/${etablissement.id}/statut?statut=${nouveauStatut}`, {
        method: "PATCH",
        credentials: "include",
      });
      chargerInteractions();
    } finally {
      setChargement(false);
    }
  }

  async function ajouterNote() {
    if (!note.trim()) return;
    setChargement(true);
    try {
      await fetch(`http://localhost:8000/prospects/${etablissement.id}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ contenu: note }),
      });
      setNote("");
      chargerInteractions();
    } finally {
      setChargement(false);
    }
  }

  async function enregistrerProchaineAction() {
    setChargement(true);
    try {
      await fetch(`http://localhost:8000/prospects/${etablissement.id}/prochaine-action`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ texte: prochaineTexte, date: prochaineDate }),
      });
    } finally {
      setChargement(false);
    }
  }

  return (
    <div className="mt-6 border-t border-slate-100 pt-5">
      <p className="mb-3 text-xs font-semibold text-slate-500">Suivi CRM</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-500">Statut</label>
          <select
            value={statut}
            onChange={(e) => changerStatut(e.target.value)}
            disabled={chargement}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
          >
            {STATUTS_PIPELINE.map((s) => (
              <option key={s.code} value={s.code}>{s.label}</option>
            ))}
          </select>
        </div>

        <div>
         <label className="mb-1.5 block text-xs font-medium text-slate-500">Prochaine action</label>
         <input
           type="text"
           value={prochaineTexte}
           onChange={(e) => setProchaineTexte(e.target.value)}
           placeholder="Ex : relancer par téléphone"
           className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
         />
         <input
           type="date"
           value={prochaineDate}
           onChange={(e) => setProchaineDate(e.target.value)}
           className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
         />
        <button
           onClick={enregistrerProchaineAction}
           disabled={chargement}
           className="mt-2 text-xs font-semibold text-blue-600 hover:underline disabled:opacity-50"
           >
          Enregistrer
        </button>
      </div>
      </div>

      <div className="mt-4">
        <label className="mb-1.5 block text-xs font-medium text-slate-500">Ajouter une note</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder="Ex : appelé, en attente de retour du DSI..."
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
        />
        <button
          onClick={ajouterNote}
          disabled={chargement || !note.trim()}
          className="mt-2 rounded-full bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
        >
          Ajouter
        </button>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium text-slate-500">Historique</p>
        {interactions.length === 0 ? (
          <p className="text-xs text-slate-400">Aucune action enregistrée pour l&apos;instant.</p>
        ) : (
          <div className="max-h-48 space-y-2 overflow-y-auto">
            {interactions.map((i) => (
              <div key={i.id} className="rounded-lg bg-slate-50/70 p-2.5 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="font-medium capitalize text-slate-600">{i.type}</span>
                  <span>{new Date(i.date).toLocaleString("fr-FR")}</span>
                </div>
                <p className="mt-1 text-slate-600">{i.contenu}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}