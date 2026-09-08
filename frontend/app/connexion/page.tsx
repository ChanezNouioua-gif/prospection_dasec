"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowRight, Loader2 } from "lucide-react";
import Image from "next/image";

export default function ConnexionPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
   e.preventDefault();
   setErreur(null);
   setChargement(true);

   try {
    const body = new URLSearchParams();
    body.append("username", username);
    body.append("password", password);

    const res = await fetch("http://localhost:8000/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include", // <-- indispensable pour envoyer/recevoir le cookie
      body,
    });

    if (!res.ok) {
      throw new Error("Identifiants incorrects");
    }

    router.push("/dashboard");
   } catch (err) {
    setErreur(err instanceof Error ? err.message : "Une erreur est survenue");
   } finally {
    setChargement(false);
   }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-white">
      {/* Background — cohérent avec le hero de la page d'accueil */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#f1f5f9_1px,transparent_1px),linear-gradient(to_bottom,#f1f5f9_1px,transparent_1px)] bg-[size:48px_48px] opacity-60" />
      <div className="absolute left-1/2 top-0 h-[650px] w-[650px] -translate-x-1/2 rounded-full bg-blue-500/10 blur-[150px]" />
      <div className="absolute right-0 top-32 h-[400px] w-[400px] rounded-full bg-cyan-400/10 blur-[120px]" />

      <div className="relative w-full max-w-md px-6">
        {/* Logo / header */}
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex h-10 w-10 items-center justify-center">
           <Image
             src="/logo_dasecgroup.png"
             alt="DASEC Group"
             width={60}
             height={60}
             className="h-12 w-12 object-contain"
             priority
            />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.35em] text-slate-400">
            DASEC GROUP
          </p>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Prospect Intelligence
          </h1>
        </div>

        {/* Card */}
        <div className="relative overflow-hidden rounded-[32px] border border-white/60 bg-white/80 p-8 shadow-2xl shadow-blue-200/40 backdrop-blur-xl">
          <h2 className="text-lg font-semibold text-slate-900">Connexion</h2>
          <p className="mt-1 text-sm text-slate-500">
            Accédez à votre espace de prospection.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="username"
                className="mb-1.5 block text-xs font-medium text-slate-600"
              >
                Identifiant
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                placeholder="Dasec_equipe"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-medium text-slate-600"
              >
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                placeholder="••••••••"
              />
            </div>

            {erreur && (
              <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-medium text-rose-600">
                {erreur}
              </p>
            )}

            <button
              type="submit"
              disabled={chargement}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow-xl shadow-blue-500/25 transition duration-300 hover:-translate-y-0.5 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {chargement ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Connexion...
                </>
              ) : (
                <>
                  Se connecter
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Accès réservé aux membres de l&apos;équipe DASEC.
        </p>
      </div>
    </main>
  );
}