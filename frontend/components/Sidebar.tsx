"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Radar, UserSearch, Building2, Megaphone, History, Settings, LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { logout, getCurrentUser } from "@/lib/api";
import Image from "next/image";

const NAV_ITEMS = [
  { label: "Prospection", icon: Radar, href: "/dashboard" },
  { label: "Décideurs", icon: UserSearch, href: "/decideurs" },
  { label: "CRM", icon: Building2, href: "/crm" },
  { label: "Campagnes", icon: Megaphone, href: "#" },
  { label: "Historique", icon: History, href: "/historique" },
  { label: "Paramètres", icon: Settings, href: "/parametres" },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [utilisateur, setUtilisateur] = useState<{ username: string; nom_complet: string | null } | null>(null);
  const [repliee, setRepliee] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(setUtilisateur)
      .catch(() => router.push("/connexion"));
  }, [router]);

  async function handleLogout() {
    try {
      await logout();
    } finally {
      router.push("/connexion");
    }
  }

  const nomAffiche = utilisateur?.nom_complet || utilisateur?.username || "…";
  const initiale = nomAffiche.charAt(0).toUpperCase();

  return (
    <aside className={`sidebar-collapsible sticky top-0 flex h-screen shrink-0 flex-col justify-between border-r border-slate-200/70 bg-white py-6 transition-[width] duration-200 ${repliee ? "w-20 px-3" : "w-64 px-4"}`}>
      <div>
        <div className={`flex items-center px-2 ${repliee ? "flex-col gap-2" : "gap-2.5"}`}>
          <div className="flex h-10 w-10 items-center justify-center">
           <Image
             src="/logo_dasecgroup.png"
             alt="DASEC Group"
             width={40}
             height={40}
             className="h-10 w-10 object-contain"
             priority
           />
          </div>
          {!repliee && <div>
            <p className="text-sm font-bold leading-tight text-slate-900">DASEC</p>
            <p className="text-[11px] text-slate-400">Prospect Intelligence</p>
          </div>}
          <button onClick={() => setRepliee((value) => !value)} aria-label={repliee ? "Afficher la barre latérale" : "Réduire la barre latérale"} title={repliee ? "Afficher le menu" : "Réduire le menu"} className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-50 hover:text-slate-700 ${repliee ? "" : "ml-auto"}`}>
            {repliee ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>
        </div>

        <button onClick={() => setRepliee((value) => !value)} aria-label={repliee ? "Afficher la barre latérale" : "Réduire la barre latérale"} title={repliee ? "Afficher le menu" : "Réduire le menu"} className={`mt-5 flex w-full items-center rounded-xl py-2 text-slate-400 transition hover:bg-slate-50 hover:text-slate-700 ${repliee ? "justify-center" : "justify-end px-3"}`}>
          {repliee ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>

        <nav className="mt-3 flex flex-col gap-1">
          {NAV_ITEMS.map(({ label, icon: Icon, href }) => {
            const active = pathname === href;
            return (
              <Link
                key={label}
                href={href}
                title={repliee ? label : undefined}
                className={`flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition ${repliee ? "justify-center" : "gap-3"} ${
                  active
                    ? "bg-blue-50 text-blue-700"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <Icon className="h-4 w-4" />
                {!repliee && label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-1 border-t border-slate-100 pt-4">
        <div className={`flex items-center rounded-xl px-3 py-2 ${repliee ? "justify-center" : "gap-3"}`} title={repliee ? nomAffiche : undefined}>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
            {initiale}
          </div>
          {!repliee && <p className="text-sm font-semibold text-slate-800">{nomAffiche}</p>}
        </div>
        <button
          onClick={handleLogout}
          title={repliee ? "Déconnexion" : undefined}
          className={`flex items-center rounded-xl px-3 py-2.5 font-medium text-slate-400 transition hover:bg-slate-50 hover:text-slate-700 ${repliee ? "justify-center text-[0px]" : "gap-3 text-sm"}`}
        >
          <LogOut className="h-4 w-4" />
          Déconnexion
        </button>
      </div>
    </aside>
  );
}
