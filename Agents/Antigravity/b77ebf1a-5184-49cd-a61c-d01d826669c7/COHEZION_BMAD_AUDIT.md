---
type: antigravity-artifact
session_id: b77ebf1a-5184-49cd-a61c-d01d826669c7
date: 2026-03-04
title: "Cohezion Codebase Audit - BMAD Integration"
tags: [agent-output, antigravity, codebase-audit, bmad]
aspect: doer
neural:
  activation: 0.627
  stage: growing
  cluster: Agents
---

# 🔍 COHEZION CODEBASE AUDIT — BMAD Integration & Compound Engineering Levers

_Date: 2026-03-02 | Scope: Full Codebase + BMAD Integration_

---

## 1. WHAT THE CODEBASE CLAIMS VS. WHAT IS REAL

### ✅ Claims That Are TRUE and Well Implemented

| Claim                                       | Evidence                                                                         | Quality             |
| ------------------------------------------- | -------------------------------------------------------------------------------- | ------------------- |
| 136+ skills in `src/cohezion/skills/`       | Verified: 136 `.md` files across all domains                                     | ✅ Rich             |
| Compound module (session, skill, thermal)   | 72 files, 427 public exports in `__init__.py`                                    | ✅ Deep             |
| FLUME encoder / morphospace                 | 26 files incl. `autoencoder.py`, `persistent_homology.py`, `morphospace.py`      | ✅ Sophisticated    |
| Autonomous skill registration via Ouroboros | `registry/skill_manager.py` — cryptographic provenance, Triune diffs, hot reload | ✅ Industrial-grade |
| SurrealDB journey persistence               | `compound/surreal_journey_repository.py`, `compound/journey_tracker.py`          | ✅ Functional       |
| Hardware-aware routing (AMD/128GB)          | `compound/hardware_monitor.py` + `swarm/hardware_aware_router.py`                | ✅ Present          |
| Vault integration (security, provenance)    | `security/provenance.py`, `vault/`, `compound/vault_search_executor.py`          | ✅ Layered          |

### ⚠️ Claims PARTIALLY True (Shallow/Incomplete)

| Claim                                       | Reality                                                                                                      | Gap                                  |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| "BMAD fully integrated" (`BMAD_ALIGNED.md`) | `orchestrator/bmad_integration.py` uses `subprocess.run()` to shell into `cohezion.py` — no programmatic API | Shell bridge, not deep integration   |
| "BMAD agents in manifest"                   | 3 agent `.md` files created, registered in CSV; but no Python binding to swarm agents                        | Persona files, not live agent wiring |
| "Workflows created"                         | Workflow YAMLs present but not connected to `compound/CompoundSession` or `swarm/team_orchestrator.py`       | YAML stubs, not active pipelines     |
| `skills/bmad_workflow.md` integration table | Maps BMAD concepts → Cohezion equivalents (conceptually correct) but no bridge code executes these mappings  | Doc-only mapping                     |
| `orchestrator/core/event_bus.py`            | File exists but not imported anywhere in `compound/` or `swarm/`                                             | Dead wiring                          |

### ❌ Unverified / Likely Aspirational

| Claim                                    | Status                                                                                                   |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Cross-session BMAD⟷Cohezion state sync   | No runtime evidence; event_bus.py has no consumers in production code                                    |
| "BMAD can trigger Cohezion workflows"    | Only via `subprocess.run(["python3","cohezion.py","security"])` — no graceful failure, no result routing |
| Cron-based BMAD task scheduling          | Generated but never activated; no systemd unit or crontab install step                                   |
| Unified KV cache visible to BMAD session | `compound/kv_cache_tracker.py` exists but BMAD has no read path to it                                    |

---

## 2. THE KEY STRUCTURAL GAP

```
┌─────────────────────────────────────────────────────────┐
│                    BMAD Layer                           │
│  _bmad/bmm/  _bmad/gds/  _bmad/tea/  _bmad/cis/       │
│  agents/*.md  workflow.yaml  config.yaml                │
│                   ↕ ONLY via                            │
│          subprocess("python3 cohezion.py ...")          │
└─────────────────────────────────────────────────────────┘
                         ↕ Gap: no bidirectional API
┌─────────────────────────────────────────────────────────┐
│               Cohezion Core Layer                       │
│  compound/CompoundSession  swarm/team_orchestrator      │
│  registry/AutonomousSkillRegistrar                      │
│  flume/FlumeEncoder  physics/dimension_extractor        │
│  vault/  healing/  reliability/                         │
└─────────────────────────────────────────────────────────┘
```

**The gap is one clean interface:** BMAD workflows need to call `CompoundSession.execute()` or `TeamOrchestrator.run()` directly — not shell out to a CLI.

