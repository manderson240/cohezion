# Cohezion Quick Start

> **Welcome to Cohezion!** This guide gets you productive in under 15 minutes.

---

## 📋 Prerequisites

- **Python**: 3.11 (required)
- **UV**: Package manager ([install](https://docs.astral.sh/uv/))
- **Ollama**: Local LLM runtime ([install](https://ollama.ai/))
- **SurrealDB**: Persistence layer (optional for basic usage)

---

## 🚀 Get Started

### 1. Clone & Install

```bash
git clone https://github.com/manderson240/cohezion.git
cd cohezion
uv sync
```

### 2. Quick Health Check

```bash
make lint          # Check code quality
make test-fast      # Run fast tests (under 1s each)
make type-check    # Run mypy type checking
```

### 3. Start the API

```bash
uv run uvicorn cohezion.api:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      COHEZION SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   FLUME      │  │  Compound    │  │  Ouroboros   │       │
│  │   VAE        │  │  Engineering │  │   Healing    │       │
│  │  (256D)      │  │   Engine     │  │  (Immune)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                    ┌───────┴───────┐                          │
│                    │   12D Universe │                          │
│                    │   Simulation  │                          │
│                    └───────────────┘                          │
│                            │                                  │
│                    ┌───────┴───────┐                          │
│                    │  Sovereign     │                          │
│                    │    Vault       │                          │
│                    └───────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **FLUME VAE** | 256D latent embedding | `src/cohezion/flume/` |
| **Compound Engineering** | Pattern accumulation | `src/cohezion/compound/` |
| **Ouroboros Healing** | Autonomous recovery | `src/cohezion/healing/` |
| **12D Universe** | Spatial-temporal simulation | `src/cohezion/universe/` |
| **Sovereign Vault** | Persistent memory | `cloud-vault-mcp/` |

---

## 📁 Project Structure

```
cohezion/
├── src/cohezion/          # Main source code
│   ├── agents/            # LLM agent implementations
│   ├── api/               # FastAPI endpoints (72+ routes)
│   ├── compound/          # Compound engineering engine
│   ├── core/              # Core infrastructure
│   ├── healing/           # Ouroboros immune system
│   ├── swarm/             # Multi-agent orchestration
│   └── universe/          # 12D simulation
├── tests/                 # Test suite
│   ├── fast/              # Unit tests (fast marker)
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── scripts/               # CI and utility scripts
├── _bmad/                 # BMAD workflow system
├── cloud-vault-mcp/      # Obsidian vault for MCP
└── _bmad-output/          # Generated artifacts
```

---

## 🔧 Common Commands

| Command | Purpose |
|---------|---------|
| `make lint` | Run ruff linter |
| `make format` | Auto-format code |
| `make test` | Run full test suite |
| `make test-fast` | Run fast unit tests only |
| `make type-check` | Run mypy type checking |
| `make all` | Run all CI checks |
| `uv run python scripts/ci/daily_health_check.py` | Health check |

---

## 🧪 Testing

```bash
# Run fast tests (under 1s each)
make test-fast

# Run specific module tests
uv run pytest tests/compound/ -v

# Run single test
uv run pytest tests/test_name.py::test_function -v

# Run integration tests (requires Ollama + SurrealDB)
uv run pytest -m integration -v
```

---

## 🔒 Security

Cohezion uses a "Red Wall" security model:

- **Constitutional Shield**: Blocks sensitive files from autonomous modification
- **Output Filter**: Redacts PII from model outputs
- **Forbidden Patterns**: System files protected from Ouroboros patches

Run security scan:
```bash
uv run bandit -r src/cohezion -f txt
```

---

## 📚 Documentation

| Resource | Location |
|----------|----------|
| **API Docs** | `http://localhost:8000/docs` |
| **AGENTS.md** | AI assistant guidelines |
| **Architecture** | `docs/architecture.md` |
| **Epic Progress** | `_bmad-output/planning-artifacts/` |
| **Security Report** | `_bmad-output/implementation-artifacts/SECURITY-REVIEW-REPORT.md` |

---

## 🐛 Troubleshooting

### Python Version Issues

```bash
# Check Python version
python --version  # Should be 3.13+

# If wrong version, install 3.13
uv python install 3.13
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall
```

### Test Failures

```bash
# Reset singleton state
# In conftest.py or manually:
cohezion.api._vae_trainer = None
cohezion.api._rl_policy = None
```

### Large Repository (Git Push Timeout)

```bash
# Use shallow push
git push --depth 50

# Or push specific files
git add <specific-files>
git commit -m "message"
git push
```

---

## 🤝 Contributing

1. Read `AGENTS.md` for AI assistant guidelines
2. Run `make all` before committing
3. Follow the BMAD workflow for feature development
4. Use `scripts/ci/daily_health_check.py` to verify health

---

## 📊 Health Monitoring

The daily health check provides visibility into codebase health:

```bash
# Run health check
uv run python scripts/ci/daily_health_check.py

# With JSON output
uv run python scripts/ci/daily_health_check.py --output json

# Attempt auto-fix
uv run python scripts/ci/daily_health_check.py --fix
```

Results are saved to:
- **Vault**: `cloud-vault-mcp/vault/daily/health-check-YYYY-MM-DD.md`
- **SurrealDB**: `health_check_record` table

---

## 🎯 Next Steps

1. **Explore the API**: Visit `/docs` endpoint
2. **Read Epic Documentation**: `_bmad-output/planning-artifacts/epics.md`
3. **Run a Simulation**: `uv run python scripts/drivers/universe_driver.py`
4. **Join Development**: Pick a story from `_bmad-output/implementation-artifacts/`

---

_Generated by BMAD Design Thinking Workflow • Updated 2026-03-04_