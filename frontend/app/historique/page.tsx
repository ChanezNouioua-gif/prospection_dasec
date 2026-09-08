"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, CalendarDays, ChevronLeft, ChevronRight, FileText, Mail, Phone, RefreshCw, Users } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";

type TypeActivite = "appel" | "email" | "rdv" | "note" | "statut" | "relance";
interface Activite { id: number; entreprise_id: number; entreprise_nom: string; secteur: string | null; sous_secteur: string | null; type: TypeActivite; contenu: string; date: string | null; auteur: string | null; }
interface HistoriqueResponse { items: Activite[]; total: number; page: number; }

const LIMIT = 25;
const FILTRES: { value: "TOUS" | TypeActivite; label: string }[] = [
  { value: "TOUS", label: "Toutes" }, { value: "appel", label: "Appels" }, { value: "email", label: "Emails" }, { value: "rdv", label: "RDV" }, { value: "note", label: "Notes" }, { value: "statut", label: "Statuts" }, { value: "relance", label: "Relances" },
];
const CONFIG_TYPE: Record<TypeActivite, { label: string; Icon: typeof Phone; className: string }> = {
  appel: { label: "Appel", Icon: Phone, className: "bg-blue-50 text-blue-600" }, email: { label: "Email", Icon: Mail, className: "bg-violet-50 text-violet-600" }, rdv: { label: "RDV", Icon: Users, className: "bg-emerald-50 text-emerald-600" }, note: { label: "Note", Icon: FileText, className: "bg-amber-50 text-amber-600" }, statut: { label: "Statut", Icon: ArrowRight, className: "bg-slate-100 text-slate-600" }, relance: { label: "Relance", Icon: RefreshCw, className: "bg-rose-50 text-rose-600" },
};

function formatDate(date: string | null): string {
  if (!date) return "Date inconnue";
  const parsed = new Date(date.replace(" ", "T") + "Z");
  return Number.isNaN(parsed.getTime()) ? "Date inconnue" : parsed.toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

export default function HistoriquePage() {
  const [recherche, setRecherche] = useState("");
  const [filtre, setFiltre] = useState<"TOUS" | TypeActivite>("TOUS");
  const [page, setPage] = useState(1);
  const [historique, setHistorique] = useState<HistoriqueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const timeout = window.setTimeout(async () => {
      setLoading(true); setErreur(null);
      try {
        const params = new URLSearchParams({ page: String(page), limite: String(LIMIT) });
        if (recherche.trim()) params.set("q", recherche.trim());
        if (filtre !== "TOUS") params.set("type", filtre);
        const res = await fetch(`http://localhost:8000/crm/historique?${params}`, { credentials: "include", cache: "no-store" });
        if (!res.ok) throw new Error("Impossible de charger l'historique");
        setHistorique(await res.json());
      } catch (error) { setErreur(error instanceof Error ? error.message : "Erreur inconnue"); }
      finally { setLoading(false); }
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [recherche, filtre, page]);

  const totalPages = Math.max(1, Math.ceil((historique?.total ?? 0) / LIMIT));
  const changerFiltre = (value: "TOUS" | TypeActivite) => { setFiltre(value); setPage(1); };

  return <main className="flex min-h-screen bg-slate-50/60 text-slate-900"><Sidebar /><div className="min-w-0 flex-1"><TopBar recherche={recherche} onRechercheChange={(value) => { setRecherche(value); setPage(1); }} /><div className="mx-auto max-w-5xl px-6 pb-12 pt-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2 text-sm text-slate-400"><Activity className="h-4 w-4" />CRM</div><h1 className="mt-1 text-2xl font-bold text-slate-900">Historique des activités</h1><p className="mt-1 text-sm text-slate-500">Suivez tous les appels, emails, notes et changements de statut.</p></div><div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500"><CalendarDays className="h-4 w-4 text-slate-400" />{historique?.total ?? 0} activité{(historique?.total ?? 0) > 1 ? "s" : ""}</div></div>
    <div className="mt-6 flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm shadow-slate-100">{FILTRES.map(({ value, label }) => <button key={value} onClick={() => changerFiltre(value)} className={`rounded-xl px-3.5 py-2 text-sm font-medium transition ${filtre === value ? "bg-blue-600 text-white shadow-sm" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"}`}>{label}</button>)}</div>
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      {erreur && <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600">{erreur}</p>}
      {!erreur && loading && <p className="py-12 text-center text-sm text-slate-400">Chargement de l&apos;historique...</p>}
      {!erreur && !loading && historique?.items.length === 0 && <div className="py-14 text-center"><Activity className="mx-auto h-8 w-8 text-slate-300" /><p className="mt-3 text-sm font-medium text-slate-500">Aucune activité ne correspond à votre recherche.</p></div>}
      {!erreur && !loading && historique && historique.items.length > 0 && <div className="divide-y divide-slate-100">{historique.items.map((activite) => { const config = CONFIG_TYPE[activite.type]; const { Icon } = config; return <Link key={activite.id} href={`/crm/prospect/${activite.entreprise_id}`} className="flex gap-4 py-4 first:pt-0 last:pb-0 hover:bg-slate-50/60"><div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${config.className}`}><Icon className="h-4 w-4" /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-x-2 gap-y-1"><p className="font-semibold text-slate-800">{activite.entreprise_nom}</p><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{config.label}</span></div><p className="mt-1 text-sm text-slate-600">{activite.contenu}</p><p className="mt-1.5 text-xs text-slate-400">{activite.sous_secteur ?? activite.secteur ?? "Prospect"} · {formatDate(activite.date)}{activite.auteur ? ` · ${activite.auteur}` : ""}</p></div><ChevronRight className="mt-2 h-4 w-4 shrink-0 text-slate-300" /></Link>; })}</div>}
    </section>
    {!loading && !erreur && totalPages > 1 && <div className="mt-6 flex items-center justify-between"><p className="text-sm text-slate-500">Page {page} sur {totalPages}</p><div className="flex gap-2"><button onClick={() => setPage((current) => current - 1)} disabled={page === 1} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="h-4 w-4" />Précédent</button><button onClick={() => setPage((current) => current + 1)} disabled={page === totalPages} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 disabled:cursor-not-allowed disabled:opacity-40">Suivant<ChevronRight className="h-4 w-4" /></button></div></div>}
  </div></div></main>;
}
