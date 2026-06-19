# 00 — Vision

## One-Line Positioning

**BuildOS Knowledge Hub** — A self-hosted AI memory system that continuously understands, indexes, and exposes every project, architecture decision, deployment, and AI workflow through search, graph relationships, and MCP tools.

---

## The Problem

Every developer with a homelab, multiple projects, and AI-assisted workflows faces the same failure:

- Claude forgets your stack between sessions
- Codex doesn't know how your projects relate
- You repeat context in every prompt
- No single source of truth across your local + homelab projects
- Architecture decisions exist only in your head

AI agents are powerful but **amnesiac**. They can reason, but cannot remember. BuildOS Knowledge Hub is the memory layer.

---

## The Solution

A continuously-running local service that:

1. **Discovers** every project on your machine and homelab
2. **Extracts** architecture, stack, decisions, APIs, deployments
3. **Generates** structured OKF (Operational Knowledge Files) per project
4. **Indexes** everything into keyword + vector + graph search
5. **Exposes** all knowledge via MCP tools to Claude, Codex, AGY, and any AI agent

---

## Core Value Propositions

| Value | Description |
|-------|-------------|
| **Zero-friction memory** | AI agents get full project context with one MCP call |
| **Always fresh** | File watcher + scheduled re-index keeps knowledge current |
| **Private by default** | Runs on your machine. No data leaves unless you choose |
| **Graph-aware** | Understands relationships between projects, not just content |
| **Universal AI interface** | One MCP server works with Claude, Codex, Cursor, AGY |

---

## Who It's For

- Developers managing 5-50+ local/homelab projects
- Teams using Claude Code, Codex, or AGY as primary AI assistants
- Anyone building a personal AI-native development workflow
- Homelab operators who want infrastructure awareness in their AI sessions

---

## What Success Looks Like

```
Claude: What projects in my homelab use FastAPI and Redis?

MCP → search({query: "FastAPI Redis", filters: {tech: ["fastapi", "redis"]}})

Claude: You have 3 projects using FastAPI + Redis:
- BuildOS (homelab, production)
- AuraStay HMS (active development, port 8001)
- Node Commander (archived)

BuildOS and AuraStay share the same ARQ job pattern. Want me to
show how AuraStay implements it so we can apply it to BuildOS?
```

That is the target experience.

---

## Non-Goals

- Not a GitHub replacement — no code hosting
- Not a CI/CD system — no build pipelines
- Not a package manager — no dependency resolution
- Not a cloud product — self-hosted only (Phase 1-3)
- Not a documentation generator for external audiences
