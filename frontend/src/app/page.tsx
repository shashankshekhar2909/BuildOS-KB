"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

const FEATURES = [
  {
    icon: "🔍",
    title: "Hybrid Search",
    desc: "Keyword + semantic + graph search across all your indexed projects.",
    detail: "PostgreSQL tsvector + pgvector cosine similarity, merged with configurable weights.",
  },
  {
    icon: "🤖",
    title: "AI-Generated OKF",
    desc: "Every project gets an Operational Knowledge File — architecture, APIs, decisions, stack.",
    detail: "LiteLLM gateway: Claude, Gemini, OpenAI, Groq, or any local model.",
  },
  {
    icon: "🛠️",
    title: "MCP Server",
    desc: "Expose your project knowledge as MCP tools. Claude Code queries it directly.",
    detail: "Tools: list_projects, get_project, search, get_okf, reindex.",
  },
  {
    icon: "⚡",
    title: "Auto-Discovery",
    desc: "Finds every project automatically. Detects language, framework, and tech stack.",
    detail: "Scans configurable directories every 15 minutes. Hash-based change detection.",
  },
  {
    icon: "🔒",
    title: "Sync Auth",
    desc: "Browse freely. Google OAuth gates expensive LLM sync operations only.",
    detail: "JWT sessions. Works on localhost and LAN — no external auth server.",
  },
  {
    icon: "📊",
    title: "Knowledge Graph",
    desc: "Relationships between projects, technologies, and concepts — visualized.",
    detail: "PostgreSQL graph schema with React Flow visualization.",
  },
];

const FLOW_STEPS = [
  { icon: "📁", label: "Your Projects", sub: "Any directory on disk" },
  { icon: "🔎", label: "Auto Discovery", sub: "Every 15 min, hash-checked" },
  { icon: "🤖", label: "AI Extraction", sub: "Gemini / Claude / GPT" },
  { icon: "📄", label: "OKF + Embeddings", sub: "768-dim vectors in pgvector" },
  { icon: "⚡", label: "Search & MCP", sub: "UI, API, Claude Code" },
];

const SETUP_STEPS = [
  {
    step: "1",
    title: "Clone & configure",
    code: `git clone https://github.com/buildwithshashank/buildos-kb
cp .env.example .env
# Add GEMINI_API_KEY or OPENAI_API_KEY
# Set SCAN_DIRECTORIES=/home/you/projects`,
  },
  {
    step: "2",
    title: "Start services",
    code: `docker compose up -d
# API  → :8010
# UI   → :3100
# MCP  → :8090`,
  },
  {
    step: "3",
    title: "Add MCP to Claude",
    code: `claude mcp add buildos-kb \\
  --transport http \\
  http://localhost:8090/mcp`,
  },
  {
    step: "4",
    title: "Ask Claude anything",
    code: `# In any Claude session:
"What projects do I have?"
"How does AetherAXE work?"
"Find auth-related code"`,
  },
];

const STACK = [
  { label: "Backend", value: "FastAPI + Python 3.13 + SQLAlchemy 2 + ARQ" },
  { label: "Database", value: "PostgreSQL 16 + pgvector (768-dim embeddings)" },
  { label: "AI", value: "LiteLLM → Gemini / Claude / OpenAI / Groq" },
  { label: "Frontend", value: "Next.js 15 + TypeScript + Tailwind CSS v4" },
  { label: "Protocol", value: "MCP Streamable HTTP, port 8090" },
  { label: "Queue", value: "ARQ + Redis — async job dedup" },
];

