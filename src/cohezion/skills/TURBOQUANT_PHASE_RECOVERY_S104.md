---
id: skill-turboquant-restoration
name: TurboQuant Phase Recovery
domain: ML Inference
version: v1.1
tier: PRIME
coherence: 1.0
parent: inference-optimization
related:
  - [[KV-cache compression]]
  - [[symmetry-hardware-bridge]]
  - [[HIHO stability]]
  - [[phase-0-backend-verification-before-dispatch-wiring]]
aliases:
  - TurboQuant Revival
  - Strix Halo KV Optimization
created: 2026-04-20
session: S104
revisions:
  - date: 2026-04-21
    session: turbo-distributed-torvalds
    change: "Added Phase 4 (backend-support verification gate) after discovering that Phases 0-2 completeness does NOT imply a working end-to-end KV compression. The installed llama-server binary on Strix Halo has no TurboQuant kernel and upstream PR #20969 is a GitHub Discussion, not a merged PR -- making any dispatcher hop a silent no-op. Refined Key Insight to reflect the module-vs-backend distinction."
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

## Phase 4 -- Backend-Support Verification Gate (added 2026-04-21)

**Restoration of the Python module is necessary but NOT sufficient.** Phases 0-3 restore `turboquant_reference.py`, `symmetry_hardware_bridge.py`, the `KVQuant` dataclass, and the streaming compressor -- but the dispatcher still has to forward `runtime_flag` values to a backend binary that implements the TurboQuant kernel. Gate Phase 4 BEFORE any `fleet.py` dispatcher hop is written.

### The silent-no-op trap

`src/cohezion/inference/fleet.py::_dispatch_openai_compatible` sends the payload to Lemonade's OpenAI-compatible endpoint. Lemonade's wrapper **silently drops unknown JSON fields** without validation. llama-server's KV-cache dtype is a server-startup flag (`--cache-type-k/-v`), not a per-request field. Both layers will accept `{"kv_cache_dtype": "turbo3"}` without error; neither will honor it. Tests that assert "request contained the flag" will pass. Memory footprint will be unchanged. **This is a silent no-op that looks healthy in every review artifact except a real memory benchmark.**

### Phase 4 checklist (read-only, ~15 min; do this BEFORE writing dispatcher code)

```bash
# 4a. Identify the actual running backend for each declared lane
ss -tlnp | grep -E ':(13306|13307|13308|13309)'
ps auxf | grep -iE 'llama|lemon|vllm'

# 4b. Check --help on the backend binary for the declared flag
BINARY=/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server
LD_LIBRARY_PATH=$(dirname $BINARY) $BINARY --help 2>&1 | grep -iE 'turbo|tbq|kv-cache-dtype'

# 4c. Scan the binary for compiled-in flag strings
strings $BINARY | grep -iE '^(turbo|tbq)'

# 4d. Live probe -- look for silent-accept-and-drop
curl -s -X POST http://localhost:13307/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Gemma-4-E4B-it-GGUF","messages":[{"role":"user","content":"hi"}],
       "max_tokens":8,"extra_body":{"kv_cache_dtype":"turbo3"}}'

# 4e. Verify any "upstream PR #NNNNN" registry comments are actually MERGED
gh pr view 20969 --repo ggml-org/llama.cpp 2>&1 | head -3
```

### Gate pass criterion

Must have BOTH: (1) `--help` or `strings` finds the flag in the binary AND (2) a live probe produces observable behavior change (non-bf16 fingerprint, different memory footprint, or a log line confirming the flag was applied).

### If Phase 4 fails

Three honest options -- surface to the user rather than pick autonomously:

1. **Rebuild llama.cpp from a community TurboQuant fork** for ROCm gfx1151. Hours-to-days. Local divergence from upstream.
2. **Pivot to a backend-supported scheme** (e.g. `kv8` / `q8_0`). Change `KVQuant.scheme` + `runtime_flag`, keep the turboquant module in tree for when upstream lands. ~1 hour of registry work + one `lemonade run --save-options` per affected model.
3. **Close out as blocked** -- set `kv_quant=KVQuant()` (default no-op) on the affected models; note the blockage in a registry comment pointing at the plan file. No runtime change.

See `learnings/2026-04-21-turboquant-phase0-and-crash-loop-triage.md` for the session that walked this path end-to-end and chose option 2.

### Regression guard

Add a test that asserts every `kv_quant.runtime_flag["llama.cpp"]` value on every model is in llama-server's whitelist:

```python
LLAMACPP_CACHE_TYPE_WHITELIST = {"f32", "f16", "bf16", "q8_0", "q4_0",
                                  "q4_1", "q5_0", "q5_1", "iq4_nl"}

def test_kv_quant_llamacpp_runtime_flags_are_in_whitelist() -> None:
    registry = FleetRegistry()
    for model in registry.models.values():
        flag = model.kv_quant.runtime_flag.get("llama.cpp")
        if flag is None:
            continue
        assert flag in LLAMACPP_CACHE_TYPE_WHITELIST
```

Lives in `tests/inference/test_registry.py`. A value outside the whitelist -- like `turbo3` -- fails fast at test time instead of silently no-opping at server startup.

## V-Model Validation
| Phase | Evidence |
|-------|----------|
| Requirements | ROADMAP: 128k ≤55 GB |
| Architecture | Hadamard rotation + PolarQuant |
| Implementation | torch ground-truth oracle |
| Unit Test | 12/12 assertions |
| Integration | Symmetry bridge injection |
| **Backend Support (Phase 4)** | **gate must pass: `--help` finds flag + live probe changes behavior** |

## Key Insight
**Never assume git history is linear. And never assume module restoration implies backend support.**

Features can be silently reverted by later commits (Phases 0-3 insight, v1.0). AND registry declarations of runtime flags can silently outlive the backend's ability to honor them (Phase 4 insight, v1.1) -- the "flag received but not honored" failure mode is invisible to unit tests and diff reviews; only a backend-support probe catches it before production.

The two mistakes compound: a module can be Phases 0-2 complete, pass 12/12 unit tests, AND have a registry declaration that the backend silently ignores. All three artifacts look healthy at once.

## Backlinks
- [[learning-359-stealth-bare-except]]
- [[Strix Halo Symphony]]
- [[Session 104]]
- [[TurboQuant ICLR 2026]]
- [[learnings/2026-04-21-turboquant-phase0-and-crash-loop-triage]]
- [[patterns/phase-0-backend-verification-before-dispatch-wiring]]
- [[decisions/2026-04-21-turboquant-to-kv8-pivot-on-strix-halo]]

---
canonical: true
coherence_verified: 2026-04-21
success_rate: 1.0
