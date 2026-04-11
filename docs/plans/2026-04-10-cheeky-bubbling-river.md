# Dynamic Adaptive Context Policy for Cohezion

## Context

Cohezion has 5 independent context layers (`.context/` manifest, FLUX Aggregator, ContextHarness, OllamaContextManager, CompoundExecutor guidance) that each manage breadth and depth independently using hardcoded constants. There is no unified controller that adapts context strategy based on task characteristics or execution feedback. This leads to:

- **Over-fetching** for simple tasks (wasting tokens on irrelevant vault patterns)
- **Under-fetching** for complex tasks (missing critical cross-domain context)
- **No feedback loop** — context strategy doesn't learn from task outcomes

The goal: A dynamic context policy that **proactively** selects the right breadth/depth profile before execution and **reactively** adjusts mid-execution based on signals like coherence drift, token pressure, and alignment scores.

---

## Architecture: ContextPolicy (single new module)

Create `src/cohezion/compound/context_policy.py` (~200 lines) that sits between the CompoundExecutor and the FLUX/ContextManager layers.

### Key Design Decisions

1. **No new infrastructure** — The ContextPolicy wraps existing FLUX aggregator and ContextManager. It doesn't add new sources; it tunes how existing sources are queried.
2. **Wire into CompoundExecutor** — Inject via `CompoundContextMixin`, replacing the current fixed-parameter context loading.
3. **Two modes: Proactive (pre-task) + Reactive (mid-task)** — Proactive classifies the task and sets initial parameters; Reactive adjusts if coherence drops or token budget is exceeded.

---

## Implementation Plan

### Task 1: Define ContextPolicy dataclass and TaskProfile enum

**File:** `src/cohezion/compound/context_policy.py` (new)

```python
class TaskProfile(Enum):
    """Task shape determines context strategy."""
    FOCUSED = "focused"     # Single-domain, deep context (e.g., debug one module)
    EXPLORATORY = "exploratory"  # Cross-domain, broad context (e.g., design new feature)
    ROUTINE = "routine"     # Well-known pattern, minimal context (template match likely)

@dataclass(frozen=True)
class ContextBudget:
    """Dynamic context parameters for a single execution."""
    flux_top_k: int          # How many FLUX blocks to fetch (breadth)
    flux_min_relevance: float  # Relevance floor (depth filter)
    flux_sources: list[FluxSource] | None  # Which sources to query (None = all)
    token_budget: int         # Max tokens for injected context
    skill_overlay: bool       # Whether to load skill-specific context
```

The profile-to-budget mapping:

| Profile | flux_top_k | min_relevance | sources | token_budget | skill_overlay |
|---------|-----------|---------------|---------|--------------|---------------|
| FOCUSED | 5 | 0.7 | [VAULT, HISTORY] | 800 | True |
| EXPLORATORY | 10 | 0.3 | None (all) | 1500 | True |
| ROUTINE | 2 | 0.8 | [CACHE, VAULT] | 300 | False |

### Task 2: Implement proactive task classification

**File:** `src/cohezion/compound/context_policy.py`

Classify the task into a TaskProfile using signals already available in the CompoundExecutor pipeline:

```python
class ContextPolicy:
    def classify_task(self, task_description: str, operation_type: str, 
                      alignment: ExecutionAlignment | None = None) -> TaskProfile:
        """Proactive: classify task before execution starts."""
```

**Classification heuristics** (no ML model needed, reuse existing RequestAlignmentAnalyzer patterns):
- **ROUTINE**: Template match similarity > 0.8 (from `_try_template_match`), OR operation_type in ("persist", "search") with short description
- **FOCUSED**: Single intent keyword cluster (from `_INTENT_KEYWORDS`), description < 100 chars, references specific file/module names
- **EXPLORATORY**: Multiple intent keywords, description > 200 chars, cross-domain terms (physics + swarm + compound), OR alignment.drift_risk > 0.3

### Task 3: Implement hybrid reactive context adjustment

**File:** `src/cohezion/compound/context_policy.py`

Two-tier reactive system:

```python
def adjust_immediate(self, current: ContextBudget, signals: ContextSignals) -> ContextBudget:
    """Tier 1: Immediate adjustment for critical signals (current execution)."""

def record_soft_signal(self, signals: ContextSignals, profile: TaskProfile) -> None:
    """Tier 2: Log soft signals for next-execution learning (vault feedback)."""
```

