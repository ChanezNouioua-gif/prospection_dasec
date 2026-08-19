import {
  Search,
  LineChart,
  Bot,
  Send,
  ShieldCheck,
  Building2,
  Radar,
  Sparkles,
  ArrowRight,
  Globe2,
  FileBarChart,
} from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-white text-slate-900">
      <Navbar />
      <Hero />
      <StatsBar />
      <HowItWorks />
      <AIAgents />
      <CTABanner />
    </main>
  );
}

/* ---------- Navbar ---------- */

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-400">
              DASEC
            </p>
            <h2 className="text-lg font-bold tracking-tight">
              Prospect Intelligence
            </h2>
          </div>
        </div>
        <nav className="hidden items-center gap-10 text-sm font-medium text-slate-500 lg:flex">
          <a
            href="#fonctionnalites"
            className="transition hover:text-slate-900"
          >
            Fonctionnalités
          </a>
          <a href="#agents" className="transition hover:text-slate-900">
            AI Agents
          </a>
          <a href="#dashboard" className="transition hover:text-slate-900">
            Dashboard
          </a>
          <a href="#contact" className="transition hover:text-slate-900">
            Contact
          </a>
        </nav>
        <a
          href="/connexion"
          className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition duration-300 hover:-translate-y-0.5 hover:bg-slate-800"
        >
          Connexion
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </header>
  );
}

/* ---------- Hero ---------- */

function Hero() {
  return (
    <section className="relative overflow-hidden bg-white">
      {/* Background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#f1f5f9_1px,transparent_1px),linear-gradient(to_bottom,#f1f5f9_1px,transparent_1px)] bg-[size:48px_48px] opacity-60" />
      <div className="absolute left-1/2 top-0 h-[650px] w-[650px] -translate-x-1/2 rounded-full bg-blue-500/10 blur-[150px]" />
      <div className="absolute right-0 top-32 h-[400px] w-[400px] rounded-full bg-cyan-400/10 blur-[120px]" />
      <div className="relative mx-auto grid min-h-[88vh] max-w-7xl items-center gap-20 px-6 py-20 lg:grid-cols-2">
        {/* LEFT */}
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700">
            <Sparkles className="h-4 w-4" />
            AI-powered B2B Prospecting Platform
          </div>
          <h1 className="mt-8 text-5xl font-black leading-[0.95] tracking-[-0.05em] text-slate-900 lg:text-7xl">
            Prospect
            <br />
            Smarter.
          </h1>
          <h2 className="mt-2 text-5xl font-black tracking-[-0.05em] text-blue-600 lg:text-7xl">
            Not Harder.
          </h2>
          <p className="mt-8 max-w-xl text-lg leading-8 text-slate-600">
            Découvrez automatiquement les entreprises pertinentes, analysez
            leur maturité numérique et laissez l&apos;intelligence
            artificielle prioriser vos futurs clients.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <a
              href="/connexion"
              className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-7 py-4 text-sm font-semibold text-white shadow-xl shadow-blue-500/25 transition duration-300 hover:-translate-y-1 hover:bg-blue-700"
            >
              Accéder au dashboard
              <ArrowRight className="h-4 w-4" />
            </a>
            <button className="rounded-full border border-slate-300 bg-white px-7 py-4 text-sm font-semibold text-slate-700 transition hover:border-slate-900 hover:text-slate-900">
              Voir une démonstration
            </button>
          </div>
          <div className="mt-12 flex flex-wrap gap-8">
            <div>
              <h3 className="text-4xl font-bold text-slate-900">214+</h3>
              <p className="mt-1 text-sm text-slate-500">
                Entreprises analysées
              </p>
            </div>
            <div>
              <h3 className="text-4xl font-bold text-slate-900">98%</h3>
              <p className="mt-1 text-sm text-slate-500">
                Précision du scoring
              </p>
            </div>
            <div>
              <h3 className="text-4xl font-bold text-slate-900">5</h3>
              <p className="mt-1 text-sm text-slate-500">
                Agents IA spécialisés
              </p>
            </div>
          </div>
        </div>
        <DashboardMockup />
      </div>
    </section>
  );
}

