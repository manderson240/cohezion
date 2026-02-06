# Cohezion Hybrid Deployment

Three-tier deployment strategy: proprietary source of truth, curated public showcase, ML artifact distribution.

## Architecture

```
Tier 1: Local GitLab CE (source of truth)
  http://localhost:8929/root/cohezion
  All code, all branches, full history.
  Docker container on Strix Halo workstation.

Tier 2: GitHub (public showcase)
  Separate repos per open-source component:
  ├── manderson240/llm-prompt-guard    (Apache 2.0)
  ├── manderson240/ollama-debate       (Apache 2.0)
  ├── manderson240/flume-encoder       (Apache 2.0, after training)
  └── manderson240/agentic-reliability (Apache 2.0)

Tier 3: Hugging Face + Ollama (ML artifacts)
  ├── HF: Trained FLUME autoencoder weights + model card
  ├── HF: Attack pattern dataset (from security module)
  └── Ollama: Custom Modelfiles for agent personas
```

## Git Remotes

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `http://localhost:8929/root/cohezion.git` | Source of truth (GitLab CE) |
| `github` | `https://github.com/manderson240/cohezion.git` | Legacy (do NOT push full repo here) |

## GitLab CE Setup

Container: `gitlab/gitlab-ce:latest`
Port: 8929 (HTTP), 2224 (SSH)
Data: `/home/mike-anderson/gitlab/{config,logs,data}`

```bash
# Start GitLab
docker start gitlab

# Stop GitLab
docker stop gitlab

# View logs
docker logs gitlab --tail 50

# Root password (first boot only)
docker exec gitlab cat /etc/gitlab/initial_root_password

# Web UI
open http://localhost:8929
```

## Public Component Extraction

Components are extracted from the monorepo into standalone packages at `/home/mike-anderson/dev/public-repos/`. Each has its own git history, README, license, and tests.

### Tier 1 (released)
- **llm-prompt-guard**: Regex-based prompt injection detection, 130+ attack patterns, OWASP LLM Top 10
- **ollama-debate**: Multi-agent democratic debate system, 7 personas, voting + consensus

### Tier 2 (after cleanup)
- **flume-encoder**: HuggingFace-compatible thought autoencoder + Rust bindings
- **agentic-reliability**: Circuit breaker + AMD iGPU resource monitor

### Not Released
- VLIW optimizer: Anthropic copyright restrictions on challenge code
- Webapp: Too tightly coupled to extract
- Full monorepo: Proprietary (source available, all rights reserved)

## Credential Management

GitLab credentials stored via `git credential store` at `~/.git-credentials`.
Token: `glpat-*` (personal access token, expires in 365 days).
Regenerate: GitLab Web UI > Profile > Access Tokens.
