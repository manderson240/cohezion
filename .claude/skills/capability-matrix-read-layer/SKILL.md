---
name: capability-matrix-read-layer
description: Architectural pattern for building a unified query interface over multiple
  siloed tracking systems. Use when you have 3+ independent monitoring/tracking systems
  that don't communicate, need cross-system capability assessment, want data-driven
  gap analysis across models/skills/agents, or when user mentions "capability matrix",
  "read layer", "unified assessment", "gap analysis", or "cross-system query".
metadata:
  author: Cohezion
  version: "1.0"
  source: src/cohezion/compound/capability_matrix.py
compatibility: Python 3.12+. Adapts to any system with multiple tracking backends.
---

# Capability Matrix Read Layer

A read-only aggregation layer that unifies multiple siloed tracking systems into a
single query interface without replacing or modifying the underlying systems.

## The Problem

When a system grows organically, tracking gets fragmented across independent subsystems.
In Cohezion's case, five separate systems existed:

| System | Tracked | Access Pattern |
|--------|---------|----------------|
| ModelQualityClassifier | Model coherence, success history | Per-model predictor objects |
| SkillHealthTracker | Invocation counts, success rates, health scores | Per-skill record dicts |
| CapabilityRegistry | Agent/skill discovery via TF-IDF search | Text-based lookup |
| SmartRouter | Static model profiles (FAST, CODING, LARGE_CONTEXT) | Enum-keyed dict |
| CostAwareRouter | Model quality/cost/TPS/latency | Separate float dicts |

None of these systems could answer cross-cutting questions like "which model is best
for coding tasks?" or "where are our capability gaps?" because each only sees its own
slice.

## The Solution: Read Layer (Not Replacement)

Build a matrix that READS from all systems at init time, normalizes into a common
schema, and provides unified query methods. The key insight: **don't replace existing
systems** -- they work fine for their original purpose. Add a read-only view on top.

## Instructions

### Step 1: Define a Common Entry Schema

Create a dataclass that captures the union of relevant fields across all sources.
Use affinity scores (0.0-1.0) per task type instead of binary capability flags.

```python
@dataclass
class CapabilityEntry:
    entity_type: str        # "model" | "skill" | "agent"
    entity_id: str
    capabilities: list[str]
    quality_score: float    # 0.0-1.0
    speed_tier: int         # 1=fastest, 5=slowest
    success_rate: float     # 0.0-1.0
    affinity: dict[str, float]  # task_type -> score (0.0-1.0)
    source: str             # "static" | "benchmark" | "execution-history"
    metadata: dict          # system-specific extras
```

Three score sources reflect data quality:
- **static** -- hardcoded defaults from config dicts
- **benchmark** -- one-time profiling results
- **execution-history** -- continuously updated from real usage (highest trust)

### Step 2: Load From Each System at Init

Each source system gets its own `_load_*` method. Wrap each in `try/except ImportError`
so the matrix degrades gracefully if a subsystem isn't available.

```python
class CapabilityMatrix:
    def __init__(self) -> None:
        self._entries: dict[str, CapabilityEntry] = {}
        self._load_static_models()    # SmartRouter + CostAwareRouter
        self._load_static_skills()    # SkillHealthTracker
        self._load_static_agents()    # filesystem scan of agent definitions

    def _load_static_models(self) -> None:
        try:
            from your_project.routing import SmartRouter, CostRouter
            # Merge data from both into CapabilityEntry
            for model_id, profile in SmartRouter.MODELS.items():
                quality = CostRouter.QUALITY.get(model_id, profile.tier / 5.0)
                affinity = self._compute_affinity(profile.capabilities)
                self._entries[f"model:{model_id}"] = CapabilityEntry(
                    entity_type="model",
                    entity_id=model_id,
                    quality_score=quality,
                    affinity=affinity,
                    source="static",
                    # ...
                )
        except ImportError:
            logger.debug("SmartRouter not available")
```

The `f"model:{model_id}"` key pattern prevents ID collisions across entity types.

### Step 3: Build the Unified Query Methods

Provide typed accessors per entity type, plus cross-entity operations:

```python
def assess_model(self, model_id: str) -> CapabilityEntry | None:
    return self._entries.get(f"model:{model_id}")

def assess_skill(self, skill_name: str) -> CapabilityEntry | None:
    return self._entries.get(f"skill:{skill_name}")

def recommend_for_task(
    self, task_type: str, constraints: dict | None = None,
) -> list[CapabilityEntry]:
    """Rank all entities by affinity + quality for a task type."""
    constraints = constraints or {}
    max_latency = constraints.get("max_latency_ms", float("inf"))
    min_quality = constraints.get("min_quality", 0.0)

    candidates = []
    for entry in self._entries.values():
        if entry.quality_score < min_quality:
            continue
        if entry.metadata.get("latency_ms", 0) > max_latency:
            continue
        score = entry.affinity.get(task_type, 0.0) + entry.quality_score
        candidates.append((score, entry))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in candidates]
```

