# 05 — Frontend Spec

## Stack

- **Next.js 15** — App Router, React 19
- **TypeScript** — strict mode
- **Carbon Design System** (`@carbon/react`) — IBM's component library
- **React Query v5** (`@tanstack/react-query`) — data fetching + cache
- **React Flow** (`@xyflow/react`) — graph visualization
- **Zustand** — lightweight global state (filters, UI state)
- **axios** or native `fetch` — HTTP client (wrap in API layer)

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout, providers, Carbon theme
│   ├── page.tsx                # Dashboard (redirect or home)
│   ├── dashboard/
│   │   └── page.tsx            # Dashboard stats + recent activity
│   ├── projects/
│   │   ├── page.tsx            # Projects list
│   │   └── [slug]/
│   │       ├── page.tsx        # Project detail (tab routing)
│   │       ├── layout.tsx      # Tabs layout
│   │       ├── overview/
│   │       │   └── page.tsx
│   │       ├── architecture/
│   │       │   └── page.tsx
│   │       ├── knowledge/
│   │       │   └── page.tsx
│   │       ├── files/
│   │       │   └── page.tsx
│   │       └── graph/
│   │           └── page.tsx
│   ├── search/
│   │   └── page.tsx            # Universal search
│   ├── explorer/
│   │   └── page.tsx            # Knowledge explorer (browse all docs)
│   └── graph/
│       └── page.tsx            # Global graph view
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx        # Sidebar + header wrapper
│   │   ├── Sidebar.tsx         # Carbon SideNav
│   │   └── Header.tsx          # Carbon Header with search
│   ├── projects/
│   │   ├── ProjectCard.tsx
│   │   ├── ProjectTable.tsx
│   │   ├── ProjectBadge.tsx    # Language/framework badges
│   │   ├── HealthBadge.tsx
│   │   └── TechStack.tsx
│   ├── search/
│   │   ├── SearchBox.tsx
│   │   ├── SearchResults.tsx
│   │   ├── SearchResult.tsx    # Single result card
│   │   └── SearchFilters.tsx
│   ├── graph/
│   │   ├── KnowledgeGraph.tsx  # React Flow wrapper
│   │   ├── ProjectNode.tsx     # Custom React Flow node
│   │   └── TechNode.tsx
│   └── common/
│       ├── StatCard.tsx
│       ├── CodeBlock.tsx
│       ├── MarkdownRenderer.tsx
│       └── EmptyState.tsx
├── lib/
│   ├── api.ts                  # API client functions
│   ├── types.ts                # TypeScript interfaces
│   └── utils.ts
├── hooks/
│   ├── useProjects.ts
│   ├── useProject.ts
│   ├── useSearch.ts
│   └── useGraph.ts
└── stores/
    ├── searchStore.ts
    └── uiStore.ts
```

---

## Pages

### Dashboard (`/dashboard`)

**Purpose:** At-a-glance system health and recent activity.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ [42 Projects] [318 Documents] [4821 Embeddings] [156 Relationships] │
├─────────────────────────────────────────────────────┤
│ Recently Indexed                │ System Status     │
│ ─────────────────               │ ──────────────    │
│ BuildOS    2m ago               │ ● DB: OK          │
│ AuraStay   14m ago              │ ● Redis: OK       │
│ NodeCmdr   1h ago               │ ● Workers: OK     │
│                                 │ ● LiteLLM: OK     │
├─────────────────────────────────────────────────────┤
│ Tech Breakdown                                       │
│ TypeScript ████████████ 18      Python ████████ 12  │
│ Go ████ 6                       Rust ██ 3            │
└─────────────────────────────────────────────────────┘
```

**Data fetching:**
```tsx
const { data: stats } = useQuery({
  queryKey: ['admin', 'stats'],
  queryFn: () => api.getStats(),
  refetchInterval: 30_000,
})
```

---

### Projects List (`/projects`)

**Purpose:** Browse and filter all indexed projects.

**Layout:**
```
[Search projects...] [Language ▼] [Framework ▼] [Status ▼]

┌──────────────────────────────────────────────────────────────────┐
│ Name          │ Stack              │ Last Scan   │ Health │ Docs  │
├──────────────────────────────────────────────────────────────────┤
│ BuildOS       │ TS · Next.js       │ 2m ago      │ ●85    │ 12    │
│ AuraStay HMS  │ PY · FastAPI       │ 14m ago     │ ●72    │ 8     │
│ Node Cmdr     │ GO · Gin           │ 1h ago      │ ●91    │ 5     │
└──────────────────────────────────────────────────────────────────┘
```

**Component:** Carbon `DataTable` with custom renderers.

**Filtering:** Zustand store for active filters, React Query for data. Filter changes invalidate query.

---

### Project Detail (`/projects/[slug]`)

Tabbed layout. Tabs: Overview | Architecture | Knowledge | Files | Graph

#### Overview Tab
- Project name, language, framework, path, git URL
- Description (from OKF Purpose section)
- Technology badges
- Health score gauge
- Quick stats: document count, chunk count, relationship count
- "Re-index" action button → calls `POST /api/projects/{slug}/reindex`

#### Architecture Tab
- Rendered Markdown from ARCHITECTURE.md (if exists)
- Fallback: Architecture section from OKF
- Component: `MarkdownRenderer` with syntax highlighting

