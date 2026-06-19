# 08 — AI Services

## LiteLLM Gateway

Single interface to all LLM providers. Configured as a local proxy or used directly via the SDK.

### Provider Configuration

```yaml
# litellm_config.yaml
model_list:
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: claude-haiku-4-5
    litellm_params:
      model: anthropic/claude-haiku-4-5-20251001
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: gemini-flash
    litellm_params:
      model: gemini/gemini-2.0-flash
      api_key: os.environ/GEMINI_API_KEY

  - model_name: groq-fast
    litellm_params:
      model: groq/llama-3.1-8b-instant
      api_key: os.environ/GROQ_API_KEY

  - model_name: text-embedding-3-small
    litellm_params:
      model: openai/text-embedding-3-small
      api_key: os.environ/OPENAI_API_KEY
```

### Model Routing by Task

| Task | Model | Reason |
|------|-------|--------|
| OKF generation | `claude-sonnet-4-6` | Best reasoning, follows structured format |
| Architecture summary | `claude-sonnet-4-6` | Nuanced understanding of codebases |
| Health check report | `groq-fast` | Simple check, fast feedback |
| Similar project detection | `claude-haiku-4-5` | Pattern matching, cheap at scale |
| Embeddings | `text-embedding-3-small` | Cost-efficient, high quality |

### Python Client Setup

```python
import litellm

litellm.api_base = settings.LITELLM_BASE_URL  # local proxy

async def call_llm(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        num_retries=3,
        fallbacks=[{"model": "claude-haiku-4-5"}],
    )
    return response.choices[0].message.content
```

---

## AI Feature 1: OKF Generation

**Purpose:** Produce a structured `buildos.okf.md` for each project.

**Input:** Project metadata + extracted document contents.

**Prompt:**
```python
OKF_SYSTEM = """
You are a senior software architect analyzing codebases.
Generate a structured OKF (Operational Knowledge File) in Markdown.
Be factual — only include information present in the documents.
Be concise — each section should be scannable in 30 seconds.
Format code exactly as shown.
"""

OKF_USER_TEMPLATE = """
Project Name: {name}
Path: {path}
Language: {language}
Framework: {framework}
Git URL: {git_url}

=== DOCUMENTS ===

{documents}

=== END DOCUMENTS ===

Generate the OKF file in this exact format:

# {name}

## Purpose
[1-2 sentences. What does this project do and why does it exist?]

## Architecture
[Bullet list: key components, how they connect, data flow summary]

## Stack
[Comma-separated: language, framework, key libraries, databases, infrastructure]

## Key APIs
[List of important endpoints or exported interfaces. Format: METHOD /path — description]

## Ports
[Service → port mapping]

## Environment Variables
[Required vars. Format: VAR_NAME — description]

## Commands
```
dev: [command to start development]
build: [command to build]
test: [command to run tests]
deploy: [command to deploy]
```

## Deployment
[How and where this runs: Docker, homelab, cloud, local only]

## Key Decisions
[Architecture decisions and the reason behind them]

## Related Projects
[Other projects this depends on, integrates with, or shares patterns with]
"""
```

**Post-processing:**
- Validate all required sections present
- If section missing, use `"[Not documented]"` placeholder
- Write to `{project_path}/buildos.okf.md`
- Store in DB with content hash

---

## AI Feature 2: Architecture Summary

**Purpose:** Generate a human-readable architecture summary from scattered documentation.

**Trigger:** Called from Project Detail → Architecture tab when no `ARCHITECTURE.md` exists.

**Prompt:**
```python
ARCH_SYSTEM = """
You are a technical writer. Generate a clear architecture summary from the provided
project files. Focus on system components, data flow, and key design decisions.
Output plain Markdown. Max 500 words.
"""

ARCH_USER_TEMPLATE = """
Project: {name} ({language} / {framework})

Documents:
{documents}

Generate a structured architecture summary with:
1. System overview (2-3 sentences)
2. Component diagram (ASCII)
3. Data flow (numbered steps)
4. Key design decisions (bullet list)
"""
```

---

## AI Feature 3: Project Health Report

**Purpose:** Identify what a project is missing (docs, tests, architecture, Docker).

**Trigger:** Scheduled hourly, or on demand via API.

**Logic (rule-based first, LLM for summary):**

```python
class HealthChecker:
    CHECKS = [
        ("has_readme", "README.md present", 15),
        ("has_architecture", "ARCHITECTURE.md present", 10),
        ("has_claude_md", "CLAUDE.md present", 10),
        ("has_tests", "Test directory present", 20),
        ("has_docker", "Dockerfile or docker-compose.yml present", 10),
        ("has_env_example", ".env.example present", 10),
        ("has_git", ".git directory present", 5),
        ("recent_commit", "Committed within 30 days", 10),
        ("has_description", "Project description in README", 5),
        ("has_okf", "buildos.okf.md generated", 5),
    ]

    def compute_score(self, project: Project, documents: list[Document]) -> HealthReport:
        doc_types = {d.type for d in documents}
        score = 0
        passed = []
        missing = []

        for check_id, description, weight in self.CHECKS:
            if self._run_check(check_id, project, doc_types):
                score += weight
                passed.append(description)
            else:
                missing.append(description)

        return HealthReport(score=score, passed=passed, missing=missing)
```

**LLM summary** (Groq fast model):
```
Given this project health report, write a 2-sentence summary of the
project's documentation health and the most important thing to fix.
```

---

## AI Feature 4: Similar Project Detection

**Purpose:** Find projects that share architectural patterns, not just technologies.

**Trigger:** Run after OKF generation for all projects.

**Approach:**
1. Embed each project's OKF using `text-embedding-3-small`
2. Compute pairwise cosine similarity between project OKF embeddings
3. If similarity > 0.75 → create `SHARES_PATTERN` relationship
4. For top-5 most similar pairs, ask LLM to explain the shared pattern

**LLM explanation prompt:**
```python
SIMILAR_SYSTEM = "You are a software architect identifying code patterns."

SIMILAR_USER = """
Project A: {okf_a}

Project B: {okf_b}

These projects have architectural similarity. In one sentence, describe
the specific pattern or approach they share.
"""
```

---

## Cost Management

| Operation | Model | Est. tokens | Est. cost |
|-----------|-------|-------------|-----------|
| OKF generation | claude-sonnet-4-6 | ~3k in, ~1k out | ~$0.02 |
| Architecture summary | claude-sonnet-4-6 | ~4k in, ~800 out | ~$0.025 |
| Health report summary | groq-fast | ~500 in, ~100 out | ~$0.0001 |
| Embedding (per document chunk) | text-embedding-3-small | ~512 tokens | ~$0.00001 |

**Cost guardrails:**
- Redis rate limiter: max 10 OKF generations per hour
- Only regenerate OKF when source documents change (hash check)
- Embedding batch size: 100 chunks per API call (reduces overhead)
- Health summaries cached for 24h per project
