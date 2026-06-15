# Cohezion Compound AI Enterprise Pipeline on Band

**Band of Agents Hackathon — Multi-Agent Software Development Track**
Built by [@manderson240](https://github.com/manderson240) | Deadline: June 19, 2026

---

## What It Does

Three specialized Cohezion agents coordinate via Band to deliver an **Enterprise AI Code Review Pipeline** — receiving a user task, decomposing it, enriching it with semantic context from a knowledge vault, and synthesizing a production-ready implementation with SkillRefiner updates.

Every state transition, handoff, and artifact flows through **Band as the active coordination layer**. Agents never communicate directly — Band is the bus.

---

## Architecture

```
User Task
    │
    ▼
┌─────────────────────────────────────┐
│         OrchestratorAgent           │  ← NPU tier (llama3.2-1b-FLM, 42 TPS)
│  • Task classification              │    claude-haiku-4-5
│  • Phase decomposition              │
│  • Risk flag identification         │
└──────────────┬──────────────────────┘
               │ POST artifact: "plan"
               ▼
        ┌─────────────┐
        │  Band       │  ← Active coordination layer
        │  Channel    │    All state lives here
        │  #pipeline  │    Agents read/write artifacts
        └─────────────┘
               │ GET artifact: "plan"
               ▼
┌─────────────────────────────────────┐
│           AnalystAgent              │  ← iGPU tier (deepseek-r1-0528-8b, ~200ms)
│  • SemanticCache lookup             │    claude-sonnet-4-5
│    (FLUME VAE 256D, L1/L2/L3)      │
│  • Risk analysis                    │
│  • Implementation hints             │
└──────────────┬──────────────────────┘
               │ POST artifact: "enriched_context"
               ▼
        ┌─────────────┐
        │  Band       │
        │  Channel    │
        │  #pipeline  │
        └─────────────┘
               │ GET artifact: "enriched_context"
               ▼
┌─────────────────────────────────────┐
│           EngineerAgent             │  ← CPU tier (Gemma-4-31B, ~800ms)
│  • Implementation synthesis         │    claude-sonnet-4-5
│  • Code patches + tests             │
│  • SkillRefiner updates             │
│  • CompoundExecutor loop closure    │
└──────────────┬──────────────────────┘
               │ POST artifact: "implementation"
               ▼
        ┌─────────────┐
        │  Band       │
        │  Channel    │
        └─────────────┘
               │
               ▼
        Final Result
```

---

## Unique Differentiators

### 1. AMD Silicon Inference ($0 per compound loop)
Maps each agent to a Cohezion inference tier running on AMD Strix Halo:
| Agent | Cohezion Tier | Silicon | Cost |
|-------|--------------|---------|------|
| Orchestrator | NPU (13306) | XDNA2, 42 TPS | $0 |
| Analyst | iGPU (13307) | RDNA 3.5 | $0 |
| Engineer | CPU (13309) | Ryzen AI MAX+ | $0 |

A 10K-token enterprise review loop costs **$0.00** on local silicon vs **$0.18** on Sonnet.

### 2. FLUME VAE Semantic Context
The Analyst uses Cohezion's **FLUME VAE** (256D latent space) to encode task descriptions and search the knowledge vault for similar patterns. 95%+ cache hit rate on seen patterns means the pipeline gets smarter with every run.

### 3. Self-Improving Compound Loop
The Engineer triggers **SkillRefiner** after every implementation — extracting reusable patterns back into the skill library. Each pipeline run makes the next one faster and more accurate.

### 4. Band as Active Coordination (not a thin wrapper)
- Agent **discovery** via Band channel roster
- **State persistence** via Band artifact history
- **Handoff protocol**: typed artifacts (`plan` → `enriched_context` → `implementation`)
- **Local simulation mode**: full coordination semantics without credentials, using file-persisted state at `~/.cohezion/band_sim_state.json`

---

## Setup

### Prerequisites
- Python 3.11+
- Anthropic API key
- (Optional) Band API credentials — use promo code **BANDHACK26** for Band Pro
- (Optional) Cohezion local inference stack (see `COHEZION_SRC` below)

### Install

```bash
cd ~/cohezion-labs/band-of-agents
pip install -r requirements.txt
# Or with uv:
uv pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
# ANTHROPIC_API_KEY=sk-ant-...
# BAND_API_KEY=...  (optional — pipeline works without it)
```

### Run the Demo

```bash
# With the sample task (FastAPI rate limiting)
python demo/run_demo.py

# With verbose artifact output
python demo/run_demo.py -v

# With a custom task
python demo/run_demo.py "Add JWT refresh token rotation to our Express.js API"

# From a task file
python demo/run_demo.py --task-file demo/sample_task.md
```

---

## What You'll See

```
══════════════════════════════════════════════
  Cohezion Compound AI Enterprise Pipeline
══════════════════════════════════════════════

Integration Status:
  Band mode: LOCAL
  Cohezion package: online
  Lemonade NPU: online
  ...

──── Agent 1/3: Orchestrator (NPU tier — Task Classification) ────
  [Band:local] cohezion-orchestrator → posted 'plan' to #enterprise-pipeline
  ✓ Plan posted to Band in 1.2s
  ✓ Complexity: MEDIUM
  ✓ Phases: 4
  ✓ Risk flags: 3

──── Agent 2/3: Analyst (iGPU tier — Semantic Enrichment) ────
  [Band:local] cohezion-analyst → posted 'enriched_context' to #enterprise-pipeline
  ✓ Enriched context posted in 2.1s
  ✓ High risks: 2
  ✓ Similar patterns found: 1
  ✓ FLUME VAE encoding applied

──── Agent 3/3: Engineer (CPU tier — Implementation Synthesis) ────
  [Band:local] cohezion-engineer → posted 'implementation' to #enterprise-pipeline
  ✓ Implementation posted in 3.8s
  ✓ Code patches: 5
  ✓ Confidence score: 87%
  ✓ Skill updates extracted: 1

══════════════════════════════════════════════
  Pipeline Complete (7.1s total)
══════════════════════════════════════════════
```

---

## File Structure

```
band-of-agents/
├── README.md              # This file
├── requirements.txt       # Dependencies
├── .env.example           # Credential template
├── agent_config.yaml      # Agent + pipeline configuration
├── prompts/
│   ├── orchestrator.md    # Orchestrator role prompt
│   ├── analyst.md         # Analyst role prompt
│   └── engineer.md        # Engineer role prompt
├── agents/
│   ├── orchestrator_agent.py   # Task classification + planning
│   ├── analyst_agent.py        # Semantic enrichment
│   └── engineer_agent.py       # Implementation synthesis
├── shared/
│   ├── band_client.py          # Band API client (live + local sim)
│   └── cohezion_bridge.py      # Cohezion inference integration
└── demo/
    ├── run_demo.py             # End-to-end demo runner
    └── sample_task.md          # Example: FastAPI rate limiting
```

---

## Band Integration Details

### How Band Serves as the Active Coordination Layer

Band is not a thin message queue here — it's the **single source of truth** for pipeline state:

1. **Agent Discovery**: Agents register themselves via their `AGENT_ID` on every artifact post. The channel roster shows who's active.

2. **Typed Artifacts**: Each stage posts a semantically typed artifact (`plan`, `enriched_context`, `implementation`). Downstream agents pull the specific type they need — no routing logic required.

3. **State Persistence**: The full artifact history is preserved in Band, enabling replay, audit, and debugging of any pipeline run.

4. **Handoff Protocol**: Each agent's `run()` method starts with `band.get_artifact(upstream_type)` and ends with `band.post_artifact(my_type, result)`. Band enforces the sequencing.

5. **Local Simulation**: When `BAND_API_KEY` is unset, `BandClient` falls back to a file-persisted in-process dict at `~/.cohezion/band_sim_state.json` — same API, same coordination semantics, zero infrastructure.

### Band API Endpoints Used

| Operation | Band Endpoint |
|-----------|--------------|
| Post artifact | `POST /v1/workspaces/{id}/channels/{id}/artifacts` |
| Get latest artifact | `GET /v1/workspaces/{id}/channels/{id}/artifacts/latest?artifact_type=plan` |
| Channel history | `GET /v1/workspaces/{id}/channels/{id}/artifacts` |

---

## Hackathon Track

**Multi-Agent Software Development** — Enterprise code review pipeline demonstrating:
- 3 specialized agents with distinct roles and inference tiers
- Band as active coordination hub for all state and handoffs
- Real Cohezion semantic cache integration (FLUME VAE)
- Self-improving compound loop via SkillRefiner
- Graceful degradation without credentials (local simulation mode)

Use promo code **BANDHACK26** for Band Pro access.
