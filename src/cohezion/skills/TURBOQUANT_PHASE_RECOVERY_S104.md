---
id: skill-turboquant-restoration
name: TurboQuant Phase Recovery
domain: ML Inference
version: v1.0
tier: PRIME
coherence: 1.0
parent: inference-optimization
related:
  - [[KV-cache compression]]
  - [[symmetry-hardware-bridge]]
  - [[HIHO stability]]
aliases:
  - TurboQuant Revival
  - Strix Halo KV Optimization
created: 2026-04-20
session: S104
---

# Skill: TurboQuant Phase Recovery

## Context
TurboQuant implementation (commit 5bcae51a0) was accidentally reverted in later commits, breaking the inference optimization path.

## Problem
```
Git history:
  5bcae51a0 feat(turboquant): Phase 0-2 ← Working implementation
  ... later commits ...
  HEAD        ← turboquant_reference.py DELETED
```

**Missing components:**
- `src/cohezion/inference/turboquant_reference.py` (178 lines)
- `src/cohezion/core/symmetry_hardware_bridge.py` (87 lines)
- `KVQuant` class in `registry.py`
- `WeightQuant` enum in `registry.py`
- Tests: 12 assertions failing

## Recovery Pattern

### Step 1: Identify Missing Files
```bash
git show 5bcae51a0 --name-only | grep -E "turboquant|symmetry"
```

### Step 2: Restore from Historical Commit
```bash
git show 5bcae51a0:src/cohezion/inference/turboquant_reference.py \
  > src/cohezion/inference/turboquant_reference.py
git show 5bcae51a0:src/cohezion/core/symmetry_hardware_bridge.py \
  > src/cohezion/core/symmetry_hardware_bridge.py
# ... etc for all files
```

### Step 3: Verify Restoration
```python
from cohezion.inference.turboquant_reference import TurboQuantReference
from cohezion.core.symmetry_hardware_bridge import get_symmetry_bridge
from cohezion.inference.registry import KVQuant

assert hasattr(TurboQuantReference, 'compress')
assert callable(get_symmetry_bridge)
assert KVQuant.scheme == "turboquant"  # Default test
```

### Step 4: Run Tests
```bash
uv run pytest tests/inference/test_turboquant_reference.py -v
# Expected: 12/12 passed
```

## Phase 3 Extension
Added streaming KV compressor for 128k context targets.

## V-Model Validation
| Phase | Evidence |
|-------|----------|
| Requirements | ROADMAP: 128k ≤55 GB |
| Architecture | Hadamard rotation + PolarQuant |
| Implementation | torch ground-truth oracle |
| Unit Test | 12/12 assertions |
| Integration | Symmetry bridge injection |

## Key Insight
**Never assume git history is linear.** Features can be silently reverted by later commits. Always verify with actual import tests.

## Backlinks
- [[learning-359-stealth-bare-except]]
- [[Strix Halo Symphony]]
- [[Session 104]]
- [[TurboQuant ICLR 2026]]

---
canonical: true
coherence_verified: 2026-04-20
success_rate: 1.0
