# Adversarial Review — commits 091770a1f..HEAD

**Reviewer:** Adversarial Review Specialist (Cohezion)
**Commits reviewed:**
- `58a188b68` feat(agents): 18 specialist agent definitions + fix(compound): DRR non-blocking, MCP vault methods, context tolerance
- `9c023456d` fix(tests): remove test_attack_patterns.py (imports nonexistent AttackPatternDatabase)
- `1bcd5a546` feat(autocontext): init_autocontext + archive_session + SkillQualityDataPipeline
- `c00702919` feat(mcp): vault_search sync wrappers + rate_limiter reset + autoliterature scanner + overnight evo loop + executor V-Model tests

---

## 1. Correctness Issues

### C1 — CRITICAL: `tests/security/test_attack_patterns.py` imports nonexistent `AttackPatternDatabase`
- **Commit:** `58a188b68` re-adds the file; `9c023456d` removed it for exactly this reason.
- **Evidence:** `uv run python -c "from cohezion.security.attack_patterns import AttackPatternDatabase"` fails with `ImportError: cannot import name 'AttackPatternDatabase'`.
- **Impact:** Test collection breaks. The class exists in `cohezion-archive/security/attack_patterns.py` but NOT in `src/cohezion/security/attack_patterns.py`.
- **Severity:** 🔴 CRITICAL — any CI/test run will crash on import.

### C2 — HIGH: MCPClient sync wrappers (`vault_write_sync`, `vault_read_sync`, `vault_delete_sync`) are architecturally broken
- **Location:** `src/cohezion/core/mcp_client.py:255-344`
- **Issue:** The wrappers explicitly create coroutines, try `asyncio.run(coro)`, and on `RuntimeError` (loop already running) they call `coro.close()` to suppress `RuntimeWarning: coroutine was never awaited`. Then they fall back to `asyncio.new_event_loop()` + `run_until_complete()`.
- **Why wrong:**
  1. `coro.close()` leaks the coroutine object without ever running it — the vault write/read/delete is silently dropped.
  2. Creating a nested event loop inside an already-running loop is unsupported in asyncio and can deadlock.
  3. The docstring literally admits this is a suppression hack: *"Explicitly closes coroutines to suppress RuntimeWarning for unawaited coros."*
- **Impact:** Data loss (vault ops silently dropped), potential deadlocks, misleading log-only error handling.
- **Severity:** 🔴 HIGH

### C3 — HIGH: `HIHOStabilityGuard.verify()` returned an awaitable-hack object instead of a real async result
- **Location:** `src/cohezion/compound/stability_guard.py:62-96`
- **Issue:** `_AwaitableStabilityCheckResult.__await__` contains `if False: yield` to trick Python into making it a generator so `await` works. This is semantically wrong: `await` on a non-blocking result should just return immediately, but the `yield` path is never hit. While it technically works, it breaks `inspect.isawaitable`, type checkers, and debugging.
- **Impact:** Technical debt; future refactoring will be fragile.
- **Severity:** 🟡 MEDIUM-HIGH

### C4 — MEDIUM: `SkillQualityDataPipeline` append-only JSONL has no concurrency safety
- **Location:** `src/cohezion/compound/skill_quality_data_pipeline.py:67-73`
- **Issue:** `save_report` opens the file in append mode (`"a"`) without any file locking. If multiple processes or threads write simultaneously, lines can interleave, producing malformed JSONL.
- **Impact:** Data corruption on concurrent writes (e.g., parallel test runs or multi-process overnight loop).
- **Severity:** 🟡 MEDIUM

### C5 — MEDIUM: `vault_search` silently returns `[]` on ANY exception
- **Location:** `src/cohezion/core/mcp_client.py:355-368`
- **Issue:** The outer `except Exception` catches auth errors, connection errors, malformed JSON, etc., and returns `[]`. Callers cannot distinguish "vault empty" from "vault unreachable".
- **Impact:** Silent failures hide operational problems.
- **Severity:** 🟡 MEDIUM

### C6 — LOW: `generate_next_experiments` uses modulo-cycle templates with no dedup
- **Location:** `src/cohezion/compound/autoresearch.py:190-260`
- **Issue:** If `n > len(templates)`, experiments repeat. No dedup logic within the generated list.
- **Impact:** Redundant experiment proposals.
- **Severity:** 🟢 LOW

---

## 2. Safety Concerns

