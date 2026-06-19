"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, ProjectOut } from "@/lib/api";
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

function LangBadge({ lang }: { lang: string }) {
  const color = LANG_COLORS[lang.toLowerCase()] ?? "#6f6f6f";
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 border"
      style={{
        borderColor: `${color}40`,
        backgroundColor: `${color}12`,
        color,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: color }} />
      {lang}
    </span>
  );
}

function FrameworkBadge({ fw }: { fw: string }) {
  return (
    <span className="inline-flex items-center text-[11px] px-2 py-0.5 bg-surface-2 border border-border text-subtle font-mono">
      {fw}
    </span>
  );
}

function TechTag({ tag }: { tag: string }) {
  return (
    <span className="inline-flex items-center text-[11px] px-2 py-0.5 bg-surface border border-border text-subtle">
      {tag}
    </span>
  );
}

function ProjectCard({ p }: { p: ProjectOut }) {
  const initials = p.name
    .split(/[\s\-_]+/)
    .slice(0, 2)
    .map((w: string) => w[0]?.toUpperCase() ?? "")
    .join("");

  const topTech = p.technologies.slice(0, 3);
  const extraCount = p.technologies.length - 3;

  return (
    <Link
      href={`/projects/${p.slug}`}
      className="group flex flex-col gap-4 bg-surface border border-border p-5 no-underline transition-all hover:border-accent/50 hover:bg-surface-2"
    >
      {/* Card header */}
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div
          className="w-9 h-9 rounded-sm flex items-center justify-center text-xs font-bold text-accent shrink-0"
          style={{ backgroundColor: "rgba(69,137,255,0.12)", border: "1px solid rgba(69,137,255,0.25)" }}
        >
          {initials || "—"}
        </div>

        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-text group-hover:text-accent transition-colors truncate">
            {p.name}
          </div>
          {p.last_indexed_at ? (
            <div className="text-[11px] text-subtle mt-0.5">
              Indexed {new Date(p.last_indexed_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
            </div>
          ) : (
            <div className="text-[11px] text-subtle mt-0.5">Never indexed</div>
          )}
        </div>
      </div>

      {/* Language + framework badges */}
      <div className="flex flex-wrap gap-1.5">
        {p.language && <LangBadge lang={p.language} />}
        {p.framework && <FrameworkBadge fw={p.framework} />}
      </div>

      {/* Tech tags */}
      {topTech.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-auto">
          {topTech.map((t) => <TechTag key={t} tag={t} />)}
          {extraCount > 0 && (
            <span className="text-[11px] text-subtle self-center">+{extraCount}</span>
          )}
        </div>
      )}
    </Link>
  );
}

export default function ProjectsPage() {
  const [q, setQ] = useState("");
  const [language, setLanguage] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["projects", { q, language, page }],
    queryFn: () => api.getProjects({ q: q || undefined, language: language || undefined, page, size: 20 }),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / 20);

  return (
    <div className="page-container">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text m-0">Projects</h1>
        <span className="text-xs text-subtle bg-surface border border-border px-2.5 py-1">
          {data?.total ?? 0} total
        </span>
      </div>

      {/* Filter bar */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-subtle pointer-events-none"
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden
          >
            <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4" />
            <line x1="10" y1="10" x2="14" y2="14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            placeholder="Filter by name…"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            className="w-full bg-surface border border-border pl-9 pr-4 py-2.5 text-sm text-text placeholder:text-subtle outline-none focus:border-accent transition-colors"
          />
        </div>
        <select
          value={language}
          onChange={(e) => { setLanguage(e.target.value); setPage(1); }}
          className="bg-surface border border-border px-4 py-2.5 text-sm text-muted outline-none focus:border-accent cursor-pointer transition-colors appearance-none pr-8"
          style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236f6f6f' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center" }}
        >
          <option value="">All Languages</option>
          <option value="typescript">TypeScript</option>
          <option value="javascript">JavaScript</option>
          <option value="python">Python</option>
          <option value="go">Go</option>
          <option value="rust">Rust</option>
        </select>
      </div>

      {/* Card grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border p-5 h-40 animate-pulse" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <div className="border border-border bg-surface p-12 text-center">
          <div className="text-muted text-sm mb-3">No projects found.</div>
          <SyncAuthModal onConfirm={() => api.triggerFullIndex()}>
            {(trigger, disabled, reason) => (
              <button
                onClick={trigger}
                disabled={disabled}
                title={reason ?? undefined}
                className="text-accent text-sm bg-transparent border border-accent/30 px-4 py-1.5 cursor-pointer hover:bg-accent/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Trigger index
              </button>
            )}
          </SyncAuthModal>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {data.items.map((p) => (
            <ProjectCard key={p.slug} p={p} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 mt-6">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1.5 text-xs bg-surface border border-border text-muted disabled:opacity-40 cursor-pointer hover:bg-surface-2 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-muted px-3">
            Page <span className="text-text font-semibold">{page}</span> of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1.5 text-xs bg-surface border border-border text-muted disabled:opacity-40 cursor-pointer hover:bg-surface-2 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
