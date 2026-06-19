// Auto-detect API base:
// - NEXT_PUBLIC_API_URL env var overrides everything (set for non-standard deployments)
// - HTTPS or no explicit port → same origin (nginx/caddy proxies /api at the public domain)
// - Explicit port (LAN access like :3100) → swap to :8010 on same host
function getBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (protocol === "https:" || !port || port === "80" || port === "443") {
      return `${protocol}//${hostname}`;
    }
    return `${protocol}//${hostname}:8010`;
  }
  return "http://localhost:8010";
}

const TOKEN_KEY = "buildos_access_token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

async function fetchJSON<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${getBase()}${path}`, { ...opts, headers });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export const api = {
  getProjects: (params?: Record<string, string | number | undefined>) => {
    const qs = params
      ? "?" + new URLSearchParams(
          Object.entries(params)
            .filter(([, v]) => v !== undefined)
            .map(([k, v]) => [k, String(v)])
        ).toString()
      : "";
    return fetchJSON<ProjectListOut>(`/api/projects${qs}`);
  },

  getProject: (slug: string) => fetchJSON<ProjectOut>(`/api/projects/${slug}`),

  getProjectOKF: (slug: string) =>
    fetchJSON<{ slug: string; name: string; okf: string | null; generated_at: string | null }>(`/api/projects/${slug}/okf`),

  getProjectDocuments: (slug: string) =>
    fetchJSON<DocumentListOut>(`/api/projects/${slug}/documents`),

  reindexProject: (slug: string, model?: string) =>
    fetchJSON<ReindexResponse>(`/api/projects/${slug}/reindex`, {
      method: "POST",
      body: JSON.stringify({ model: model ?? null }),
    }),

  search: (query: string, params?: Record<string, string | undefined>) => {
    const qs = new URLSearchParams({ q: query, ...params }).toString();
    return fetchJSON<SearchResponse>(`/api/search?${qs}`);
  },

  getStats: () => fetchJSON<Stats>(`/api/admin/stats`),
  getHealth: () => fetchJSON<Health>(`/api/admin/health`),
  getAvailableModels: () => fetchJSON<ModelsResponse>(`/api/admin/models`),
  triggerFullIndex: (model?: string) =>
    fetchJSON<ReindexResponse>(`/api/admin/index/full`, {
      method: "POST",
      body: JSON.stringify({ model: model ?? null }),
    }),
};

// Types
export interface ProjectOut {
  id: string;
  name: string;
  slug: string;
  path: string;
  language: string | null;
  framework: string | null;
  description: string | null;
  status: string;
  health_score: number | null;
  git_url: string | null;
  technologies: string[];
  metadata_: Record<string, unknown>;
  last_indexed_at: string | null;
  discovered_at: string;
}

export interface ProjectListOut {
  items: ProjectOut[];
  total: number;
  page: number;
  size: number;
}

export interface DocumentOut {
  id: string;
  project_id: string;
  type: string;
  title: string;
  path: string;
  content: string | null;
  word_count: number | null;
  updated_at: string;
}

export interface DocumentListOut {
  items: DocumentOut[];
  total: number;
}

export interface SearchResult {
  chunk_id: string;
  chunk_text: string;
  document_title: string;
  document_type: string;
  project_name: string;
  project_slug: string;
  score: number;
  score_breakdown: { keyword: number; semantic: number; graph: number };
  highlight: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  latency_ms: number;
  search_types_used: string[];
}

export interface Stats {
  projects: number;
  documents: number;
  chunks: number;
  embeddings: number;
  relationships: number;
}

export interface Health {
  status: string;
  checks: Record<string, string>;
  stats: Stats;
}

export interface ReindexResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ModelOption {
  id: string;
  provider: string;
  label: string;
}

export interface ModelsResponse {
  models: ModelOption[];
  default: string;
}
