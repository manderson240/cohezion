# Cohezion Code Review Instructions

This file configures automated and AI-assisted code review for this repository.
Contents are injected as the highest-priority instruction block for Claude Code's
review pipeline and any compatible AI review tool.

---

## Cohezion-Specific Rules (Enforce These)

### P0 — Never Grow God Objects
Files over 500 lines are hard-limit violations (CLAUDE.md). Flag any commit that grows:
- `src/cohezion/api/__init__.py` beyond its current 2,113 lines (already P0 — do not add to it)
- `src/cohezion/compound/executor.py` beyond its current 1,443 lines (already P0 — do not add to it)

For any PR that adds >100 lines to either file, comment: "This file is already a P0 god object.
Route the new behavior to a separate module and wire it in."

### P0 — No Broad `except Exception` Stealth Catches
Flag `except (SubclassError, Exception)` tuples — because `Exception` is a supertype, the tuple
is semantically identical to `except Exception:`. Use only sibling-or-unrelated types in except
tuples (e.g. `except (ImportError, AttributeError, KeyError, TypeError, ValueError)`).

This is Learning L359. New bare `except Exception:` or stealthy superset tuples should not be
introduced; the existing 1,607 are being remediated in phases.

### P0 — No Direct Port Bypass in Live Inference Paths
Any new code in `src/cohezion/` referencing ports `11434`, `13306`, `13307`, `13308`, or `13309`
directly (not via `# allow-direct-port: <reason>`) violates Harness N4.

The canonical inference entry point is `:13305` (the OmniRouter). New inference code must use
`build_gaia_llm_tier()` or `build_reasoning_orchestrator()`, not direct port references.

### P1 — Wire-at-Creation
Any new `src/` module must declare a wiring target at creation time: which step in
`CompoundExecutor`, which detector, or which registry entry it connects to. A module with no
wiring is a Wire-at-Creation violation (Learning L227). Flag with: "What is this module's wiring
target? Declare it in `__init__.py` or wire it to CompoundExecutor, DegradationDetector, or the
skill registry."

### P1 — FLUME-First
New modules that process semantic content must route through FLUME encode/decode. Bypass is allowed
only for performance-critical hot paths with explicit comment. Flag raw string comparison where
cosine similarity against the latent space was intended.

### P1 — Subprocessing Must Use `.venv` Python
Any `subprocess.run([python, ...])` must use the `.venv/bin/python3` path, not `sys.executable`.
See Learning L367. Flag any new subprocess call using `sys.executable` for Python invocation.

### P2 — No `sys.path.insert` with Hardcoded Home Paths
`sys.path.insert(0, "/home/...")` is forbidden. Use relative imports or `PYTHONPATH`.
Pre-commit hook (`no-hardcoded-home-paths`) enforces this, but flag in review as well.

### P2 — No Em-Dashes in YAML Frontmatter or Code-Generating Templates
The `—` (U+2014) character in skill names generates invalid Python class names. Flag any `.md`
file with YAML frontmatter containing em-dashes in `name:` or `slug:` fields.

### P2 — YAML Frontmatter for Structured Config
Files in `src/cohezion/skills/`, `.agent/`, and `docs/plans/` that are structured config or state
MUST use YAML frontmatter `.md` format, not JSON. JSON is for wire formats only.

---

## Ponytail Decision Ladder (Before Coding)

When reviewing PRs that add new code, ask: did the author consider these in order?

1. Could config, data, or a prompt solve this instead of code?
2. Does this already exist in the codebase? (The 1,607 existing modules are not all discoverable by inspection)
3. Is this in stdlib? (`pathlib`, `dataclasses`, `functools`, `contextlib`)
4. Is this in an already-installed dep? (check `pyproject.toml`)
5. Is this a one-liner? (inline it rather than creating a module)
6. Only after the above: new code, minimum viable, no scaffolding

Flag PRs that introduce new modules where an existing module would have sufficed.

---

## Positive Patterns (Affirm These)

- Tests written against the compound engineering loop structure (not just unit stubs)
- New inference paths using `build_gaia_llm_tier()` rather than direct HTTP calls
- Skill files with valid YAML frontmatter and a `wiring_target:` field
- `async/await` throughout I/O paths with explicit timeouts
- `DegradationDetector.set_routing_callback()` wired after ExecutorFactory usage

---

## Invariants Checked by CI (Do Not Override)

The following are enforced by `make validate` (23 checks) and `harness_check.py`:
- `worktree.baseRef == "head"` (C1)
- `SemanticCache.similarity_threshold` is encoder-calibrated (CA1)
- `task_classifier.py` classifies all 8 fixture cases correctly (CL1)
- `DegradationDetector.suggest_routing_tier()` returns from `{"npu","igpu","cpu"}` (CB12)
- No `ctx_size=0` loads on heavy models via `:13305` (N3)

Do not approve PRs that break passing harness invariants.

---

## Local Inference Context

This codebase runs on AMD Strix Halo (Ryzen AI MAX+ 395, 128 GiB unified memory).
All inference should prefer the OmniRouter at `:13305`. The FLM fleet includes:
- `llama3.2-1b-FLM` — 42 TPS, classification/routing
- `deepseek-r1-0528-8b-FLM` — 10.6 TPS, reasoning tasks
- `Gemma-4-E4B-it-GGUF` — iGPU, code gen/synthesis

Never recommend CUDA-specific optimizations; this hardware uses ROCm/RDNA3.5.
