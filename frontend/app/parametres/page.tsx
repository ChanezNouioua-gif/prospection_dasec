"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Radar,
  Building2,
  Megaphone,
  History,
  Settings,
  LogOut,
  Bell,
  UserSearch,
  KeyRound,
  Users,
  BellRing,
  Loader2,
  CheckCircle2,
  CircleAlert,
} from "lucide-react";

/* ---------------------------------------------------------------- */
/* Config                                                            */
/* ---------------------------------------------------------------- */

// Ajuste ce préfixe si tes routes ne sont pas montées sur /auth dans main.py
// (ex: app.include_router(auth.router, prefix="/auth")).
const API_BASE = "http://localhost:8000";
const AUTH_BASE = `${API_BASE}/auth`;

/* ---------------------------------------------------------------- */
/* Types                                                              */
/* ---------------------------------------------------------------- */

interface MembreEquipe {
  username: string;
  nom_complet: string | null;
}

/* ---------------------------------------------------------------- */
/* Page                                                               */
/* ---------------------------------------------------------------- */

export default function ParametresPage() {
  return (
    <main className="flex min-h-screen bg-slate-50/60 text-slate-900">
      <Sidebar />
      <div className="flex-1">
        <TopBar />
        <div className="mx-auto max-w-3xl px-6 pb-12 pt-6">
          <PageHeader />
          <div className="mt-6 space-y-6">
            <SecuriteSection />
            <NotificationsSection />
            <EquipeSection />
          </div>
        </div>
      </div>
    </main>
  );
}

/* ---------------------------------------------------------------- */
/* Sidebar / TopBar — repris de crm/page.tsx pour rester cohérent    */
/* ---------------------------------------------------------------- */

function Sidebar() {
  const items = [
    { label: "Prospection", icon: Radar, href: "/dashboard", active: false },
    { label: "Décideurs", icon: UserSearch, href: "/decideurs", active: false },
    { label: "CRM", icon: Building2, href: "/crm", active: false },
    { label: "Campagnes", icon: Megaphone, href: "#", active: false },
    { label: "Historique", icon: History, href: "/historique", active: false },
    { label: "Paramètres", icon: Settings, href: "/parametres", active: true },
  ];

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col justify-between border-r border-slate-200/70 bg-white px-4 py-6">
      <div>
        <div className="flex items-center gap-2.5 px-2">
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
        <p className="text-sm font-medium text-slate-400">Paramètres du compte</p>
        <div className="ml-auto flex items-center gap-3">
          <button className="relative flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:border-slate-900 hover:text-slate-900">
            <Bell className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

function PageHeader() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900">Paramètres</h1>
      <p className="mt-1 text-sm text-slate-500">
        Gère ton compte, tes préférences et l&apos;équipe DASEC.
      </p>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Sécurité — changement de mot de passe                             */
/* ---------------------------------------------------------------- */

function SecuriteSection() {
  const [ancien, setAncien] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [message, setMessage] = useState<{ type: "succes" | "erreur"; texte: string } | null>(null);

  const erreurValidation =
    nouveau.length > 0 && nouveau.length < 8
      ? "Le nouveau mot de passe doit faire au moins 8 caractères."
      : confirmation.length > 0 && nouveau !== confirmation
      ? "La confirmation ne correspond pas au nouveau mot de passe."
      : null;

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (erreurValidation || !ancien || !nouveau) return;

    setEnCours(true);
    try {
      const res = await fetch(`${AUTH_BASE}/mot-de-passe`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ancien_mot_de_passe: ancien,
          nouveau_mot_de_passe: nouveau,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail ?? "Échec de la modification du mot de passe.");
      }
      setMessage({ type: "succes", texte: "Mot de passe modifié." });
      setAncien("");
      setNouveau("");
      setConfirmation("");
    } catch (err) {
      setMessage({
        type: "erreur",
        texte: err instanceof Error ? err.message : "Erreur inconnue.",
      });
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <KeyRound className="h-4 w-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-900">Mot de passe</p>
      </div>

      <form onSubmit={soumettre} className="space-y-3">
        <ChampMotDePasse
          label="Mot de passe actuel"
          valeur={ancien}
          onChange={setAncien}
          autoComplete="current-password"
        />
        <ChampMotDePasse
          label="Nouveau mot de passe"
          valeur={nouveau}
          onChange={setNouveau}
          autoComplete="new-password"
        />
        <ChampMotDePasse
          label="Confirmer le nouveau mot de passe"
          valeur={confirmation}
          onChange={setConfirmation}
          autoComplete="new-password"
        />

        {erreurValidation && (
          <p className="flex items-center gap-1.5 text-xs font-medium text-amber-600">
            <CircleAlert className="h-3.5 w-3.5" />
            {erreurValidation}
          </p>
        )}

        {message && (
          <p
            className={`flex items-center gap-1.5 text-xs font-medium ${
              message.type === "succes" ? "text-emerald-600" : "text-rose-600"
            }`}
          >
            {message.type === "succes" ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <CircleAlert className="h-3.5 w-3.5" />
            )}
            {message.texte}
          </p>
        )}

        <button
          type="submit"
          disabled={enCours || !!erreurValidation || !ancien || !nouveau}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enCours && <Loader2 className="h-4 w-4 animate-spin" />}
          Modifier le mot de passe
        </button>
      </form>
    </div>
  );
}

