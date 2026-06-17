---
name: local-inference-reflection-loop
description: |
  Pattern for wiring health-driven routing feedback into a tiered local executor.
  Use when: (1) DegradationDetector.suggest_routing_tier() exists but isn't consulted
  by the executor (routing stays static despite degradation signals), (2) NPU returns
  HTTP 500 transiently and the executor should proactively avoid it next cycle,
  (3) coordinator holds a detector but doesn't pass it to the executor constructor.
  Key insight: the reflection override is DOWNGRADE-ONLY — health-driven routing can
  worsen the tier (NPU→iGPU when NPU is stale), but never improve it (task complexity
  from classifier wins for upward routing).
author: Claude Code
version: 1.0.0
---

# Local Inference Reflection Loop

## Problem

`DegradationDetector.check_degradation()` is called after every task result, updating
health baselines. But `suggest_routing_tier()` is never consulted by the executor —
routing remains purely classifier-driven. When NPU goes stale (HTTP 500), the only
response is reactive fallback (after the 500), not proactive avoidance.

## Architecture

```
LoopCoordinator
  ├── _degradation_detector (DegradationDetector)
  └── run() → LocalImprovementExecutor(base_url, degradation_detector=self._detector)
                └── execute_task()
                      ├── classify_node(description)   # task complexity
                      ├── detector.suggest_routing_tier() # hardware health
                      └── if health_rank < classifier_rank: node = health_tier (downgrade)
```

## Implementation

### Step 1: Tier rank dict (ordinal comparison)

```python
_TIER_RANK: dict[str, int] = {"cpu": 0, "igpu": 1, "npu": 2}
```

### Step 2: Add detector param to executor

```python
class LocalImprovementExecutor:
    def __init__(
        self,
        base_url: str = LEMONADE_BASE_URL,
        degradation_detector: Any = None,   # ← add
    ) -> None:
        self._degradation_detector = degradation_detector
```

### Step 3: Downgrade-only override in execute_task

```python
node = _classify_node(description)

if self._degradation_detector is not None:
    try:
        suggested = self._degradation_detector.suggest_routing_tier()
        if _TIER_RANK.get(suggested, 1) < _TIER_RANK.get(node, 1):
            logger.info("task %s: degradation reflection %s→%s", task_id, node, suggested)
            node = suggested
    except Exception:
        pass  # reflection is non-blocking
```

### Step 4: Coordinator passes detector to executor

```python
# In LoopCoordinator.run():
local_exec = LocalImprovementExecutor(
    self.config.local_base_url,
    degradation_detector=self._degradation_detector,  # ← pass through
)
```

## suggest_routing_tier() semantics

Per CB12 harness invariant (`DegradationDetector`):
- Grace period (no baselines yet) → `"igpu"` (safe middle tier)
- composite_score ≥ 80 → `"npu"` (all metrics healthy)
- 50 ≤ score < 80 → `"igpu"`
- score < 50 → `"cpu"` (significant degradation)

Composite score = `100 * (healthy_established / total_established)` where "healthy"
means not in the recent-20-alert set.

## Discriminating Test

```python
# Verifies the detector actually reaches the executor constructor, not just that
# the coordinator runs (a wrong impl drops the kwarg silently):
captured = {}
def capture(base_url, degradation_detector=None):
    captured["degradation_detector"] = degradation_detector
    return _mock_local_exec()

detector = DegradationDetector()
coordinator = LoopCoordinator(config, degradation_detector=detector)
with patch("cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
           side_effect=capture):
    coordinator.run()

assert captured["degradation_detector"] is detector
```

Note: patch at SOURCE module (`local_executor`), not calling module (`coordinator`) —
see `module-level-import-for-mocking` skill for why.

## Files Changed (2026-06-17)

- `src/cohezion/compound/autonomous_loop/local_executor.py` — `_TIER_RANK`, `degradation_detector` param, downgrade override in `execute_task()`
- `src/cohezion/compound/autonomous_loop/coordinator.py` — passes `degradation_detector=self._degradation_detector` to executor constructor
- `src/cohezion/compound/degradation_detector.py` — added `get_composite_health_score()`, `suggest_routing_tier()`, `get_health_summary()` (CB6/CB12)
- `tests/compound/test_loop_coordinator.py` — `TestReflectionLoopWiring` class with 2 discriminating tests
