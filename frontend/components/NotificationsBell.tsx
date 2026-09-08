// components/NotificationsBell.tsx — nouveau fichier, tout le composant cloche que je t'ai donné
"use client";

import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { getResumeCrm } from "@/lib/api";

interface Tache {
  id: number;
  prospect_nom: string;
  description: string;
  date_echeance: string;
  en_retard: boolean;
}

export function NotificationsBell() {
  const [ouvert, setOuvert] = useState(false);
  const [taches, setTaches] = useState<Tache[]>([]);

  useEffect(() => {
    getResumeCrm()
      .then((data) => setTaches(data.taches_du_jour.filter((t: Tache) => t.en_retard)))
      .catch(() => setTaches([]));
  }, []);

  return (
    <div className="relative">
      <button
        onClick={() => setOuvert((o) => !o)}
        className="relative flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:border-slate-900 hover:text-slate-900"
      >
        <Bell className="h-4 w-4" />
        {taches.length > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
            {taches.length}
          </span>
        )}
      </button>

      {ouvert && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Relances en retard
          </p>
          {taches.length === 0 ? (
            <p className="px-2 py-3 text-sm text-slate-400">Aucune relance en retard 🎉</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {taches.map((t) => (
                <li key={t.id} className="rounded-xl px-2 py-2 text-sm hover:bg-slate-50">
                  <p className="font-medium text-slate-800">{t.prospect_nom}</p>
                  <p className="text-xs text-slate-500">{t.description}</p>
                  <p className="text-xs text-rose-500">Échéance : {t.date_echeance}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}