### S1 — HIGH: `autoliterature_scanner.py` downloads and parses arbitrary XML/JSON from the internet with no sandboxing
- **Location:** `scripts/autoliterature_scanner.py`
- **Issues:**
  - `urllib.request` calls to arXiv and HuggingFace with no timeout enforcement on some paths.
  - `xml.etree.ElementTree.parse` on untrusted Atom feeds — XML parsing vulnerabilities (billion laughs, entity expansion) are possible though CPython's ET is generally safe.
  - `json.loads` on HF API responses with no schema validation.
  - `eval()` / `exec()` NOT present in diff (verified via grep).
- **Impact:** Remote compromise via malicious XML/JSON if arXiv/HF serve attacker-controlled content.
- **Mitigation:** Add timeouts, use `defusedxml`, validate response schemas.
- **Severity:** 🟡 MEDIUM

### S2 — MEDIUM: `overnight_evo_loop.py` and scripts swallow `Exception` with `pass`
- **Evidence:** ~30 `except Exception: pass` or `except Exception: logger.debug(...)` patterns across scripts.
- **Impact:** Attack indicators, data corruption, or resource leaks are silently hidden.
- **Severity:** 🟡 MEDIUM

### S3 — LOW: `rate_limiter.py` reset singleton is test-only but callable in production
- **Location:** `src/cohezion/security/rate_limiter.py:156-165`
- **Issue:** `reset_rate_limiter()` resets global state. No guard preventing production callers.
- **Impact:** Accidental or malicious rate-limit bypass.
- **Severity:** 🟢 LOW

---

## 3. V-Model Gaps

### V1 — HIGH: No Requirements Traceability for 4 new scripts
- **Scripts:** `autoliterature_scanner.py`, `overnight_evo_loop.py` (E65-E70 additions), `e71_dynamic_stopping_driver.py`, `e80_reflective_autoresearch.py`
- **Gap:** No `docs/requirements/` entries, no SRS/SDD artifacts, no traceability matrix linking commits to requirements.
- **Severity:** 🟡 MEDIUM

### V2 — MEDIUM: `docs/reviews/overnight-v-model-review.md` acknowledges review was NOT conducted in the designated worktree
- **Evidence:** Review doc states: *"The designated reviewer worktree ... was not created at session start. This review was conducted from the main checkout."*
- **Gap:** Per V-Model Phase 8, reviews should happen in isolated worktrees to avoid contamination. This was skipped.
- **Severity:** 🟡 MEDIUM

### V3 — MEDIUM: No Integration-Level Tests for `autoliterature_scanner.py`
- **Gap:** Scanner has 0 tests. It is a 893-line script hitting external APIs.
- **Severity:** 🟡 MEDIUM

### V4 — LOW: Agent definitions in `.claude/agents/` lack version metadata
- **Gap:** No `version`, `last_reviewed`, or `V-Model phase` YAML frontmatter fields.
- **Severity:** 🟢 LOW

---

## 4. Test Coverage

| Module / File | Tests Added | Coverage Assessment |
|---------------|-------------|---------------------|
| `test_autocontext_integration.py` | 15 | Good — manifest init, archive, session lifecycle, idempotency, permission edge cases |
| `test_skill_quality_data_pipeline.py` | 14 | Good — save/load/trend, malformed lines, safe filenames, real scorer integration |
| `test_mcp_client_invariants.py` | 28 (280 lines) | Strong — async contract, sync wrappers, fallback behavior, skill_selector AST check |
| `test_executor_vmodel.py` | 111 lines | Structural invariants only (types, signatures). No behavioral integration tests. |
| `test_autorun_spinloop.py` | 89 lines | Regression guard for negative-timeout bug. Good. |
| `test_autoresearch_improvements.py` | 103 lines | Deduplication + HIHO experiment generation. Good. |
| `test_new_experiments_e65_e70.py` | 119 lines | Math/formula checks for adaptive LR, parallel, weighted voting, retirement CV. Lightweight. |
| `test_hermetic_design_patterns.py` | 202 lines | Structure tests for esoteric pattern classes. Low business value but covers code. |
| `test_attack_patterns.py` | 164 lines | **BROKEN** — imports nonexistent class. |
| `test_context_engineering_mcp.py` | Updated | Async mock fixes for `AsyncClient`. Good maintenance. |

**Overall:** Strong unit-test coverage for new modules. Weak integration / e2e coverage for external-API scripts.

---

## 5. Documentation