---

## 3. COMPOUND ENGINEERING LEVERS — Ranked by Impact/Effort

### 🔴 LEVER 1: BMADSession → CompoundSession Bridge (HIGH IMPACT · MEDIUM EFFORT)

**What it unlocks:** Every BMAD workflow gets full Cohezion swarm intelligence — skill selection, token routing, thermal prediction, journey capture — automatically.

```python
# New file: orchestrator/bmad_session_bridge.py
from cohezion.compound import CompoundSession, SessionConfig
from cohezion.swarm import TeamOrchestrator

class BMADSessionBridge:
    """Programmatic bridge: BMAD workflow step → CompoundSession"""
    def execute_workflow_step(self, step: dict) -> dict:
        session = CompoundSession(config=SessionConfig(
            skill_name=step["skill"],
            model=step.get("model", "auto"),
        ))
        return session.run(step["prompt"])
```

**Where to place:** `orchestrator/bmad_session_bridge.py`, imported in all `_bmad/*/workflows/*.yaml` via a loader.

---

### 🔴 LEVER 2: BMAD Workflow → SkillSelector Auto-routing (HIGH IMPACT · LOW EFFORT)

**Current state:** BMAD workflows hardcode which agent/model to use.  
**Lever:** Route every BMAD step through `compound/skill_selector.py` → `swarm/smart_router.py`.

```python
# Just 3 lines in bmad_integration.py
from cohezion.compound import SkillSelector
selector = SkillSelector()
best_skill = selector.select(task_description=step["description"])
```

This makes every BMAD step **self-routing** — token burn drops because the cheapest capable model is always chosen.

---

### 🟡 LEVER 3: Knowledge Graph ↔ BMAD \_memory Sync (HIGH IMPACT · MEDIUM EFFORT)

**What it unlocks:** `_bmad/_memory/` sidecars become queryable via Cohezion's vault + embedding search.

```
_bmad/_memory/cohezion-integration/ ──→ cohezion.vault.embedding_model.embed()
                                     ──→ SurrealDB vector store
                                     ──→ compound.VaultSearchExecutor.search()
```

**One lever to pull:** Add a `BMadMemorySync` task to `compound/schedulers.py` that runs every 10 min, embedding all `_bmad/_memory/**/*.md` files into SurrealDB.

---

### 🟡 LEVER 4: Ouroboros Cycle → BMAD Story Auto-generation (COMPOUND MULTIPLIER)

**The magic:** When `AutonomousSkillRegistrar.register_on_ouroboros_complete()` fires, emit a BMAD story artifact automatically.

```python
# In registry/skill_manager.py, after registration succeeds:
bmad_story = BMADStoryFactory.from_skill(registered_skill)
bmad_story.write_to("data/universe/")
```

Every skill improvement auto-creates a BMAD story → epic traceability is maintained with **zero human effort**.

---

### 🟡 LEVER 5: FLUME Encoder → BMAD Intent Classifier (ELEGANT + TOKEN-SAVING)

**What it unlocks:** Instead of sending full BMAD prompt text to an LLM to classify intent, run it through `flume/FlumeEncoder` locally → 256-dim z-vector → nearest-neighbor skill lookup.

```python
# Replace LLM call with local FLUME
from cohezion.flume.encoder_v2 import FlumeEncoder
from cohezion.compound import SkillSelector

encoder = FlumeEncoder()
z = encoder.encode(user_prompt)  # local, ~2ms
skill = SkillSelector().select_from_vector(z)  # no LLM token burn
```

**Token burn reduction estimate:** ~60-80% on skill routing decisions.

---

### 🟢 LEVER 6: Event Bus → BMAD Async Trigger (LOW EFFORT · HIGH ELEGANCE)

**Current:** `orchestrator/core/event_bus.py` exists but has no consumers.  
**Fix:** Wire `healing/` and `compound/degradation_detector.py` events to the event bus. BMAD workflow steps subscribe to `"skill.degraded"` and auto-trigger investigation workflows.

```python
bus = get_event_bus()
bus.subscribe("skill.degraded", lambda e: trigger_bmad_workflow("self-heal", e))
bus.subscribe("ouroboros.complete", lambda e: sync_bmad_story(e))
```

---

### 🟢 LEVER 7: Compound Hardware Monitor → BMAD Concurrency Advisor (QUICK WIN)

**What it unlocks:** Before BMAD runs a parallel workflow step, check `HardwareMonitor.get_metrics()` and downgrade concurrency if thermal throttling is detected.

```python
hw = get_hardware_monitor()
if hw.get_metrics().cpu_temp > 85:
    concurrency = 2  # throttle
```

