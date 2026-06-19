"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SyncAuthModal } from "@/components/SyncAuthModal";
import Link from "next/link";

const LANG_COLORS: Record<string, string> = {
  typescript: "#3178c6",
  javascript: "#f1e05a",
  python: "#3572a5",
  go: "#00add8",
  rust: "#dea584",
  ruby: "#701516",
  java: "#b07219",
  css: "#563d7c",
};

function LangDot({ lang }: { lang: string }) {
  const color = LANG_COLORS[lang.toLowerCase()] ?? "#6f6f6f";
  return (
    <span
      className="inline-block w-2 h-2 rounded-full shrink-0"
      style={{ backgroundColor: color }}
      title={lang}
    />
  );
}

// Inline SVG icons — no new deps
const STAT_META = [
  {
    key: "projects",
    label: "Projects",
    icon: (
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
        <rect x="1" y="3" width="6" height="10" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="9" y="6" width="6" height="7" rx="1" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    ),
  },
  {
    key: "documents",
    label: "Documents",
    icon: (
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
        <path d="M3 2h7l3 3v9H3V2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        <path d="M10 2v3h3" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        <line x1="5" y1="7" x2="11" y2="7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="5" y1="10" x2="9" y2="10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    key: "chunks",
    label: "Chunks",
    icon: (
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
        <rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    ),
  },
  {
    key: "embeddings",
    label: "Embeddings",
    icon: (
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
        <circle cx="3" cy="8" r="2" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="13" cy="4" r="2" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="13" cy="12" r="2" stroke="currentColor" strokeWidth="1.3" />
        <line x1="5" y1="7.2" x2="11" y2="4.8" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
        <line x1="5" y1="8.8" x2="11" y2="11.2" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    key: "relationships",
    label: "Relationships",
    icon: (
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
        <circle cx="8" cy="3" r="2" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="3" cy="13" r="2" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="13" cy="13" r="2" stroke="currentColor" strokeWidth="1.3" />
        <line x1="6.7" y1="4.6" x2="4.3" y2="11.4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
        <line x1="9.3" y1="4.6" x2="11.7" y2="11.4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
        <line x1="5" y1="13" x2="11" y2="13" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: api.getStats,
    refetchInterval: 30_000,
  });
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.getHealth,
    refetchInterval: 30_000,
  });
  const { data: projects } = useQuery({
    queryKey: ["projects", { size: 5 }],
    queryFn: () => api.getProjects({ size: 5, page: 1 }),
  });

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text m-0">Dashboard</h1>
        <p className="text-sm text-muted mt-1">System overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 mb-6 sm:grid-cols-3 lg:grid-cols-5">
        {STAT_META.map((s) => {
          const value = stats?.[s.key as keyof typeof stats];
          return (
            <div
              key={s.label}
              className="bg-surface border border-border p-4 flex flex-col gap-2"
              style={{ borderTop: "2px solid var(--color-accent)" }}
            >
              <span className="text-subtle">{s.icon}</span>
              <div className="text-3xl font-bold text-text leading-none">
                {statsLoading ? (
                  <span className="text-subtle">…</span>
                ) : (
                  (value ?? "—")
                )}
              </div>
              <div className="text-xs text-muted">{s.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Recent Projects */}
        <div className="lg:col-span-2 bg-surface border border-border p-5">
          <h2 className="text-sm font-semibold text-text mt-0 mb-4">Recent Projects</h2>
          <div className="divide-y divide-border">
            {projects?.items.map((p) => (
              <Link
                key={p.slug}
                href={`/projects/${p.slug}`}
                className="flex items-center justify-between py-3 text-sm no-underline hover:bg-surface-2 -mx-5 px-5 transition-colors group"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {p.language && <LangDot lang={p.language} />}
                  <span className="font-medium text-text truncate group-hover:text-accent transition-colors">
                    {p.name}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  {p.language && (
                    <span className="text-[10px] font-mono bg-surface-2 border border-border px-1.5 py-0.5 text-subtle uppercase tracking-wide">
                      {p.language}
                    </span>
                  )}
                  {p.framework && (
                    <span className="text-muted text-xs hidden sm:block">{p.framework}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-border">
            <Link href="/projects" className="text-accent text-xs hover:opacity-80 transition-opacity">
              View all projects →
            </Link>
          </div>
        </div>

        {/* System Status */}
        <div className="bg-surface border border-border p-5 flex flex-col">
          <h2 className="text-sm font-semibold text-text mt-0 mb-4">System Status</h2>
          <div className="divide-y divide-border flex-1">
            {health
              ? Object.entries(health.checks).map(([key, val]) => (
                  <div key={key} className="flex justify-between items-center py-2.5 text-xs">
                    <span className="text-muted capitalize">{key}</span>
                    <span
                      className={`flex items-center gap-1.5 font-mono ${
                        val === "ok" ? "text-success" : "text-error"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full inline-block ${
                          val === "ok" ? "bg-success" : "bg-error"
                        }`}
                      />
                      {val === "ok" ? "ok" : val}
                    </span>
                  </div>
                ))
              : (
                <div className="py-3 text-muted text-xs flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-subtle inline-block" />
                  Checking…
                </div>
              )}
          </div>

          <SyncAuthModal onConfirm={() => api.triggerFullIndex()}>
            {(trigger, disabled, reason) => (
              <button
                onClick={trigger}
                disabled={disabled}
                title={reason ?? undefined}
                className="mt-5 w-full py-2.5 text-xs font-semibold text-white transition-opacity border-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
                style={{ background: "linear-gradient(to right, #4589ff, #0f62fe)" }}
              >
                Trigger Full Re-index
              </button>
            )}
          </SyncAuthModal>
        </div>
      </div>

      {/* Search shortcut */}
      <Link
        href="/search"
        className="flex items-center gap-3 mt-4 bg-surface border border-border p-4 text-subtle text-sm no-underline hover:border-border-2 hover:text-muted transition-colors group"
      >
        <svg
          width="15"
          height="15"
          viewBox="0 0 16 16"
          fill="none"
          className="shrink-0"
          aria-hidden
        >
          <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4" />
          <line x1="10" y1="10" x2="14" y2="14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
        Search your knowledge base…
        <span className="ml-auto text-xs text-subtle font-mono hidden sm:block">⌘K</span>
      </Link>
    </div>
  );
}