#### Knowledge Tab
- All extracted documents as accordion cards
- Each card: document title, type badge, word count, last updated
- Click to expand → show full document content
- Show parsed metadata for `package.json`, `docker-compose.yml`

#### Files Tab
- List of all extracted files with type, path, hash
- Last indexed timestamp per file
- Button to view raw content

#### Graph Tab
- React Flow mini-graph: this project + 2-hop neighbors
- Node types: ProjectNode (blue), TechNode (green)
- Edge labels: relationship type
- Click node → navigate to that project or filter by tech

---

### Search (`/search`)

**Purpose:** Universal knowledge search — like Notion / Cursor memory search.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ 🔍 Search everything...                              │
│ [Keyword] [Semantic] [Graph] [All ▼]                 │
└──────────────────────────────────────────────────────┘

Showing 12 results for "FastAPI Redis"  (145ms)

┌──────────────────────────────────────────────────────┐
│ ARCHITECTURE.md  ·  BuildOS                          │
│ ...ARQ is a **Redis**-backed async job queue...      │
│ Keyword: 0.72  Semantic: 0.91  [Open Project]        │
├──────────────────────────────────────────────────────┤
│ CLAUDE.md  ·  AuraStay HMS                           │
│ ...Uses FastAPI + Redis for session management...    │
│ Keyword: 0.65  Semantic: 0.83  [Open Project]        │
└──────────────────────────────────────────────────────┘
```

**Behavior:**
- Debounced input: 300ms delay before firing query
- URL-driven: `?q=...&type=...` — shareable links
- Real-time results via React Query with `keepPreviousData`
- Highlight matched terms in result snippets

---

### Graph View (`/graph`)

**Purpose:** Visual map of all projects and their relationships.

**Implementation:**
- React Flow canvas
- Nodes: ProjectNode (custom) with name, framework badge, health indicator
- Edges: labeled with relationship type (USES, DEPENDS_ON, DEPLOYS)
- Controls: zoom, fit view, minimap
- Click node → side panel with project summary
- Filter panel: show only selected technologies or relationship types

**Initial layout:** `dagre` or `elk` auto-layout algorithm

---

## API Client (`lib/api.ts`)

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const api = {
  getProjects: (params?: ProjectListParams) =>
    fetch(`${BASE}/api/projects?${qs(params)}`).then(r => r.json()),

  getProject: (slug: string) =>
    fetch(`${BASE}/api/projects/${slug}`).then(r => r.json()),

  getProjectOKF: (slug: string) =>
    fetch(`${BASE}/api/projects/${slug}/okf`).then(r => r.json()),

  search: (query: string, filters?: SearchFilters) =>
    fetch(`${BASE}/api/search?${qs({q: query, ...filters})}`).then(r => r.json()),

  getGraph: () =>
    fetch(`${BASE}/api/graph/nodes`).then(r => r.json()),

  getProjectGraph: (slug: string) =>
    fetch(`${BASE}/api/graph/project/${slug}`).then(r => r.json()),

  getStats: () =>
    fetch(`${BASE}/api/admin/stats`).then(r => r.json()),

  reindexProject: (slug: string) =>
    fetch(`${BASE}/api/projects/${slug}/reindex`, {method: 'POST'}).then(r => r.json()),

  triggerFullIndex: () =>
    fetch(`${BASE}/api/admin/index/full`, {method: 'POST'}).then(r => r.json()),
}
```

---

## TypeScript Types (`lib/types.ts`)

```typescript
interface Project {
  id: string
  name: string
  slug: string
  path: string
  language: string | null
  framework: string | null
  description: string | null
  status: 'active' | 'archived' | 'error'
  health_score: number | null
  technologies: string[]
  last_indexed_at: string | null
  metadata: {
    ports?: number[]
    docker?: boolean
    git_url?: string
    git_branch?: string
  }
}

interface Document {
  id: string
  project_id: string
  type: string
  title: string
  path: string
  content: string | null
  word_count: number | null
  parsed_data: Record<string, unknown> | null
  updated_at: string
}

interface SearchResult {
  type: 'chunk'
  chunk_text: string
  document_title: string
  document_type: string
  project_name: string
  project_slug: string
  score: number
  score_breakdown: {
    keyword: number
    semantic: number
    graph: number
  }
  highlight: string
}

interface GraphNode {
  id: string
  type: 'project' | 'technology'
  label: string
  data: Project | Technology
}

interface GraphEdge {
  id: string
  source: string
  target: string
  label: string  // relationship type
  weight: number
}
```

---

## State Management

**React Query** for all server state. Cache keys follow: `['entity', 'id/filter']`.

**Zustand** for UI-only state:
```typescript
// searchStore.ts
interface SearchStore {
  query: string
  filters: SearchFilters
  searchType: 'all' | 'keyword' | 'semantic' | 'graph'
  setQuery: (q: string) => void
  setFilters: (f: Partial<SearchFilters>) => void
  setSearchType: (t: SearchStore['searchType']) => void
}

// uiStore.ts
interface UIStore {
  sidebarOpen: boolean
  selectedProjectSlug: string | null
  setSidebarOpen: (open: boolean) => void
  setSelectedProject: (slug: string | null) => void
}
```

---

## Carbon Theme Setup

```tsx
// app/layout.tsx
import { Theme } from '@carbon/react'

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Theme theme="g100">  {/* dark theme */}
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </Theme>
      </body>
    </html>
  )
}
```

Use `g10` for light, `g100` for dark. Provide theme toggle in header.