function ChampMotDePasse({
  label,
  valeur,
  onChange,
  autoComplete,
}: {
  label: string;
  valeur: string;
  onChange: (v: string) => void;
  autoComplete: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-500">{label}</span>
      <input
        type="password"
        value={valeur}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        className="w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
      />
    </label>
  );
}

/* ---------------------------------------------------------------- */
/* Notifications                                                     */
/* ---------------------------------------------------------------- */

function NotificationsSection() {
  const [actives, setActives] = useState<boolean | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    async function charger() {
      try {
        const res = await fetch(`${AUTH_BASE}/preferences`, { credentials: "include" });
        if (!res.ok) throw new Error();
        const data = await res.json();
        setActives(Boolean(data.notifications_actives));
      } catch {
        setErreur("Impossible de charger les préférences.");
      }
    }
    charger();
  }, []);

  async function basculer() {
    if (actives === null || enCours) return;
    const nouvelleValeur = !actives;
    setActives(nouvelleValeur); // optimiste
    setEnCours(true);
    setErreur(null);
    try {
      const res = await fetch(`${AUTH_BASE}/preferences`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notifications_actives: nouvelleValeur }),
      });
      if (!res.ok) throw new Error();
    } catch {
      setActives(!nouvelleValeur); // rollback
      setErreur("Échec de la mise à jour — réessaie.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <BellRing className="h-4 w-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-900">Notifications</p>
      </div>

      <div className="flex items-center justify-between rounded-xl bg-slate-50/60 p-4">
        <div>
          <p className="text-sm font-medium text-slate-700">Relances et alertes</p>
          <p className="mt-0.5 text-xs text-slate-400">
            Tâches en retard, nouveaux prospects, RDV à venir.
          </p>
        </div>
        <button
          role="switch"
          aria-checked={actives ?? false}
          onClick={basculer}
          disabled={actives === null || enCours}
          className={`relative h-6 w-11 shrink-0 rounded-full transition disabled:opacity-50 ${
            actives ? "bg-blue-600" : "bg-slate-200"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
              actives ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      </div>

      {erreur && (
        <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-rose-600">
          <CircleAlert className="h-3.5 w-3.5" />
          {erreur}
        </p>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Équipe                                                             */
/* ---------------------------------------------------------------- */

function EquipeSection() {
  const [membres, setMembres] = useState<MembreEquipe[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    async function charger() {
      try {
        const res = await fetch(`${AUTH_BASE}/equipe`, { credentials: "include" });
        if (!res.ok) throw new Error();
        setMembres(await res.json());
      } catch {
        setErreur("Impossible de charger l'équipe.");
      }
    }
    charger();
  }, []);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="mb-4 flex items-center gap-2">
        <Users className="h-4 w-4 text-slate-400" />
        <p className="text-sm font-semibold text-slate-900">Équipe</p>
      </div>

      {erreur && (
        <p className="flex items-center gap-1.5 text-xs font-medium text-rose-600">
          <CircleAlert className="h-3.5 w-3.5" />
          {erreur}
        </p>
      )}

      {!erreur && membres === null && (
        <p className="text-sm text-slate-400">Chargement...</p>
      )}

      {membres && membres.length > 0 && (
        <div className="space-y-2">
          {membres.map((m) => (
            <div key={m.username} className="flex items-center gap-3 rounded-xl bg-slate-50/60 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                {(m.nom_complet ?? m.username).charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">{m.nom_complet ?? m.username}</p>
                <p className="text-xs text-slate-400">@{m.username}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
