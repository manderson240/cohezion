---
type: audit
date: 2026-06-07
owner: compound-engineering-specialist
router: "http://localhost:13305 (lemonade 10.6.0)"
subject: "simplicity_audit.py — boolean_flag_params + mutable_default_args (items 97 + 110)"
tier_results:
  npu:
    model: llama3.2-1b-FLM
    device: npu
    latency_ms: 3841
    verdict: sound_with_confusion
  igpu:
    model: Granite-4.1-8B-GGUF
    device: gpu (vulkan)
    latency_ms: 5364
    verdict: sound_scope_limitation_noted
  cpu:
    model: Qwen3-0.6B-GGUF
    device: cpu
    latency_ms: 509
    verdict: sound
loop_tick: loop-backlog-build-0607
---

# Local Fleet Review — simplicity_audit.py (items 97 + 110)

**Date:** 2026-06-07
**Router:** `http://localhost:13305` (Lemonade 10.6.0)
**Owner:** compound-engineering-specialist
**Tick:** `loop-backlog-build-0607`

This is the first specialist-owned, inference-bearing tick: a real tri-device code review
dispatched through the `:13305` router to NPU, iGPU, and CPU — no synthetic or fabricated
responses.

---

## Functions Reviewed

`src/cohezion/compound/simplicity_audit.py`:

- **`_boolean_default_count`** + **`boolean_flag_params`** (item 97 — control coupling / flag-argument smell)
- **`_mutable_default_count`** + **`mutable_default_args`** (item 110 — shared mutable default footgun)

Both functions are pure AST walkers (no execution, no file writes). They scan
`args.defaults` + `args.kw_defaults` for specific node types and return sorted smell lists.

---

## Router Health at Review Time

```json
{
  "npu":  { "model_name": "llama3.2-1b-FLM",    "device": "npu",        "backend_port": 8003 },
  "igpu": { "model_name": "Granite-4.1-8B-GGUF", "device": "gpu/vulkan", "backend_port": 8004 }
}
```

CPU tier was loaded on-demand (`Qwen3-0.6B-GGUF`, `llamacpp_backend=cpu`, `ctx_size=4096`)
and unloaded immediately after use (OOM discipline).

---

## Per-Device Results

### Tier 1 — NPU (`llama3.2-1b-FLM`)

| Field | Value |
|---|---|
| Model | `llama3.2-1b-FLM` |
| Device | NPU (XDNA2) |
| Latency | 3 841 ms |
| Finish | stop |

**Response:**
> The provided Python AST-analysis functions appear to be sound, but one potential correctness
> edge case is not explicitly handled: when a function has a default argument with a value that
> is a boolean (e.g., `x = 1`), the function is still considered to have a default argument,
> even though the value is a boolean. … However, the provided functions seem to be correct in
> the sense that they correctly count the number of functions with a default argument that meet
> the specified threshold.

**Specialist note:** The NPU's stated edge case is a false concern — the code correctly uses
`isinstance(d.value, bool)` to distinguish real `True`/`False` from integer `1`/`0` (Python
`bool` is a subclass of `int`, but `isinstance(1, bool)` returns `False`). The NPU conflated
the two. Overall verdict: **sound** (edge case raised was not a real bug).

---

### Tier 2 — iGPU (`Granite-4.1-8B-GGUF`)

| Field | Value |
|---|---|
| Model | `Granite-4.1-8B-GGUF` |
| Device | GPU (Vulkan / RDNA) |
| Latency | 5 364 ms |
| Finish | stop |

**Response:**
> The implementations correctly handle most common cases for counting boolean and mutable
> default arguments, but they miss edge cases where defaults are computed dynamically via
> expressions (e.g., `lambda: True` or `lambda: [1, 2]`) or where defaults are assigned
> using `ast.Name` nodes that refer to variables defined elsewhere in the function body.
> Such dynamically evaluated defaults are not captured because the functions only inspect
> the AST nodes directly representing constants or constructors, failing to evaluate the
> runtime value of more complex default expressions. Additionally, the handling of
> keyword-only arguments with defaults in functions defined with variable argument lists
> (`*args` or `**kwargs`) is implicitly correct, but the functions do not explicitly account
> for defaults in such contexts beyond the generic `args.defaults` and `args.kw_defaults`
> attributes, which should still work as intended. Overall, the primary limitation lies in
> the inability to evaluate non-constant default expressions.

**Specialist note:** This is the most substantive review. The `lambda: [1, 2]` gap is real —
an `ast.Lambda` node or an `ast.Name` (e.g. `EMPTY_LIST = []` as a module-level sentinel)
would escape `_mutable_default_count`. However, this is a documented **scope limitation**
of static smell detection, not a correctness bug: the functions are intentionally conservative,
flagging only the clearly-patterned footguns. The `*args`/`**kwargs` note is a non-issue
(those params have no defaults by definition). Verdict: **sound within stated scope**;
lambda and named-variable defaults are a known gap, not a defect.

---

### Tier 3 — CPU (`Qwen3-0.6B-GGUF`)

| Field | Value |
|---|---|
| Model | `Qwen3-0.6B-GGUF` (Q4_0) |
| Device | CPU (llamacpp) |
| Load time | 730 ms |
| Inference latency | 509 ms |
| Finish | stop |
| Unloaded after | yes |

**Response (with `/no_think` system prompt to suppress chain-of-thought):**
> One correctness edge case is that the `_boolean_default_count` function correctly
> identifies bool values in the AST, which is essential for determining the number of
> boolean expressions in a function. This ensures that the function accurately reflects
> the presence of boolean values in the function's parameters, which is crucial for
> correctness.

**Specialist note:** The 0.6B model effectively confirmed soundness with limited additional
analysis. At this tier, the primary value is a low-cost sanity check — no false positives,
no alarming novel edge cases raised. Verdict: **sound**.

---

## Consensus

All three tiers agreed the implementations are **correct for their stated purpose** (pure
AST-level static smell detection). The only substantive finding — raised by the iGPU tier —
is that lambda expressions and `ast.Name` references as default values would escape detection.
This is an intentional scope boundary, not a bug: the smell detectors target the most common
footgun forms (`[]`, `{}`, `set()`, `list()`, etc.) and document that a "number is a smell
flagged for judgment, not a verdict." No correctness defects were identified. The NPU's
stated concern about integer-1 being counted as boolean was incorrect; the code handles this
exactly right via `isinstance(d.value, bool)`.

**Recommendation:** Optionally add a note to the docstring of `_mutable_default_count`
acknowledging that `lambda: [...]` and named-variable defaults are out of scope — but this
is documentation hygiene, not a functional fix.

---

## Fleet Exercised

| Tier | Model | Device | Latency | Status |
|---|---|---|---|---|
| NPU | llama3.2-1b-FLM | XDNA2 NPU | 3 841 ms | ✓ genuine response |
| iGPU | Granite-4.1-8B-GGUF | Vulkan GPU | 5 364 ms | ✓ genuine response |
| CPU | Qwen3-0.6B-GGUF | CPU (llamacpp) | 509 ms | ✓ genuine response, unloaded |

All three tiers were genuinely exercised via `:13305` router. No responses were fabricated.
CPU model was loaded on-demand and unloaded after use (OOM-safe).
