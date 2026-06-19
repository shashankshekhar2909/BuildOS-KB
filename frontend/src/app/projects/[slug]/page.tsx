"use client";
import { useQuery } from "@tanstack/react-query";
import { useState, use } from "react";
import { api } from "@/lib/api";
import { SyncAuthModal } from "@/components/SyncAuthModal";
import { ModelSelector } from "@/components/ModelSelector";
import Link from "next/link";

const TABS = ["Overview", "Documents", "OKF"] as const;
type Tab = (typeof TABS)[number];

export default function ProjectDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [tab, setTab] = useState<Tab>("Overview");
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("");

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", slug],
    queryFn: () => api.getProject(slug),
  });

  const { data: okf } = useQuery({
    queryKey: ["project-okf", slug],
    queryFn: () => api.getProjectOKF(slug),
    enabled: tab === "OKF",
  });

  const { data: docs } = useQuery({
    queryKey: ["project-docs", slug],
    queryFn: () => api.getProjectDocuments(slug),
    enabled: tab === "Documents",
  });

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[40vh]">
        <div className="text-muted text-sm animate-pulse">Loading project…</div>
      </div>
    );
  }

  if (!project) {
    return <div className="page-container text-error text-sm">Project not found: {slug}</div>;
  }

  const gitUrl = project.git_url;
  const isGitHttp = gitUrl?.startsWith("http");
  const gitDisplay = gitUrl?.replace(/^https?:\/\//, "").replace(/\.git$/, "") ?? "—";

  return (
    <div className="page-container max-w-5xl">
      {/* Breadcrumb */}
      <Link href="/projects" className="text-accent text-xs no-underline hover:opacity-80 flex items-center gap-1 w-fit">
        ← All Projects
      </Link>

      {/* Header */}
      <div className="mt-4 mb-6 pb-6 border-b border-border">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-black text-text mt-0 mb-3 tracking-tight">{project.name}</h1>
            <div className="flex flex-wrap gap-1.5 items-center">
              {project.language && <Badge color="blue">{project.language}</Badge>}
              {project.framework && <Badge color="green">{project.framework}</Badge>}
              {project.technologies.slice(0, 6).map((t) => (
                <Badge key={t} color="gray">{t}</Badge>
              ))}
              <Badge color={project.status === "active" ? "green" : "gray"}>{project.status}</Badge>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <ModelSelector value={selectedModel} onChange={setSelectedModel} />
            <SyncAuthModal onConfirm={() => api.reindexProject(slug, selectedModel || undefined).then(() => alert("Re-index queued!"))}>
              {(trigger, disabled, reason) => (
                <button
                  onClick={trigger}
                  disabled={disabled}
                  title={reason ?? undefined}
                  className="px-4 py-2 text-xs font-semibold bg-accent text-white border-0 cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ↺ Re-index
                </button>
              )}
            </SyncAuthModal>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted">
          <span className="font-mono truncate max-w-xs">{project.path}</span>
          {gitUrl && (
            isGitHttp ? (
              <a
                href={gitUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent no-underline hover:opacity-80 flex items-center gap-1"
              >
                ⎇ {gitDisplay} ↗
              </a>
            ) : (
              <span className="font-mono">⎇ {gitDisplay}</span>
            )
          )}
          {project.last_indexed_at && (
            <span>Indexed {new Date(project.last_indexed_at).toLocaleString()}</span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border mb-6 gap-0">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-medium border-0 cursor-pointer transition-colors bg-transparent ${
              tab === t
                ? "text-text border-b-2 border-accent -mb-px"
                : "text-muted hover:text-text"
            }`}
          >
            {t}
            {t === "Documents" && docs && (
              <span className="ml-1.5 text-[10px] bg-surface-2 text-subtle px-1.5 py-0.5 rounded-full">
                {docs.total}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "Overview" && (
        <div className="grid gap-4 md:grid-cols-2">
          <InfoCard title="Project details">
            <Row label="Language" value={project.language ?? "—"} />
            <Row label="Framework" value={project.framework ?? "—"} />
            <Row label="Health score" value={project.health_score !== null ? `${project.health_score}/100` : "—"} />
            <Row label="Last indexed" value={project.last_indexed_at ? new Date(project.last_indexed_at).toLocaleString() : "Never"} />
            <Row label="Discovered" value={project.discovered_at ? new Date(project.discovered_at).toLocaleString() : "—"} />
          </InfoCard>

          <div className="flex flex-col gap-4">
            {gitUrl && (
              <InfoCard title="Repository">
                <div className="py-3">
                  {isGitHttp ? (
                    <a
                      href={gitUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent text-sm no-underline hover:opacity-80 font-mono break-all flex items-center gap-2"
                    >
                      <span className="text-lg">⎇</span>
                      <span>{gitDisplay}</span>
                      <span className="text-xs shrink-0">↗</span>
                    </a>
                  ) : (
                    <span className="text-muted text-xs font-mono break-all">{gitUrl}</span>
                  )}
                </div>
              </InfoCard>
            )}

            {Object.keys(project.metadata_ ?? {}).length > 0 && (
              <InfoCard title="Metadata">
                {Object.entries(project.metadata_).map(([k, v]) => (
                  <Row key={k} label={k} value={JSON.stringify(v)} />
                ))}
              </InfoCard>
            )}
          </div>
        </div>
      )}

      {/* Documents */}
      {tab === "Documents" && (
        <div className="flex flex-col gap-2">
          {!docs ? (
            <div className="text-muted text-sm animate-pulse">Loading documents…</div>
          ) : docs.items.length === 0 ? (
            <div className="py-12 text-center text-muted text-sm border border-border bg-surface">
              No documents extracted yet.
            </div>
          ) : (
            docs.items.map((doc) => {
              const isOpen = expandedDoc === doc.id;
              return (
                <div key={doc.id} className="border border-border bg-surface overflow-hidden">
                  <button
                    onClick={() => setExpandedDoc(isOpen ? null : doc.id)}
                    className="w-full px-4 py-3 flex justify-between items-center cursor-pointer bg-transparent border-0 hover:bg-surface-2 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-accent text-base shrink-0">{docIcon(doc.type)}</span>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-text truncate">{doc.title}</div>
                        <div className="text-[11px] text-muted font-mono truncate">{doc.path}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-3">
                      <Badge color="gray">{doc.type}</Badge>
                      {doc.word_count && (
                        <span className="text-[11px] text-subtle hidden sm:block">{doc.word_count.toLocaleString()} words</span>
                      )}
                      <span className={`text-subtle text-xs transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}>
                        ▾
                      </span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="border-t border-border">
                      {doc.content ? (
                        <pre className="p-4 text-xs text-muted font-mono leading-relaxed overflow-auto max-h-[60vh] whitespace-pre-wrap break-words bg-bg m-0">
                          {doc.content}
                        </pre>
                      ) : (
                        <div className="p-4 text-sm text-muted text-center">No content available.</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* OKF */}
      {tab === "OKF" && (
        <div>
          {!okf?.okf ? (
            <div className="bg-surface border border-border p-12 text-center">
              <div className="text-4xl mb-4">📄</div>
              <div className="text-text font-semibold mb-2">No OKF generated yet</div>
              <div className="text-muted text-sm mb-5">Trigger a re-index to generate the Operational Knowledge File using AI.</div>
              <div className="flex items-center gap-2 justify-center">
                <ModelSelector value={selectedModel} onChange={setSelectedModel} />
                <SyncAuthModal onConfirm={() => api.reindexProject(slug, selectedModel || undefined).then(() => alert("Re-index queued!"))}>
                  {(trigger, disabled, reason) => (
                    <button
                      onClick={trigger}
                      disabled={disabled}
                      title={reason ?? undefined}
                      className="px-5 py-2 bg-accent text-white text-sm font-semibold border-0 cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      ↺ Trigger re-index
                    </button>
                  )}
                </SyncAuthModal>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted">Generated {okf.generated_at ? new Date(okf.generated_at).toLocaleString() : ""}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(okf.okf!)}
                  className="text-xs text-accent bg-transparent border-0 cursor-pointer hover:opacity-80"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-surface border border-border p-6 overflow-auto font-mono text-sm leading-relaxed text-text whitespace-pre-wrap break-words rounded-none">
                {okf.okf}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function docIcon(type: string): string {
  const map: Record<string, string> = {
    readme: "📖", okf: "🤖", plan: "📋", architecture: "🏗️",
    claude_md: "🧠", dockerfile: "🐳", docker_compose: "🐳",
    package_json: "📦", pyproject: "🐍", requirements: "🐍",
    go_mod: "🔵", cargo_toml: "🦀", markdown: "📄",
    todo: "✅", env_example: "⚙️",
  };
  return map[type] ?? "📄";
}

function Badge({ children, color = "green" }: { children: React.ReactNode; color?: "green" | "blue" | "gray" }) {
  const cls = {
    green: "bg-success/10 text-success border-success/20",
    blue: "bg-accent/10 text-accent border-accent/20",
    gray: "bg-surface-2 text-muted border-border",
  }[color];
  return (
    <span className={`border px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>
      {children}
    </span>
  );
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border p-4">
      <h3 className="text-[10px] font-bold text-muted uppercase tracking-widest mt-0 mb-3">{title}</h3>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between items-center py-2 text-sm gap-4">
      <span className="text-muted shrink-0">{label}</span>
      <span className={`text-right truncate text-text ${mono ? "font-mono text-xs" : ""}`}>
        {value}
      </span>
    </div>
  );
}