This prevents the crashes seen in overnight runs.

---

## 4. THE THREE ELEGANT UNIFYING PATTERNS

### Pattern A: Cohezion as BMAD's "Nervous System"

Every BMAD agent is a **persona stub** — its actual intelligence is Cohezion.

```
BMAD Agent Persona ──→ BMADSessionBridge ──→ CompoundSession ──→ Swarm/Skills/Cache
```

The agent `.md` files become **intent declarations**, not implementations.

### Pattern B: Skills as Universal Currency

Skills are already the shared vocabulary (`skills/bmad_workflow.md` maps BMAD patterns to skill equivalents). The leverage is making this mapping **executable**, not just documented.

```
BMAD Workflow Step name ──→ SkillSelector.select() ──→ registered skill ──→ execute
```

### Pattern C: Journey Capture as BMAD Retrospective

Every `CompoundSession` journey is already stored. Wire `JourneyTracker` summary output to BMAD's `/retrospective` workflow automatically.

---

## 5. WHAT TO AVOID (Anti-patterns Found)

| Anti-Pattern                               | Location                                         | Risk                                                          |
| ------------------------------------------ | ------------------------------------------------ | ------------------------------------------------------------- |
| `subprocess.run()` for cross-system calls  | `orchestrator/bmad_integration.py` L152          | No error propagation, no streaming, timeout-only failure mode |
| YAML workflow steps with no Python backing | `_bmad/bmm/workflows/cohezion/`                  | Invisible failures — silently skip                            |
| Manual cron injection                      | `generate_cron_entries()` in bmad_integration.py | Never activated unless human installs it                      |
| 991,610+ files in `data/` dir              | `data/`                                          | Git-unsafe, IDE-crippling — move to SurrealDB blobs           |
| Duplicate router files                     | `compound/cost_aware_router*.py` (4 files)       | Confusion about which is canonical                            |

---

## 6. PRIORITY SPRINT MAP

```
Sprint 1 (30 min): LEVER 2 — SkillSelector in BMADIntegration
  → Wire SkillSelector into execute_task() in orchestrator/bmad_integration.py
  → Test: python3 orchestrator/bmad_integration.py --execute cohezion-security-check

Sprint 2 (30 min): LEVER 6 — Event Bus consumers
  → Add compound/degradation_detector.py → bus.publish("skill.degraded", ...)
  → Add healing/get_healing_system() → bus.subscribe consumer

Sprint 3 (60 min): LEVER 1 — BMADSessionBridge
  → New: orchestrator/bmad_session_bridge.py
  → Replace subprocess in execute_task() with BMADSessionBridge.execute()
  → All BMAD tasks now get full compound session tracking

Sprint 4 (30 min): LEVER 4 — Ouroboros → BMAD Story
  → Add BMADStoryFactory call in registry/skill_manager.py
  → Epic traceability goes autonomous

Sprint 5 (60 min): LEVER 3 — Memory Sync
  → scheduler that embeds _bmad/_memory/ → SurrealDB
  → BMAD agent context becomes searchable via VaultSearchExecutor
```

---

## 7. SYSTEM COHERENCE SCORE (Honest Assessment)

| Dimension                     | Score    | Notes                                                   |
| ----------------------------- | -------- | ------------------------------------------------------- |
| Cohezion Core depth           | 9/10     | Compound, flume, registry are industrial-grade          |
| BMAD-Cohezion integration     | 3/10     | CLI subprocess only; no programmatic bridge             |
| Skill coverage                | 8/10     | 136 skills; most well-formed; some stubs                |
| Journey/memory persistence    | 7/10     | SurrealDB wiring works; \_bmad/\_memory not connected   |
| Token efficiency              | 6/10     | SmartRouter + semantic cache present; not wired to BMAD |
| Compound engineering leverage | 5/10     | Parts are compound; BMAD → Cohezion path is not         |
| **Overall COHEZION**          | **6/10** | Strong engine, weak transmission                        |

> **The project has a Formula 1 engine connected to the drivetrain via a garden hose.**  
> Levers 1–3 replace the garden hose with a proper driveshaft.

---

## 8. SINGLE MOST IMPORTANT FILE TO CREATE NEXT

**`src/cohezion/bmad/bridge.py`** — a thin adapter that:

1. Accepts a BMAD workflow step dict
2. Routes it through `SkillSelector` → `CompoundSession`
3. Returns structured result back to BMAD
4. Registers the journey in `SurrealJourneyRepository`
5. Publishes event to `event_bus`

This single file closes 4 of the 7 gaps above. It is the **keystone**.

## Related Vault Notes

- [[cohezion]]
- [[agent-architecture]]
- [[surrealdb]]