function DashboardMockup() {
  const stats = [
    { label: "Entreprises collectées", value: "214", delta: "+12% ce mois" },
    { label: "Score moyen", value: "87", delta: "+3 pts ce mois" },
    { label: "Confiance IA", value: "94%", delta: "+1 pt ce mois" },
    { label: "Prospects prioritaires", value: "56", delta: "+8 cette semaine" },
  ];

  const rows = [
    { nom: "CHU Alger", secteur: "Santé", score: 92, statut: "Très fiable" },
    { nom: "Djezartech", secteur: "Telecom", score: 88, statut: "Très fiable" },
    { nom: "Algérie Télécom", secteur: "Telecom", score: 74, statut: "À valider" },
    { nom: "Groupe FTMS", secteur: "Oil & Gas", score: 69, statut: "À valider" },
    { nom: "Cerdist", secteur: "Agroalimentaire", score: 61, statut: "À revoir" },
  ];

  const statutColor: Record<string, string> = {
    "Très fiable": "text-emerald-600",
    "À valider": "text-amber-600",
    "À revoir": "text-rose-600",
  };

  return (
    <div
      id="dashboard"
      className="relative overflow-hidden rounded-[32px] border border-white/60 bg-white/80 p-6 shadow-2xl shadow-blue-200/40 backdrop-blur-xl"
    >
      <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-blue-500/10 blur-3xl" />
      <div className="absolute bottom-0 left-0 h-32 w-32 rounded-full bg-cyan-400/10 blur-3xl" />

      <div className="relative">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">
              Bienvenue, DASEC Team
            </p>
            <p className="text-xs text-slate-400">Aperçu de la prospection</p>
          </div>
          <div className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500">
            Tous les secteurs
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-slate-100 bg-slate-50/60 p-3"
            >
              <p className="text-lg font-bold text-slate-900">{s.value}</p>
              <p className="text-[11px] leading-tight text-slate-500">
                {s.label}
              </p>
              <p className="mt-1 text-[10px] font-medium text-emerald-600">
                {s.delta}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-5">
          <div className="rounded-xl border border-slate-100 p-3 sm:col-span-3">
            <p className="mb-2 text-xs font-semibold text-slate-500">
              Top prospects
            </p>
            <div className="space-y-2">
              {rows.map((r) => (
                <div
                  key={r.nom}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="w-24 truncate font-medium text-slate-800">
                    {r.nom}
                  </span>
                  <span className="w-20 truncate text-slate-400">
                    {r.secteur}
                  </span>
                  <span className="w-8 text-right font-semibold text-slate-700">
                    {r.score}
                  </span>
                  <span
                    className={`w-16 text-right font-medium ${statutColor[r.statut]}`}
                  >
                    {r.statut}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col items-center justify-center rounded-xl border border-slate-100 p-3 sm:col-span-2">
            <p className="mb-2 text-xs font-semibold text-slate-500">
              Répartition par secteur
            </p>
            <div
              className="flex h-24 w-24 items-center justify-center rounded-full"
              style={{
                background:
                  "conic-gradient(#2563eb 0% 30%, #38bdf8 30% 55%, #34d399 55% 75%, #a78bfa 75% 90%, #e2e8f0 90% 100%)",
              }}
            >
              <div className="flex h-16 w-16 flex-col items-center justify-center rounded-full bg-white text-center">
                <span className="text-sm font-bold text-slate-900">214</span>
                <span className="text-[9px] text-slate-400">total</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Stats bar ---------- */

function StatsBar() {
  const stats = [
    {
      icon: ShieldCheck,
      value: "98%",
      label: "Précision du scoring",
      sub: "Basé sur nos critères métiers",
    },
    {
      icon: Building2,
      value: "214",
      label: "Entreprises enrichies",
      sub: "Données à jour et vérifiées",
    },
    {
      icon: Bot,
      value: "5",
      label: "Agents IA spécialisés",
      sub: "Un pipeline 100% automatisé",
    },
    {
      icon: Radar,
      value: "24/7",
      label: "Surveillance continue",
      sub: "De nouvelles opportunités chaque jour",
    },
  ];

  return (
    <section className="mx-auto -mt-6 max-w-6xl px-6">
      <div className="grid grid-cols-1 gap-6 rounded-2xl border border-slate-100 bg-white p-8 shadow-lg shadow-slate-100 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ icon: Icon, value, label, sub }) => (
          <div key={label} className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xl font-bold text-slate-900">{value}</p>
              <p className="text-sm font-medium text-slate-700">{label}</p>
              <p className="text-xs text-slate-400">{sub}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------- How it works ---------- */

function HowItWorks() {
  const steps = [
    {
      icon: Search,
      title: "1. Découvrir",
      description:
        "L'IA identifie et découvre les entreprises pertinentes à partir de sources fiables et officielles.",
    },
    {
      icon: LineChart,
      title: "2. Analyser",
      description:
        "Nos agents analysent leur présence digitale, leurs technologies, leur maturité et leurs besoins potentiels.",
    },
    {
      icon: Sparkles,
      title: "3. Scorer",
      description:
        "Un score de priorité est calculé pour chaque entreprise selon vos critères commerciaux.",
    },
    {
      icon: Send,
      title: "4. Agir",
      description:
        "Accédez à un dashboard clair pour prioriser vos actions et maximiser vos opportunités.",
    },
  ];

  return (
    <section id="fonctionnalites" className="mx-auto max-w-6xl px-6 py-24">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-slate-900">
          Comment ça fonctionne
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Un pipeline intelligent en 4 étapes
        </p>
      </div>

      <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map(({ icon: Icon, title, description }, i) => (
          <div key={title} className="relative text-center">
            {i < steps.length - 1 && (
              <div className="absolute right-[-1rem] top-6 hidden h-px w-8 bg-slate-200 lg:block" />
            )}
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <Icon className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-sm font-semibold text-slate-900">
              {title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">
              {description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------- AI Agents ---------- */

function AIAgents() {
  const agents = [
    {
      icon: Search,
      name: "Discovery Agent",
      description: "Recherche et identification d'entreprises ciblées.",
    },
    {
      icon: LineChart,
      name: "Tech Analysis Agent",
      description: "Analyse des technologies et de la maturité digitale.",
    },
    {
      icon: Globe2,
      name: "Website Agent",
      description: "Analyse des sites et de la présence en ligne.",
    },
    {
      icon: Sparkles,
      name: "Scoring Agent",
      description: "Calcul du score et du potentiel commercial.",
    },
    {
      icon: FileBarChart,
      name: "Reporting Agent",
      description: "Génération de rapports et recommandations.",
    },
  ];

  return (
    <section
      id="agents"
      className="border-t border-slate-100 bg-slate-50/60 py-24"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-slate-900">
            Powered by AI Agents
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Chaque étape est exécutée par un agent IA spécialisé.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {agents.map(({ icon: Icon, name, description }) => (
            <div
              key={name}
              className="rounded-xl border border-slate-200 bg-white p-5 text-center shadow-sm"
            >
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-slate-900">
                {name}
              </h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- CTA banner + footer ---------- */

function CTABanner() {
  return (
    <footer className="bg-slate-900">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 py-10 sm:flex-row">
        <div className="text-center sm:text-left">
          <h3 className="text-lg font-semibold text-white">
            Prêt à booster votre prospection ?
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Connectez-vous et accédez à votre dashboard.
          </p>
        </div>
        <a
          href="/connexion"
          className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          Accéder au dashboard
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>

      <div className="border-t border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-6 py-4 text-xs text-slate-500 sm:flex-row">
          <span className="font-medium text-slate-300">
            DASEC <span className="text-blue-400">Prospect Intelligence</span>
          </span>
          <span>Plateforme interne sécurisée</span>
          <span>DASEC Group © 2026</span>
        </div>
      </div>
    </footer>
  );
}