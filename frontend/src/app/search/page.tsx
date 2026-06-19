"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";

// Deterministic accent hue per project name — keeps avatars stable across renders
function projectColor(name: string): string {
  const palette = [
    "#4589ff", // blue
    "#42be65", // green
    "#ff7eb6", // pink
    "#be95ff", // purple
    "#82cfff", // light-blue
    "#f1c21b", // yellow
    "#ff8389", // red
    "#3ddbd9", // teal
  ];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff;
  return palette[h % palette.length];
}

function ProjectAvatar({ name }: { name: string }) {
  const initials = name
    .split(/[\s\-_]+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("") || "??";
  const color = projectColor(name);

  return (
    <div
      className="w-8 h-8 rounded-sm flex items-center justify-center text-[11px] font-bold shrink-0"
      style={{ backgroundColor: `${color}18`, border: `1px solid ${color}35`, color }}
      aria-hidden
    >
      {initials}
    </div>
  );
}

function DocTypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    readme: "README",
    okf: "OKF",
    changelog: "CHANGELOG",
    config: "config",
    source: "source",
    markdown: "md",
  };
  return (
    <span className="inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 bg-accent/10 border border-accent/20 text-accent/80 uppercase tracking-wide">
      {labels[type?.toLowerCase()] ?? type}
    </span>
  );
}

function ScorePill({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  // colour shifts: < 60 subtle, 60-80 muted, 80+ accent
  const cls =
    pct >= 80
      ? "bg-accent/15 border-accent/30 text-accent"
      : pct >= 60
      ? "bg-surface-2 border-border-2 text-muted"
      : "bg-surface border-border text-subtle";
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 border rounded-full ${cls}`}>
      {pct}%
    </span>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selected, setSelected] = useState<number>(-1);
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["search", debouncedQuery],
    queryFn: () => api.search(debouncedQuery),
    enabled: debouncedQuery.length > 2,
  });

  const results = data?.results ?? [];

  const handleChange = (val: string) => {
    setQuery(val);
    setSelected(-1);
    clearTimeout((window as unknown as Record<string, unknown>).__searchTimeout as ReturnType<typeof setTimeout>);
    (window as unknown as Record<string, unknown>).__searchTimeout = setTimeout(() => setDebouncedQuery(val), 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!results.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, -1));
    } else if (e.key === "Enter" && selected >= 0) {
      e.preventDefault();
      router.push(`/projects/${results[selected].project_slug}`);
    }
  };

  return (
    <div className="page-container">
      <h1 className="text-2xl font-bold text-text mb-6">Search</h1>

      {/* Search input */}
      <div className="relative mb-5">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 text-subtle pointer-events-none"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden
        >
          <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
          <line x1="10" y1="10" x2="14" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          placeholder="Search projects, documents, decisions…"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          className="w-full bg-surface border-2 border-accent pl-11 pr-4 py-3 text-text text-base outline-none placeholder:text-subtle"
        />
        {debouncedQuery.length > 2 && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[11px] text-subtle select-none">
            ↑↓ navigate · Enter to open
          </span>
        )}
      </div>

      {/* Meta row */}
      {debouncedQuery.length > 2 && (
        <div className="flex items-center gap-3 text-xs text-muted mb-5">
          {isLoading ? (
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-subtle inline-block animate-pulse" />
              Searching…
            </span>
          ) : (
            <>
              <span>{data?.total ?? 0} results</span>
              <span className="text-border">·</span>
              <span>{data?.latency_ms ?? 0}ms</span>
              {(data?.search_types_used ?? []).map((t) => (
                <span
                  key={t}
                  className="px-1.5 py-0.5 bg-surface-2 border border-border text-[10px] text-subtle font-mono uppercase tracking-wide"
                >
                  {t}
                </span>
              ))}
            </>
          )}
        </div>
      )}

      {/* Results */}
      <div className="flex flex-col gap-2">
        {results.map((r, i) => (
          <Link
            key={r.chunk_id}
            href={`/projects/${r.project_slug}`}
            className={`block no-underline border p-4 transition-all cursor-pointer ${
              i === selected
                ? "border-accent bg-accent/5"
                : "border-border bg-surface hover:border-border-2 hover:bg-surface-2"
            }`}
            onMouseEnter={() => setSelected(i)}
            onMouseLeave={() => setSelected(-1)}
          >
            {/* Result header */}
            <div className="flex items-start gap-3 mb-2.5">
              <ProjectAvatar name={r.project_name} />

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-0.5">
                  <span className="font-semibold text-sm text-text truncate">{r.document_title}</span>
                  {r.document_type && <DocTypeBadge type={r.document_type} />}
                </div>
                <span className="text-accent text-xs font-medium">{r.project_name}</span>
              </div>

              <div className="shrink-0 ml-2">
                <ScorePill score={r.score} />
              </div>
            </div>

            {/* Excerpt */}
            <p
              className="m-0 text-sm text-muted leading-relaxed line-clamp-3 pl-11"
              dangerouslySetInnerHTML={{
                __html: r.highlight || r.chunk_text.slice(0, 280) + "…",
              }}
            />

            {/* Score breakdown + nav hint */}
            <div className="mt-2.5 pl-11 flex items-center gap-3">
              <div className="flex gap-3 text-[11px] text-subtle">
                {r.score_breakdown.keyword > 0 && (
                  <span>kw {Math.round(r.score_breakdown.keyword * 100)}%</span>
                )}
                {r.score_breakdown.semantic > 0 && (
                  <span>sem {Math.round(r.score_breakdown.semantic * 100)}%</span>
                )}
              </div>
              {i === selected && (
                <span className="ml-auto text-[11px] text-accent font-medium">Open project →</span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {/* Empty states */}
      {debouncedQuery.length > 2 && !isLoading && !results.length && (
        <div className="text-center py-16 text-muted text-sm">
          No results for &quot;{debouncedQuery}&quot;. Try a broader query or trigger a re-index.
        </div>
      )}
      {debouncedQuery.length <= 2 && (
        <div className="text-center py-16 text-muted text-sm">
          Type at least 3 characters to search across all projects.
        </div>
      )}
    </div>
  );
}
