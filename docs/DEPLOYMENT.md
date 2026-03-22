# Cohezion Deployment Model

## Architecture: Hybrid Local/Remote

Cohezion uses a hybrid deployment model with local GitLab as the source of truth and GitHub for selected public components.

## Repositories

### Primary: GitLab CE (Local)
- **URL**: `http://localhost:8929/root/cohezion`
- **Remote name**: `origin`
- **Role**: Source of truth for all development, CI/CD, and private code
- **Branches**: `main`, `develop`, feature branches

### Public Components: GitHub
- **`manderson240/cohezion`**: Legacy mirror. **Read-only** — do NOT push full repo.
- **`/home/mike-anderson/dev/public-repos/llm-prompt-guard`**: Apache 2.0 licensed
- **`/home/mike-anderson/dev/public-repos/ollama-debate`**: Apache 2.0 licensed

Public components are maintained as separate repositories with independent dependency management. Code flows from cohezion → public-repos via manual extraction, not automated sync.

### ML Models: Ollama (Local)
- `deepseek-r1:70b` — primary reasoning model
- `qwen3-coder:30b` — code generation
- `phi3:mini` — fast structured output

Global concurrency limit: 4 simultaneous Ollama requests.

## CI/CD

### GitLab CI (`.gitlab-ci.yml`)
7 stages: lint → validate → test → compound → typecheck → security → deploy

- **Runner**: Shell executor at `~/.local/bin/gitlab-runner`
- **Config**: `clone_url = "http://localhost:8929"` (avoids DNS issues)
- **Cache**: uv + pip caches shared across jobs
- **Artifacts**: JUnit XML reports, coverage

### Pre-commit Hooks (`.pre-commit-config.yaml`)
- **Commit stage** (fast, ~3-5s): ruff format check, syntax errors, trailing whitespace
- **Push stage** (thorough): full ruff lint with auto-fix, mypy type checking

### GitHub Actions (`.github/workflows/lint.yml`)
Minimal — ruff + mypy on PRs only. Not the primary CI system.

## Services

### Cloud Vault MCP Server
- **Port**: 8360
- **Transport**: Streamable HTTP (FastMCP)
- **Vault path**: `~/vaults/cohezion-vault/`
- **Endpoint**: `POST /mcp` (no trailing slash)
- **Protocol**: JSON-RPC 2.0 over SSE, MCP 2024-11-05

Start: `cd cloud-vault-mcp && uv run python -m mcp_server.main`

### SurrealDB
- **Role**: Journey persistence, simulation data
- **Auth**: `USE NS cohezion DB core` + root:root
- **Fallback**: JSONL files at `data/journeys/`

## Cost Guardrails

- **Cloud Run**: Free Tier only — no paid compute
- **Ollama**: Local inference only — no cloud API calls for routine operations
- **Anthropic API**: Reserved for inbox processor and specific compound tasks

## Branching Strategy

```
main ← feature branches (PR-based merge)
develop ← integration branch (97 commits ahead of origin)
```

Feature branches: `feature/<name>`, `fix/<name>`, `style/<name>`, `docs/<name>`

## Hardware

- AMD Ryzen AI MAX+ 395, 128GB LPDDR5X
- Radeon 8060S iGPU (integrated, NOT discrete)
- GTT memory: 128GB (`mem_info_gtt_total`, not `mem_info_vram_total`)
