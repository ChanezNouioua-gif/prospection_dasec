"use client";

import { Search, Download, Plus } from "lucide-react";
import { NotificationsBell } from "@/components/NotificationsBell";

interface TopBarProps {
  recherche?: string;
  onRechercheChange?: (valeur: string) => void;
  onExporter?: () => void;
}

export function TopBar({ recherche = "", onRechercheChange, onExporter }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-[1500px] items-center gap-4 px-6">
        <div className="relative flex-1 max-w-xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={recherche}
            onChange={(e) => onRechercheChange?.(e.target.value)}
            placeholder="Rechercher un établissement, une commune, une wilaya..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-11 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={onExporter}
            disabled={!onExporter}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-900 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download className="h-4 w-4" />
            Exporter
          </button>
          <button className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:-translate-y-0.5 hover:bg-blue-700">
            <Plus className="h-4 w-4" />
            Nouvelle recherche
          </button>
          <NotificationsBell />
        </div>
      </div>
    </header>
  );
}