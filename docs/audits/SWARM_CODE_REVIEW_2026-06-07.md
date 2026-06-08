---
type: audit
date: 2026-06-07
owner: swarm-orchestration-specialist
method: direct-multimodel
models_used:
  - id: llama3.2-1b-FLM
    tier: NPU (XDNA2)
    port: 13305
    role: simplicity-analyst
  - id: Granite-4.1-8B-GGUF
    tier: iGPU (Vulkan, Granite 4.1 8B)
    port: 13305
    role: correctness-critic
per_file_verdict:
  simplicity_audit.py: PASS (two noted limitations)
  problem_discovery.py: PASS (basename-collision low-severity finding)
  test_boolean_flag_params.py: PASS
  test_mutable_default_args.py: PASS
consensus: PASS — no blocking issues; two low-severity findings logged
---

# Swarm Multi-Model Local-Inference Code Review — 2026-06-07

Session diff reviewed: `0ac0df66d..HEAD`

## Why `democratic_debate` Was Not Used

`src/cohezion/swarm/democratic_debate.py` was inspected and found to be Ollama-wired
(`_call_agent` POSTs to `/api/generate`, Ollama's body shape) against Ollama model names
(`gemma3:4b`, `phi3:mini`, `qwen2.5-coder:7b`) — **not** the `:13305` OpenAI-compat fleet.
Three additional reasons against adapting it:

1. Model names do not match the resident fleet (`llama3.2-1b-FLM`, `Granite-4.1-8B-GGUF`); calling
   them through the router would trigger auto-loads, risking OOM eviction of live sessions.
2. `_gather_proposals` and `_voting_phase` both `asyncio.gather` across 7 personas × N rounds —
   violates K1 OOM discipline (concurrent piled loads banned).
3. The task pre-authorized this fallback: "if `democratic_debate`'s API is hard to drive headlessly,
   fall back to direct `:13305` multi-model calls + a simple majority vote."

**Method used:** direct sequential `POST /api/v1/chat/completions` calls to `:13305`, two distinct
tiers, simple majority vote (2 of 2 agree → consensus).

---

## Fleet at Review Time

```
GET http://localhost:13305/api/v1/health  (Lemonade 10.6.0)
```

| Model | Device | Tier | PID |
|---|---|---|---|
| `llama3.2-1b-FLM` | NPU (XDNA2) | Tier 1 | 42012 |
| `Granite-4.1-8B-GGUF` | GPU (Vulkan) | Tier 2 | 143445 |

Both models were **already loaded** (resident). No pre-loads performed. No models evicted.
Calls were strictly sequential (NPU first, then GPU).

---

## Code Under Review

| File | Change type |
|---|---|
| `src/cohezion/compound/simplicity_audit.py` | NEW: `_boolean_default_count`, `boolean_flag_params` (item 97); `_mutable_default_count`, `mutable_default_args` (item 110) |
| `src/cohezion/compound/problem_discovery.py` | NEW: two `ProblemTemplate` wirings for items 97/110 in `default_templates()` |
| `tests/compound/test_boolean_flag_params.py` | NEW: 9 discriminating tests |
| `tests/compound/test_mutable_default_args.py` | NEW: 9 discriminating tests |

---

## Tier 1 — NPU (llama3.2-1b-FLM)

**Role:** Simplicity analyst — correctness of bool-is-int handling and mutable-default exclusions.

**Prompt questions:**
1. Does `isinstance(d.value, bool)` correctly exclude integers like 1/0?
2. Does `_mutable_default_count` correctly exclude tuples `()`?
3. Edge cases missed (at most 2)?

**Raw response (137 tokens):**
> 1. Yes, correctly excludes integers. `bool` is a subclass of `int` in Python.
> 2. [Confused answer — said "No" but explained they should be excluded; the code does correctly
>    exclude tuples since `()` is `ast.Tuple`, not `ast.List`/`ast.Dict`/`ast.Set`.]
> 3. Edge cases: "functions with no mutable default arguments" (not a real gap — those are
>    correctly not flagged), functions with mutable defaults not in `_MUTABLE_CTOR_NAMES`
>    (generic/uninformative).

**Reviewer note:** 1B NPU model returned low-signal output on Q2 and Q3 (muddled phrasing,
generic non-findings). Per metacognitive-calibration rules, this output is weighted accordingly
— the model confirmed Q1 correctly; Q2/Q3 answers are not actionable. The AST verification
below (ground-truth) supersedes the 1B model's Q2/Q3 responses.

**Tier 1 vote: PASS** (with low-signal qualification on items 2/3)

---

## Tier 2 — iGPU (Granite-4.1-8B-GGUF)

**Role:** Correctness critic — AST node types, test coverage, wiring collision.

**Prompt questions:**
1. Correctness of `isinstance(d.value, bool)`?
2. Are `ast.List`/`ast.Dict`/`ast.Set` the right AST node types? Does it miss list comprehensions?
3. Missing discriminating tests?
4. Basename collision in `default_templates()` keys?

**Raw response (427 tokens, key excerpts):**

> **Verdict: PASS**
>
> 1. `isinstance(d.value, bool)` is appropriate. `isinstance(True, bool)` returns True; the explicit
>    check correctly identifies boolean constants.
>
> 2. `ast.List`, `ast.Dict`, `ast.Set` correctly identify literal mutable containers. List
>    comprehensions `[x for x in ...]` are `ast.ListComp`, not `ast.List`. Detecting them would
>    require more complex analysis. For the scope of this tool, the current implementation is
>    sufficient — it targets the most common and explicit mutable defaults.
>
> 3. No obvious missing discriminating tests were identified.
>
> 4. The basename collision is present but external to the reviewed functions (correct observation).

**Tier 2 vote: PASS** with acknowledgment of the ListComp limitation and the baseline collision.

---

## Reviewer-Synthesized Findings (AST ground-truth, independent of model votes)

### F1 — Known Limitation: `ast.ListComp` not flagged by `_mutable_default_count`

**File:** `simplicity_audit.py` — `_mutable_default_count`
**Severity:** Low (documented limitation, not a correctness bug; the smell is less common)

```python
def f(x=[i for i in range(3)]):  # ast.ListComp, NOT ast.List
    ...
```

`_mutable_default_count` checks `isinstance(d, ast.List | ast.Dict | ast.Set)`. A list
comprehension as a default is `ast.ListComp` and is **not caught**. The same applies to
`{k: v for ...}` (DictComp) and `{v for ...}` (SetComp). Verified via:

```python
>>> type(ast.parse("def f(x=[i for i in range(3)]):\n    pass").body[0].args.defaults[0]).__name__
'ListComp'
```

This is a known limitation (report-only tool, targets the most common explicit forms). No test
covers it, and none should — testing a known-out-of-scope case could mislead readers into
thinking it's supposed to be caught. Recommend logging as a limitation comment in the docstring
if the scope ever expands.

**Action:** None required now. Log as known limitation.

---

### F2 — Low-Severity: Basename collision in `discover_problems` dedup (finding_id non-uniqueness)

**File:** `problem_discovery.py` L84–85; `simplicity_audit.py` ALL output builders (e.g. L268, L328)
**Severity:** Low (pre-existing pattern; new items 97/110 follow the same convention)

All `simplicity_audit` instruments key findings as `f"{path.name}::{node.name}"` — **basename
only** (e.g. `utils.py::helper`, not `src/cohezion/utils.py::helper`).
`default_templates()` uses `lambda f: str(f[0])` for tuple findings, so the `finding_id`
stored in `discover_problems` becomes e.g. `boolean_flag_params:utils.py::helper`.

If the scan paths include two files with the same basename in different directories (e.g.
`a/utils.py` and `b/utils.py`) both containing `def helper(a=True, b=False)`, they produce
the **same** `finding_id`. One actioned in `exclude_known` suppresses both — a phantom dedup.

This is **pre-existing** (affects all 6 instruments, not just the two new ones). The new items
97/110 follow the same convention as their siblings, so introducing per-function `relpath` keying
is a cross-cutting change, not a targeted fix. No test covers this case.

**Action:** File as a backlog item if fine-grained multi-directory scans are ever needed.
No fix in this session (report-only audit, non-blocking).

---

## Per-File Verdicts

| File | Verdict | Notes |
|---|---|---|
| `simplicity_audit.py` (`_boolean_default_count`, `boolean_flag_params`) | **PASS** | Bool-is-int handled correctly; threshold `>=` correct |
| `simplicity_audit.py` (`_mutable_default_count`, `mutable_default_args`) | **PASS** | Tuple/frozenset correctly excluded; ListComp limitation is known and acceptable |
| `problem_discovery.py` (`default_templates()` wiring) | **PASS** | Clean wiring; basename collision is pre-existing, low-severity |
| `tests/compound/test_boolean_flag_params.py` | **PASS** | Discriminating: covers bool-is-int trap, kwonly, threshold boundary, error resilience |
| `tests/compound/test_mutable_default_args.py` | **PASS** | Discriminating: covers tuple-vs-list, frozenset, constructor form, error resilience |

---

## Swarm Consensus

**PASS — no blocking issues.**

Two models on two tiers (NPU + GPU) independently found no correctness blockers. The
reviewer-synthesized analysis (AST ground-truth) confirms the core logic is correct and
the tests are genuinely discriminating. Two low-severity findings are logged above (F1:
ListComp limitation; F2: basename collision); neither requires a fix in this session.

The 1B NPU model (llama3.2-1b-FLM) returned low-signal output on two of three questions;
its affirming vote on Q1 is accurate, and its Q2/Q3 responses are superseded by direct AST
verification. This is consistent with expected 1B capability bounds and is reported honestly.
