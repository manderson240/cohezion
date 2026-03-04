# Cohezion Architecture Overview

**Last Updated:** 2026-03-04  
**Version:** 15 Epics Active

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            COHEZION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        INTERACTION LAYER                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ FastAPI     │  │ Dashboard   │  │ CLI Tools   │  │ MCP Server │ │   │
│  │  │ (72+ routes)│  │ (Web UI)    │  │              │  │            │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        AGENT LAYER                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Scout Agent │  │ Critic Agent│  │ Lab Agent   │  │ Diplomat   │ │   │
│  │  │ (Research)  │  │ (Review)    │  │ (Testing)   │  │ (Comm)     │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Analyst     │  │ Architect   │  │ Designer    │  │ Narrator   │ │   │
│  │  │ (Analysis)  │  │ (Design)    │  │ (Creative)  │  │ (Story)    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      INTELLIGENCE LAYER                               │   │
│  │                                                                       │   │
│  │  ┌───────────────────┐    ┌───────────────────┐                       │   │
│  │  │   FLUME VAE       │    │  COMPOUND         │                       │   │
│  │  │   (256D Latent)   │◄──►│  ENGINEERING       │                       │   │
│  │  │   - Manifold       │    │  - Pattern Acc.    │                       │   │
│  │  │   - Physics       │    │  - Skill Refine   │                       │   │
│  │  │   - Temporal      │    │  - Guidance       │                       │   │
│  │  └───────────────────┘    └───────────────────┘                       │   │
│  │           │                          │                                │   │
│  │           │    ┌─────────────────────┘                                │   │
│  │           │    │                                                      │   │
│  │           ▼    ▼                                                      │   │
│  │  ┌───────────────────┐    ┌───────────────────┐                       │   │
│  │  │   12D UNIVERSE     │    │  OUROBOROS        │                       │   │
│  │  │   SIMULATION        │◄──►│  (HEALING)         │                       │   │
│  │  │   - Spatial (x,y,z)│    │  - Immune System  │                       │   │
│  │  │   - Time (t)        │    │  - Drift Det.     │                       │   │
│  │  │   - Physics        │    │  - Auto Patch     │                       │   │
│  │  │   - Biology        │    │  - Safety Gate    │                       │   │
│  │  │   - Logic          │    │  - Validation     │                       │   │
│  │  │   - Quantum        │    │                   │                       │   │
│  │  │   - Field          │    │                   │                       │   │
│  │  │   - Control        │    │                   │                       │   │
│  │  │   - Novelty        │    │                   │                       │   │
│  │  │   - Precipitation  │    │                   │                       │   │
│  │  │   - Spacetime      │    │                   │                       │   │
│  │  │   - Brane          │    │                   │                       │   │
│  │  └───────────────────┘    └───────────────────┘                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      INFRASTRUCTURE LAYER                             │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │ SurrealDB  │  │   Redis    │  │  Ollama    │  │  Sovereign     │  │   │
│  │  │ (Persist)  │  │  (Cache)   │  │  (LLM)     │  │  Vault (MCP)   │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │ Cost Router │  │ Swarm     │  │ Semantic   │  │ Security       │  │   │
│  │  │ (Routing)   │  │ Orchestr. │  │ Cache      │  │ Shield         │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Overview

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **FLUME VAE** | 256D latent space embedding | `src/cohezion/flume/` |
| **12D Universe** | Spatial-temporal simulation | `src/cohezion/universe/` |
| **Compound Engineering** | Pattern accumulation & skill refinement | `src/cohezion/compound/` |
| **Ouroboros Healing** | Autonomous system repair | `src/cohezion/healing/` |
| **Sovereign Vault** | Persistent knowledge store | `cloud-vault-mcp/` |
| **Swarm Orchestration** | Multi-agent coordination | `src/cohezion/swarm/` |
| **Cost Router** | Model routing optimization | `src/cohezion/swarm/cost_aware_router.py` |
| **Semantic Cache** | LLM response caching | `src/cohezion/cache/` |
| **Security Shield** | Constitutional protection | `src/cohezion/security/` |