### Step 4: Add Gap Analysis

Iterate over all task types, find the best available score for each, and flag
anything below the gap threshold (0.7 works well in practice).

```python
TASK_TYPES = ["coding", "reasoning", "analysis", "creative", "tool-calling"]

def run_gap_analysis(self) -> list[CapabilityGap]:
    gaps = []
    threshold = 0.7
    for task_type in self.TASK_TYPES:
        best = max(
            (e.affinity.get(task_type, 0.0)
             for e in self._entries.values()
             if e.entity_type == "model"),
            default=0.0,
        )
        if best < threshold:
            gaps.append(CapabilityGap(
                task_type=task_type,
                best_available_score=best,
                threshold=threshold,
                suggested_action="scout" if best < 0.3 else "finetune",
            ))
    return gaps
```

The "scout" vs "finetune" decision: if the best score is very low (<0.3), no existing
model is close enough to fine-tune -- you need to find a new one entirely.

### Step 5: Add Runtime Updates (EMA)

Use exponential moving average to blend new execution results with historical scores.
This prevents a single bad run from tanking a model's score.

```python
def update_from_execution(self, entity_id: str, result: dict) -> None:
    for entry in self._entries.values():
        if entry.entity_id == entity_id:
            coherence = result.get("coherence", entry.quality_score)
            # EMA: 80% old + 20% new
            entry.quality_score = 0.8 * entry.quality_score + 0.2 * coherence
            entry.source = "execution-history"
            break
```

### Step 6: Add Fine-Tune Decision Tree

Cross-reference gaps with training data availability to suggest concrete actions:

| Training Samples | Fine-Tune Mode | Approach |
|-----------------|---------------|----------|
| < 50 | soft | System prompt injection via Modelfile |
| 50-500 | qlora | QLoRA adapter training |
| > 500 | call | Full CALL cycle (autonomous training loop) |

### Step 7: Export for Humans

Generate a markdown report so non-engineers can review capability status:

```python
def export_report(self) -> str:
    """Markdown table: entity | quality | speed | success | capabilities | source"""
    # Include: entity tables, gap analysis, fine-tune suggestions
```

## Key Design Decisions

1. **Read-only at init, not continuous sync.** The matrix snapshots state at
   construction time. This avoids import cycles and race conditions. Call
   `enrich_from_execution_history()` explicitly when you want fresh runtime data.

2. **Affinity scores over binary capabilities.** A model rated 0.6 for coding is
   more informative than "supports coding: yes/no". Enables ranking and gap thresholds.

3. **Graceful degradation per source.** Each `_load_*` method catches its own
   ImportError. If SkillHealthTracker isn't installed, the matrix still works for
   models and agents.

4. **Namespaced keys (`model:`, `skill:`, `agent:`).** Prevents ID collisions when
   different systems use the same names for different entity types.

5. **Three score tiers (static/benchmark/execution-history).** Lets consumers
   decide how much to trust a score. Static defaults are better than nothing;
   execution history is ground truth.

## When to Use This Pattern

- 3+ independent tracking/monitoring systems that don't share data
- Need to answer cross-system questions ("best X for task Y")
- Want gap analysis without modifying existing subsystems
- Building capability assessment for any multi-component AI system
- Need human-readable reports that span multiple backends

## When NOT to Use This Pattern

- Only 1-2 data sources (just query them directly)
- Sources change schema frequently (maintenance overhead exceeds value)
- Need real-time streaming updates (this is snapshot-based)
- Sources are already unified (don't add a layer for nothing)

## Common Issues

### Import Cycles
The matrix imports from source systems. If source systems also import from the
matrix, you get circular imports. **Fix:** Matrix reads at init only, never
exposes itself to source systems. The dependency arrow is one-way.

### Stale Data
Matrix snapshots at init. Long-lived instances may have outdated scores.
**Fix:** Call `enrich_from_execution_history()` before operations that need
fresh data, or reconstruct the matrix periodically.

### Over-Engineering the Affinity Map
Tempting to add 20 task types. Start with 5-8 that matter. You can always add more.

## Reference Implementation

- `src/cohezion/compound/capability_matrix.py` -- core read layer (411 lines)
- `src/cohezion/compound/workflow_manager.py` -- orchestration layer on top
  (onboarding, gap analysis, fine-tuning workflows)