### D1 — GOOD: Agent definitions are well-structured
- 18 `.claude/agents/*.md` files with clear responsibilities, key skills, and tool lists.

### D2 — GOOD: `overnight-v-model-review.md` is thorough
- Documents prior-session findings with traceable commit references.

### D3 — MEDIUM: `autoliterature_scanner.py` lacks a design doc
- 893-line script with no architecture diagram, data-flow doc, or security review.
- **Severity:** 🟡 MEDIUM

### D4 — LOW: `e71_dynamic_stopping_driver.py` and `e80_reflective_autoresearch.py` have only inline docstrings
- No standalone README or integration guide.
- **Severity:** 🟢 LOW

---

## 6. `RuntimeWarning: coroutine was never awaited` Findings

**Status:** ⚠️ ACKNOWLEDGED BUT NOT FIXED

- **MCPClient `_sync` wrappers** (`vault_write_sync`, `vault_read_sync`, `vault_delete_sync`) explicitly mention suppressing this warning via `coro.close()`.
- **Test `test_skill_selector_uses_vault_search_sync_wrapper`** documents that `skill_selector.py` previously called `vault_find_relevant_context` without `await`, creating the warning. The "fix" was switching to the sync wrapper — a workaround, not a root-cause fix.
- **Root cause:** Sync code paths calling async methods without `await` (or `asyncio.run`) inside an already-running event loop.
- **Proper fix:** Either make `SkillSelector` fully async, or run vault ops in an executor/thread, or refactor MCPClient to expose only sync APIs to sync callers.
- **Severity:** 🔴 HIGH — this is an async contract violation that leads to silent data loss.

---

## 7. Follow-Up Tasks

| ID | Task | Severity | Owner Suggestion |
|----|------|----------|----------------|
| T1 | **Fix `AttackPatternDatabase` import** — either add the class to `src/cohezion/security/attack_patterns.py` or remove the test file again | 🔴 CRITICAL | Security / Agent |
| T2 | **Refactor MCPClient sync wrappers** — replace `asyncio.run` + `coro.close()` hacks with `asyncio.run_coroutine_threadsafe` or a dedicated thread executor. Ensure vault ops never silently drop | 🔴 HIGH | MCP Specialist |
| T3 | **Add file locking to `SkillQualityDataPipeline.save_report`** or switch to SQLite/atomic writes | 🟡 MEDIUM | Data Pipeline |
| T4 | **Add integration tests for `autoliterature_scanner.py`** using `responses` / `respx` mocks | 🟡 MEDIUM | Autoharness Specialist |
| T5 | **Create V-Model traceability matrix** linking E65-E80 experiments to requirements | 🟡 MEDIUM | V-Model Reviewer |
| T6 | **Review `overnight_evo_loop.py` exception swallowing** — replace bare `except Exception: pass` with at-minimum `logger.warning` + exception type checks | 🟡 MEDIUM | Stability Specialist |
| T7 | **Add `defusedxml` or schema validation** to `autoliterature_scanner.py` XML parsing | 🟡 MEDIUM | Security / MCP |
| T8 | **Add `version` and `review_date` metadata** to `.claude/agents/*.md` | 🟢 LOW | Platform Coordinator |
| T9 | **Investigate `_AwaitableStabilityCheckResult`** — refactor to proper sync-return or `async` method | 🟢 LOW | Compound Engineering |
| T10 | **Add `timeout` enforcement** to all `urllib.request` calls in scanner | 🟢 LOW | Autoresearch |
| T11 | **Gate `reset_rate_limiter()` behind `if os.getenv("COHEZION_TEST_MODE")`** to prevent production abuse | 🟢 LOW | Security |
| T12 | **Write architecture doc** for autoliterature pillar (data flow, API contracts, caching) | 🟡 MEDIUM | Autoresearch Specialist |

---

## 8. Severity Summary

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Correctness | 1 (C1) | 2 (C2, C3) | 2 (C4, C5) | 1 (C6) |
| Safety | 0 | 1 (S1) | 1 (S2) | 1 (S3) |
| V-Model | 0 | 0 | 3 (V1, V2, V3) | 1 (V4) |
| Test Coverage | 1 (broken tests) | 0 | 1 (missing integration) | 0 |
| Documentation | 0 | 0 | 1 (D3) | 1 (D4) |
| **Async Bug** | — | **1 (unawaited coroutine)** | — | — |

**Total follow-up tasks:** 12
**Blockers for merge/release:** T1, T2 (CRITICAL + HIGH)
