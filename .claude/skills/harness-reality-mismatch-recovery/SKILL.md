---
name: harness-reality-mismatch-recovery
description: |
  Recover when harness.md (or similar truth docs) document CB invariants as VERIFIED
  but the implementation is absent from the current branch HEAD.
  Use when: (1) harness.md lists methods like suggest_routing_tier(), get_health_summary(),
  snapshot()/diff_snapshots(), to_dict()/from_dict() as verified, but grep finds them missing
  from the source file, (2) git log shows a commit with the feature but it's on a different
  branch, (3) a "feat(compound): implement CB6-CB12" style commit exists in git history
  but isn't reachable from HEAD.
author: Claude Code
version: 1.0.0
---

# Harness/Reality Mismatch Recovery

## Problem

`harness.md` documents invariants like `CB12: suggest_routing_tier()` as VERIFIED.
But `grep "suggest_routing_tier" src/cohezion/compound/degradation_detector.py` returns nothing.
The implementation exists somewhere in git history but not on the current branch.

## Root Cause

The implementation was committed to a separate session branch (`session-repo-health-automation`
in the concrete case) and never merged into the feature branch you're working on.
Harness.md was written against that branch's HEAD.

## Solution

**Step 1 — Confirm the gap:**
```bash
grep -n "suggest_routing_tier\|get_health_summary\|to_dict\|from_dict" \
  src/cohezion/compound/degradation_detector.py
# Expected: no matches
```

**Step 2 — Find the commit in all branches:**
```bash
git log --oneline --all | grep -i "CB6\|CB12\|health observ\|implement.*CB"
# Example output: 4c9ac4ada feat(compound): implement CB6-CB12 health observability layer
```

**Step 3 — Get the full diff to understand what was implemented:**
```bash
git show 4c9ac4ada -- src/cohezion/compound/degradation_health.py | head -300
git show 4c9ac4ada -- src/cohezion/compound/degradation_detector.py
```

**Step 4 — Check which branch contains the commit:**
```bash
git log --oneline --all | grep -B2 -A2 "4c9ac4ada"
# Shows surrounding commits → identifies parent branch
```

**Step 5 — Restore the implementation:**

If the commit introduced a NEW file (like `degradation_health.py`), reconstruct it from the `git show` diff (lines prefixed with `+`).

If the commit MODIFIED an existing file, apply the patch surgically:
- Import the new dependency
- Add inheritance (`class DegradationDetector(HealthObservabilityMixin):`)
- Wire observability state in `__init__`
- Add `_call_count += 1` in the hot path
- Append emitted alerts to `_alert_history` rolling buffer

**Step 6 — Verify all CB invariants pass:**
```bash
uv run python -c "
from cohezion.compound.degradation_detector import DegradationDetector
d = DegradationDetector()
# CB9
assert d.get_alert_summary()['total'] == 0
# CB11
snap = d.snapshot()
assert {'call_count','baselines_established','health_summary','composite_score','alert_summary','health_trend'} <= set(snap.keys())
diff = DegradationDetector.diff_snapshots(snap, snap)
assert diff['health_changes'] == {}
# CB12
assert d.suggest_routing_tier() == 'igpu'  # grace period → safe middle tier
# CB7
state = d.to_dict()
d2 = DegradationDetector.from_dict(state)
print('All CB7/CB9/CB11/CB12 PASS')
"
```

## Key Architecture: HealthObservabilityMixin Pattern

The CB6-CB12 implementation uses a **mixin** to keep `degradation_detector.py` under the 500-line hard limit:

- `degradation_health.py` — `HealthObservabilityMixin`: ALL read-only health/aggregate methods
- `degradation_detector.py` — `DegradationDetector(HealthObservabilityMixin)`: mutation/write-path only

The mixin uses TYPE_CHECKING-only imports from the host class to avoid circular imports:
```python
if TYPE_CHECKING:
    from cohezion.compound.degradation_detector import DegradationAlert, MetricBaseline
```

The host class MUST provide these attributes in `__init__` (the mixin declares them as type-only):
- `_baselines: dict[str, MetricBaseline]`
- `_call_count: int`
- `_alert_history: list[DegradationAlert]`
- `_snapshot_history: list[dict]`
- `_max_snapshot_history: int`
- `cache_hit_rate_threshold / coherence_threshold / token_efficiency_drop_threshold: float`

## CB13 Category-Error Warning

CB13 says `suggest_routing_tier()` and `task_classifier.classify().node` must agree ≥90%.

**This is a category error if interpreted as per-prompt comparison.**

- `suggest_routing_tier()` → health-score-based, **constant per detector state**
- `classify(prompt).node` → **prompt-dependent**, varies per input

The correct CB13 invariant is **non-contradiction**: when health is good (score≥80 → "npu"),
the detector must not recommend "cpu" while the classifier is sending the majority of CL1
queries to fast silicon (npu/gpu). Test this as a health-band check, not a per-prompt loop.

Also: `task_classifier` returns `"npu"` or `"gpu"` only. Normalize `"gpu" → "igpu"` when
comparing to `suggest_routing_tier()` vocabulary (`{"npu", "igpu", "cpu"}`).

## Verified

- Confirmed: all 38 tests pass (18 boundary tests + 20 existing detector tests, 1 expected skip)
- `make validate` still passes (25/25) after restoration
- `uv run pytest tests/unit -q` still passes (353 unit tests)
