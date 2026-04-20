---
name: adaptive-context-policy-pattern
description: |
  Architecture pattern for dynamic FLUX context breadth/depth control in
  compound AI systems. Use when: (1) building a ContextPolicy for a compound
  executor, (2) FLUX queries use hardcoded top_k/min_relevance constants,
  (3) different task types need different context strategies (simple tasks
  over-fetching, complex tasks under-fetching), (4) context parameters need
  to persist and improve across sessions and tools.
  Provides: ROUTINE/FOCUSED/EXPLORATORY classification, hybrid reactive
  adjustment, cross-platform YAML frontmatter persistence, MCP tool access.
author: Claude Code
version: 1.0.0
---

# Adaptive Context Policy Pattern

## Problem

Compound executors use hardcoded FLUX parameters (`top_k=3`, `min_relevance=0.5`)
for all tasks. Simple tasks over-fetch irrelevant context; complex cross-domain
tasks under-fetch. Parameters never improve across sessions. Different tools
(Claude Code, Gemini CLI, Zed) all start from the same defaults.

## Solution: ContextPolicy

Three-layer controller in `compound/context_policy.py`:

### Layer 1: Proactive Classification

```python
class TaskProfile(Enum):
    ROUTINE     = "routine"      # template hits, short persist/search
    FOCUSED     = "focused"      # single-domain, moderate complexity (default)
    EXPLORATORY = "exploratory"  # cross-domain, high drift risk

policy = ContextPolicy()
profile = policy.classify_task(task_description, operation_type,
                                template_similarity=0.9, drift_risk=0.1)
budget = policy.get_budget(profile)
```

**Classification waterfall** (in priority order):
1. `template_similarity > 0.8` → ROUTINE (strongest signal)
2. `drift_risk > 0.3` → EXPLORATORY (overrides simple-task heuristics)
3. Short persist/search (`<100 chars`) → ROUTINE
4. `>=2 cross-domain terms` (physics+swarm+compound...) → EXPLORATORY
5. `>=2 intent clusters` + `>200 chars` → EXPLORATORY
6. Default → FOCUSED

### Layer 2: Profile Budgets

| Profile | top_k | min_rel | sources | tokens | skill_overlay |
|---------|-------|---------|---------|--------|---------------|
| FOCUSED | 5 | 0.70 | VAULT+HISTORY | 800 | True |
| EXPLORATORY | 10 | 0.30 | all | 1500 | True |
| ROUTINE | 2 | 0.80 | CACHE+VAULT | 300 | False |

```python
@dataclass(frozen=True)  # CRITICAL: frozen prevents mid-pipeline mutation
class ContextBudget:
    flux_top_k: int
    flux_min_relevance: float
    flux_sources: tuple[FluxSource, ...] | None  # None = all
    token_budget: int
    skill_overlay: bool
```

### Layer 3: Hybrid Reactive Adjustment

**Tier 1 (immediate, current execution):**
```python
signals = ContextSignals(coherence_state=0.3, token_usage=700)
adjusted = policy.adjust_immediate(current_budget, signals)
# coherence < 0.5 → top_k += 3, min_rel -= 0.1  (broaden)
# tokens > 80%    → top_k = 2, min_rel += 0.1   (narrow)
```

**Tier 2 (vault learning, next execution):**
```python
policy.record_soft_signal(signals, profile, task_description)
# alignment < 0.6 → logs "drift_prone" → future tasks include HISTORY source
# template_hit on EXPLORATORY → logs "over_classified" → future downgrades to ROUTINE
```

## Cross-Platform Persistence

`.context/policy/learned-budgets.md` — YAML frontmatter markdown (not JSON):

```markdown
---
version: "1.0.0"
profiles:
  focused:
    flux_top_k: 5
    flux_min_relevance: 0.7
    ...
outcome_summary:
  total_executions: 42
  by_profile:
    focused: {successes: 38, avg_coherence: 0.76}
---

# Learned Context Budgets
[narrative documentation]
```

**Why YAML frontmatter markdown, not JSON:**
- Obsidian/vault-keeper can index it
- Markdown body carries narrative context (why budgets were tuned)
- Any tool (Pi, humans) can read it without code
- Consistent with skills/*.md, .context/ patterns

**Access from any tool:**
```python
# Python (any session, any tool)
policy = ContextPolicy()  # warm-starts from .context/policy/learned-budgets.md

# MCP (Zed, Gemini, Antigravity)
# get_context_policy / update_context_policy on compound-mcp server
```

## Executor Integration Points

```python
# In CompoundExecutor.execute_task():

# Step 0.5: Classify + apply policy
budget = self.apply_policy(task_description, operation_type)

# Step 1.7: Reactive Tier 1 (after alignment check)
signals = ContextSignals(
    coherence_state=self._context_manager.coherence_state,
    token_usage=self._context_manager.token_usage,
)
budget = self._context_policy.adjust_immediate(budget, signals)

# Step 10.9: Record outcome for cross-session learning
self._context_policy.record_outcome(profile, budget, success, coherence)
```

## Critical Implementation Notes

### Singleton Pollution Prevention (L294)
```python
# WRONG: mutates module-level dict → pollutes other instances in same process
_PROFILE_BUDGETS[profile] = new_budget

# CORRECT: instance-level copy
def __init__(self):
    self._budgets = dict(_PROFILE_BUDGETS)  # copy, not reference
```

### AgentNode Integration (backward compatible)
```python
class AgentNode(WorkflowNode):
    def __init__(self, spec, flux_aggregator=None, context_budget=None):
        self._budget = context_budget  # None = use class defaults

    async def _get_flux_context(self, inputs):
        top_k = self._budget.flux_top_k if self._budget else self._FLUX_TOP_K
        sources = list(self._budget.flux_sources) if self._budget?.flux_sources else None
```

## Observed Performance (Session 96)

Real compound loop run (`compound_cycle.py`):
- Both tasks classified as FOCUSED (correct for single-domain test tasks)
- Tier 1 narrowing fired due to core context tokens (800) at 80% threshold
- `learned-budgets.md` updated: 2 executions, 0.76 avg coherence, 100% success

## Files

- `src/cohezion/compound/context_policy.py` — Core implementation
- `src/cohezion/compound/context_integration.py` — CompoundContextMixin integration
- `src/cohezion/graph/nodes.py` — AgentNode integration
- `src/cohezion/mcp/compound_server.py` — MCP tools
- `.context/policy/learned-budgets.md` — Persistent state
- `tests/compound/test_context_policy.py` — 22 tests

## References

- Session 96, L292 (architecture), L293 (YAML choice), L294 (singleton fix)
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` L292-L294