**ContextSignals** (all already available in the executor pipeline):
- `coherence_state: float` — from ContextManager.coherence_state
- `token_usage: int` — from ContextManager.token_usage
- `alignment_score: float` — from RequestAlignmentAnalyzer
- `template_hit: bool` — from _try_template_match

**Tier 1 — Immediate (applied to current execution):**
1. If coherence drops below 0.5 (HIHO threshold) → broaden: increase top_k by 3, lower min_relevance by 0.1
2. If token_usage > 80% of budget → narrow: decrease top_k to 2, raise min_relevance by 0.1

**Tier 2 — Next-execution learning (logged to vault, applied on future classify_task):**
3. If alignment_score < 0.6 → record "drift-prone task" pattern, future similar tasks start with HISTORY source included
4. If template_hit = True and profile was EXPLORATORY → record "over-classified" signal, future similar tasks start as ROUTINE

### Task 4: Wire ContextPolicy into CompoundContextMixin

**File:** `src/cohezion/compound/context_integration.py` (modify)

Replace fixed token_budget=1000 and hardcoded coherence_threshold=0.5 with ContextPolicy outputs:

- In `load_core_context()`: Use `ContextBudget.token_budget` instead of manifest's fixed budget
- In `load_skill_context()`: Gate on `ContextBudget.skill_overlay`
- Add `apply_policy(task_description, operation_type)` method that calls `ContextPolicy.classify_task()` and stores the resulting budget

### Task 5: Wire ContextPolicy into AgentNode FLUX queries

**File:** `src/cohezion/graph/nodes.py` (modify)

Replace the hardcoded `_FLUX_TOP_K = 3` and `_FLUX_MIN_RELEVANCE = 0.5` with values from ContextBudget:

- Add optional `context_budget: ContextBudget | None` parameter to `AgentNode.__init__`
- In `_get_flux_context()`: Use budget's top_k, min_relevance, and sources
- Fallback to current hardcoded values if no budget provided (backward compatible)

### Task 6: Add feedback logging for context effectiveness

**File:** `src/cohezion/compound/context_policy.py` (extend)

After task execution, log which context profile was used and whether it was effective:

```python
def record_outcome(self, profile: TaskProfile, budget: ContextBudget,
                   execution_success: bool, coherence_final: float) -> None:
    """Log context strategy outcome for future refinement."""
```

This records to the existing VaultLogger, enabling the SkillSelector to learn which context strategies work best for which task types. Lightweight — just a structured dict appended to the vault log.

### Task 7: Tests

**File:** `tests/compound/test_context_policy.py` (new)

6 focused tests:
1. `test_classify_routine_task` — short persist task → ROUTINE
2. `test_classify_focused_task` — single-module debug → FOCUSED
3. `test_classify_exploratory_task` — cross-domain design → EXPLORATORY
4. `test_adjust_immediate_coherence_drop` — coherence < 0.5 → broadens budget (Tier 1)
5. `test_adjust_immediate_token_pressure` — token > 80% → narrows budget (Tier 1)
6. `test_soft_signal_drift_recorded` — alignment < 0.6 → logs to vault, doesn't change current budget (Tier 2)

---

## Files Modified

| File | Action | Lines ~Changed |
|------|--------|---------------|
| `src/cohezion/compound/context_policy.py` | **New** | ~200 |
| `src/cohezion/compound/context_integration.py` | Modify | ~30 |
| `src/cohezion/graph/nodes.py` | Modify | ~15 |
| `tests/compound/test_context_policy.py` | **New** | ~120 |

## Files Referenced (Read-only)

- `src/cohezion/compound/executor.py` — CompoundExecutor pipeline (Steps 1-4 of 11-step)
- `src/cohezion/compound/request_alignment_analyzer.py` — Alignment scoring
- `src/cohezion/flux/aggregator.py` — FluxAggregator.get_context() API
- `src/cohezion/flux/types.py` — FluxSource, FluxBlock, FluxContext
- `src/cohezion/compound/models.py` — ExecutionAlignment, IntentType

## Verification

1. `uv run pytest tests/compound/test_context_policy.py -q` — New tests pass
2. `uv run pytest tests/compound/test_context_integration.py -q` — Existing tests still pass
3. `uv run pytest tests/graph/test_context_bus.py -q` — Node tests still pass
4. `ruff format src/cohezion/compound/context_policy.py && ruff check src/cohezion/compound/context_policy.py` — Clean
5. Manual smoke: Import ContextPolicy, classify sample tasks, verify budget outputs make sense
