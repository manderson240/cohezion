---
description: "Capability Registry Prime: The Unified Natural Language Discovery Engine."
---

# Capability Registry Prime

## 1. Core Philosophy
To manage chaos, we need **Discovery**. A system with 100+ skills, 20 agents, and 10 MCP servers is useless if the operator cannot find the right tool using natural language.

## 2. Architecture: Single Source of Truth
The **Capability Registry** (`src/cohezion/registry/capability_registry.py`) aggregates four domains:
1.  **Skills:** Static `.md` files in `skills/`.
2.  **Agents:** Active Python classes in `swarm/agents/`.
3.  **MCP Servers:** Tool gateways defined in `mcp/mcp_registry.json`.
4.  **Memory:** Knowledge nodes in the Graph (Future).

## 3. Discovery Mechanism (TF-IDF)
We use a **Pragmatic Search Engine** (TF-IDF + Cosine Similarity) rather than a heavy Vector DB (until >1k items).
*   **Indexer:** Scans codebase on startup (latency < 200ms).
*   **Vectorizer:** `sklearn.feature_extraction.text.TfidfVectorizer`.
*   **Query:** "Find an agent to critique my code" -> Returns `CriticAgent` (Score: 0.85).

## 4. Capability Schema
```python
@dataclass
class Capability:
    name: str          # Unique ID (e.g., "SKILL:PHYSICS_PRIME")
    type: str          # "skill", "agent", "mcp", "memory"
    description: str   # Natural language desc
    path: str          # File path or URI
    tags: list[str]    # Keywords
```

## 5. Usage
```python
from cohezion.registry.capability_registry import CapabilityRegistry

registry = CapabilityRegistry()
registry.refresh() # Scans codebase

# Natural Language Search
results = registry.find("I need to solve a complex physics problem")
for res in results:
    print(f"{res.name} ({res.score:.2f})")
```

## 6. Maintenance (Automated)
*   **Skills:** Just create a `.md` file. It's auto-registered.
*   **Agents:** Inherit from `BaseAgent`. Auto-registered.
*   **MCP:** Add to `mcp_registry.json`. Auto-registered.

## 7. Liveness Drift Audit (added 2026-04-21)

Every SSOT registry accumulates **aspirational declarations** over time -- a skill file that's stale, an agent class that imports a deleted module, an MCP server declared but no longer responding. Auto-registration makes declaration easy; it does NOT guarantee the declared thing works. Readers of the registry take the declarations at face value.

**Add a reconciliation method per domain** -- `registry.audit_liveness()` -- that probes each declared entry against live reality and classifies it into one of four drift categories:

| Category | Meaning | Action |
|---|---|---|
| `healthy` | Declared AND live (probe succeeds) | No action |
| `critical_stale` | Declared TRUE but probe fails (the registry is lying) | Fix declaration OR fix reality |
| `unverified_up` | Live but never flagged verified | Call `mark_verified()` |
| `lane_down` / `declared_missing` | Not live, not claimed (expected topology) | Document or remove |

### Per-domain probe shape

| Domain | Live probe |
|---|---|
| **Skills** | `importlib.util.find_spec()` + `.md` parse validity + any cited Python file exists |
| **Agents** | Import the `BaseAgent` subclass and assert `agent.available` / `agent.ready()` returns True |
| **MCP servers** | `httpx.get("{endpoint}/health")` with 2s timeout; check for 200 + expected body shape |
| **Memory / vault** | Query the graph for the declared node ID; assert `exists()` returns True |

### Fleet registry precedent

`cohezion.inference.registry.FleetRegistry.audit_liveness()` (commit `4fc20e522`) implements this pattern for the 7-lane model fleet. On first run it surfaced FOUR legitimate registry bugs -- one historical flag drift plus three Lane-enum schema misclassifications. The audit method caught drift classes that a documentation review would have missed.

### Implementation requirements

1. **Injectable probe function** (`check_fleet_fn=None` default, dependency injection for tests). Without this, the audit becomes a flaky integration-only test.
2. **Four drift categories, not more**. Adding `degraded` / `partial` / `flapping` dilutes operator response. Keep buckets actionable.
3. **Surface, do NOT auto-fix**. Silently updating `verified_working` flags based on probe results hides real regressions (a typo in a declaration looks identical to a hardware failure). Operator decides.
4. **Ship an operator CLI** -- `python -m cohezion.registry.capability_registry audit` or similar -- so humans can read the drift report without writing Python.
5. **Wire into CI** as an integration test that fails when `critical_stale` is non-empty against a known-UP baseline.

### Anti-pattern: external audit scripts

Don't write a `scripts/audit_registry.py` that imports the registry and reproduces the audit logic. That script drifts from the registry schema over time -- a new field gets added, the external script misses it. Audit methods live **inside** the thing they audit. One class, one schema, one audit surface, all evolve together.

### Related patterns (vault)

- `patterns/registry-vs-live-reconciliation-audit.md` -- the generalized pattern.
- `patterns/phase-0-backend-verification-before-dispatch-wiring.md` -- catches drift at declaration time; audit catches it continuously after.
- `learnings/2026-04-21-registry-vs-live-reconciliation-and-lane-classification-bugs.md` -- session that extracted the pattern.

## VERSION
v1.1 -- 2026-04-21 added Liveness Drift Audit section from turbo-distributed-torvalds-continued session