function FlowDiagram() {
  const [active, setActive] = useState(-1);

  useEffect(() => {
    let i = 0;
    const t = setInterval(() => {
      setActive(i);
      i++;
      if (i >= FLOW_STEPS.length) {
        setTimeout(() => { setActive(-1); i = 0; }, 800);
      }
    }, 700);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col items-center gap-0 sm:flex-row sm:items-start sm:justify-center sm:gap-0">
      {FLOW_STEPS.map((s, i) => (
        <div key={s.label} className="flex flex-col sm:flex-row items-center">
          {/* Node */}
          <div
            className={`flex flex-col items-center gap-2 px-5 py-4 border transition-all duration-500 w-36 ${
              active === i
                ? "border-accent bg-accent/10 scale-105 shadow-lg shadow-accent/20"
                : active > i
                ? "border-border-2 bg-surface-2 opacity-80"
                : "border-border bg-surface opacity-50"
            }`}
          >
            <span className="text-2xl">{s.icon}</span>
            <span className="text-xs font-bold text-text text-center leading-tight">{s.label}</span>
            <span className="text-[10px] text-muted text-center leading-tight">{s.sub}</span>
          </div>

          {/* Arrow */}
          {i < FLOW_STEPS.length - 1 && (
            <div className={`flex items-center justify-center transition-all duration-500 ${
              active > i ? "text-accent" : "text-border"
            }`}>
              <span className="hidden sm:block text-2xl font-bold mx-1">→</span>
              <span className="sm:hidden text-2xl font-bold my-1">↓</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Nav */}
      <nav className="sticky top-0 z-50 flex items-center h-14 px-8 gap-6 border-b border-border bg-surface/90 backdrop-blur-sm">
        <span className="font-black text-base tracking-tight">BuildOS KB</span>
        <span className="text-subtle text-xs hidden sm:block">by BuildWithShashank</span>
        <div className="ml-auto flex items-center gap-3">
          <Link
            href="/dashboard"
            className="px-4 py-1.5 text-white text-sm font-semibold no-underline transition-opacity hover:opacity-90"
            style={{ background: "linear-gradient(to right, #4589ff, #0f62fe)" }}
          >
            Open Dashboard →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative max-w-4xl mx-auto px-8 pt-20 pb-12 text-center overflow-hidden">
        {/* CSS-only dot grid pattern */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(69,137,255,0.18) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
            maskImage: "radial-gradient(ellipse 80% 70% at 50% 50%, black 40%, transparent 100%)",
            WebkitMaskImage: "radial-gradient(ellipse 80% 70% at 50% 50%, black 40%, transparent 100%)",
          }}
        />

        <div className="relative">
          <div className="inline-block bg-surface border border-border px-3 py-1 text-[11px] font-bold text-subtle tracking-widest uppercase mb-6">
            Self-hosted · Open source · LAN-ready
          </div>

          <h1 className="text-5xl font-black leading-tight tracking-tight mb-6 m-0">
            AI memory for<br />
            <span className="text-accent">all your projects</span>
          </h1>

          <p className="text-lg text-muted max-w-xl mx-auto mb-8 leading-relaxed">
            BuildOS Knowledge Hub discovers every project on your machine, generates AI knowledge files,
            and exposes everything via search and MCP tools — so Claude always knows your codebase.
          </p>

          <div className="flex gap-3 justify-center flex-wrap mb-16">
            <Link
              href="/dashboard"
              className="px-6 py-3 text-white text-base font-semibold no-underline transition-opacity hover:opacity-90"
              style={{ background: "linear-gradient(to right, #4589ff, #0f62fe)" }}
            >
              Open Dashboard →
            </Link>
            <Link
              href="/search"
              className="px-6 py-3 border border-border text-muted text-base font-semibold no-underline hover:text-text hover:border-border-2 transition-colors"
            >
              Search projects
            </Link>
          </div>

          {/* Stats bar */}
          <div className="grid grid-cols-4 border-t border-b border-border divide-x divide-border">
            {[
              { label: "Search modes", value: "3" },
              { label: "LLM providers", value: "∞" },
              { label: "MCP tools", value: "5" },
              { label: "Deploy time", value: "< 5m" },
            ].map(({ label, value }) => (
              <div key={label} className="py-5">
                <div className="text-3xl font-black text-accent">{value}</div>
                <div className="text-xs text-muted mt-1">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works — animated flow */}
      <section className="max-w-6xl mx-auto px-8 py-16 border-t border-border">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-black tracking-tight mb-2">How it works</h2>
          <p className="text-muted text-sm">Five steps from raw code to Claude-queryable knowledge</p>
        </div>

        <FlowDiagram />

        {/* Step details */}
        <div className="mt-12 grid grid-cols-1 gap-px bg-border sm:grid-cols-5">
          {[
            {
              n: "01",
              title: "Discover",
              desc: "Worker scans SCAN_DIRECTORIES every 15 min. Detects language, framework, git URL from project markers.",
            },
            {
              n: "02",
              title: "Extract",
              desc: "Reads README, CLAUDE.md, package.json, Dockerfiles, and all nested markdown. Hash-deduped.",
            },
            {
              n: "03",
              title: "Generate OKF",
              desc: "LLM synthesizes an Operational Knowledge File — purpose, architecture, APIs, decisions.",
            },
            {
              n: "04",
              title: "Embed",
              desc: "Chunks text, generates 768-dim embeddings via Gemini text-embedding-004, stores in pgvector.",
            },
            {
              n: "05",
              title: "Query",
              desc: "Hybrid keyword + semantic search in UI. MCP server exposes same data to Claude Code.",
            },
          ].map((s) => (
            <div key={s.n} className="bg-bg p-5">
              <div className="text-xs font-black text-accent tracking-widest mb-2">{s.n}</div>
              <div className="text-sm font-bold text-text mb-2">{s.title}</div>
              <div className="text-xs text-muted leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-8 py-12 border-t border-border">
        <h2 className="text-xl font-bold mb-6 tracking-tight">Features</h2>
        <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-bg p-6 flex flex-col gap-3"
              style={{ borderTop: "2px solid var(--color-accent)" }}
            >
              <span className="text-3xl">{f.icon}</span>
              <h3 className="text-base font-bold m-0">{f.title}</h3>
              <p className="text-sm text-muted m-0 leading-relaxed">{f.desc}</p>
              <p className="text-xs text-subtle m-0 font-mono">{f.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Setup */}
      <section className="max-w-6xl mx-auto px-8 py-12 border-t border-border">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-black tracking-tight mb-2">Get started in 4 steps</h2>
          <p className="text-muted text-sm">Docker Compose gets everything running. No cloud required.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SETUP_STEPS.map((s) => (
            <div key={s.step} className="bg-surface border border-border p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 text-7xl font-black text-border/30 leading-none -mt-2 -mr-2 pointer-events-none select-none">
                {s.step}
              </div>
              <div className="flex items-center gap-3 mb-3">
                <span className="w-7 h-7 rounded-full bg-accent text-white text-xs font-bold flex items-center justify-center shrink-0">
                  {s.step}
                </span>
                <h3 className="text-sm font-semibold m-0">{s.title}</h3>
              </div>
              <pre className="bg-bg border border-border p-3 text-[11px] text-muted font-mono m-0 overflow-x-auto leading-relaxed whitespace-pre relative z-10">
                {s.code}
              </pre>
            </div>
          ))}
        </div>

        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-surface border border-border p-4 text-sm text-muted">
            <span className="text-text font-semibold block mb-1">📦 Prerequisites</span>
            Docker + Docker Compose · Git · (Optional) Gemini/OpenAI API key for OKF generation
          </div>
          <div className="bg-surface border border-border p-4 text-sm text-muted">
            <span className="text-text font-semibold block mb-1">🔑 Sync auth</span>
            Browse and search freely. Only re-index triggers (LLM calls) require Google sign-in.
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="max-w-6xl mx-auto px-8 py-12 border-t border-border">
        <h2 className="text-xl font-bold mb-6 tracking-tight">Tech stack</h2>
        <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map(({ label, value }) => (
            <div key={label} className="bg-bg px-5 py-4">
              <div className="text-[10px] font-bold text-accent uppercase tracking-widest mb-1">{label}</div>
              <div className="text-sm text-text">{value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 text-center border-t border-border">
        <h2 className="text-2xl font-black mb-3">Ready to index your projects?</h2>
        <p className="text-muted mb-6 text-sm">Clone, configure, deploy — AI memory layer up in minutes.</p>
        <div className="flex gap-3 justify-center flex-wrap">
          <Link
            href="/dashboard"
            className="px-8 py-3 text-white text-base font-semibold no-underline transition-opacity hover:opacity-90 inline-block"
            style={{ background: "linear-gradient(to right, #4589ff, #0f62fe)" }}
          >
            Go to Dashboard →
          </Link>
          <Link
            href="/search"
            className="px-8 py-3 border border-border text-muted text-base font-semibold no-underline hover:text-text hover:border-border-2 transition-colors inline-block"
          >
            Search projects
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 text-center">
        <div className="text-sm font-semibold text-text mb-1">BuildOS Knowledge Hub</div>
        <div className="text-xs text-subtle">
          Built by{" "}
          <span className="text-accent font-medium">BuildWithShashank</span>
          {" · "}Self-hosted AI memory{" · "}MIT License
        </div>
      </footer>
    </div>
  );
}