---

## 🔄 Data Flow

```
User Request
     │
     ▼
┌─────────────┐     ┌─────────────┐
│  FastAPI    │────►│ Cost Router │────► Select Best Model
│  Endpoint   │     └─────────────┘
└─────────────┘
     │
     ▼
┌─────────────┐     ┌─────────────┐
│ Agent Layer │────►│ Semantic    │────► Cache Hit?
│             │     │ Cache       │        │
└─────────────┘     └─────────────┘        ▼
     │                                    Yes ──► Return Cached
     ▼                                    No ────► Continue
┌─────────────┐
│ LLM Call    │────► Ollama (Local) / API (Remote)
│             │
└─────────────┘
     │
     ▼
┌─────────────┐
│ Compound    │────► Pattern Matching + Skill Selection
│ Engine      │
└─────────────┘
     │
     ▼
┌─────────────┐
│ 12D Journey │────► Record trajectory in universe simulation
│ Recording   │
└─────────────┘
     │
     ▼
┌─────────────┐
│ Sovereign   │────► Persist learning to vault/SurrealDB
│ Vault       │
└─────────────┘
```

---

## 🗂️ Directory Structure

```
src/cohezion/
├── agents/          # LLM agent implementations
│   ├── base.py      # Base agent class
│   ├── scout.py     # Research agent
│   ├── critic.py    # Review agent
│   └── ...
├── api/             # FastAPI endpoints (72+ routes)
│   ├── app.py       # App factory
│   ├── routes*.py   # Route modules
│   └── ...
├── compound/        # Compound engineering engine
│   ├── executor.py  # Main executor
│   ├── skill_refiner.py
│   └── ...
├── core/            # Core infrastructure
│   ├── persistence/ # SurrealDB repositories
│   ├── time_keeper.py
│   └── ...
├── healing/         # Ouroboros immune system
│   ├── immune_system.py
│   ├── drift_analyzer.py
│   └── ...
├── flume/           # FLUME VAE
│   ├── autoencoder.py
│   └── ...
├── swarm/           # Multi-agent orchestration
│   ├── agent_factory.py
│   ├── cost_aware_router.py
│   └── ...
├── universe/        # 12D simulation
│   ├── engine.py
│   └── ...
└── security/        # Security infrastructure
    ├── output_filter.py
    ├── prompt_guard.py
    └── ...
```

---

## 🔗 Key Integrations

| Integration | Purpose | Protocol |
|------------|---------|----------|
| **Ollama** | Local LLM inference | HTTP API |
| **SurrealDB** | Graph + document database | WebSocket |
| **Redis** | Semantic caching | TCP |
| **Obsidian Vault** | Knowledge persistence | MCP |
| **HuggingFace** | Model weights | HTTP |

---

## 📈 Metrics & Observability

| Metric | Where to Find |
|--------|---------------|
| **Cost tracking** | `src/cohezion/core/credit_manager.py` |
| **Latency metrics** | Semantic cache + journey tracker |
| **Agent performance** | `src/cohezion/swarm/metrics.py` |
| **Health checks** | `scripts/ci/daily_health_check.py` |
| **Security scans** | `bandit -r src/cohezion` |

---

## 🛡️ Security Model

```
┌─────────────────────────────────────────┐
│          CONSTITUTIONAL SHIELD          │
├─────────────────────────────────────────┤
│                                         │
│  FORBIDDEN:                             │
│  • .agent/                              │
│  • .gemini/                             │
│  • security/                            │
│  • .env, .secrets                       │
│  • credentials, passwords               │
│  • CONSTITUTION.md                      │
│                                         │
│  OUTPUT FILTER:                         │
│  • PII detection & redaction           │
│  • Toxicity filtering                   │
│  • Insight packet synthesis             │
│                                         │
│  PATH TRAVERSAL:                        │
│  • Canonical path validation            │
│  • Subdirectory confinement             │
│                                         │
└─────────────────────────────────────────┘
```

---

_Generated by BMAD Design Thinking Workflow • Updated 2026-03-04_