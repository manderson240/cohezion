---
type: Cohezion Audit
date: 2026-06-15
scope: src/cohezion/**
tools: ruff, grep, local inference (Gemma-4-E4B via :13305)
---

# Coding Standards Audit — 2026-06-15

Deterministic scan + local inference judgment (Gemma-4-E4B-it-GGUF via Lemonade :13305).

## Summary

| Category | Count | P0 | P1 | Auto-fix |
|---|---|---|---|---|
| God objects (>500L hard limit) | 15 files | 2 | 8 | — |
| L359 bare `except Exception` | 1,607 clauses | 0 | ~200 production | — |
| S105/S107 hardcoded credentials | 8 | 1 fixed | 0 | done |
| sys.path.insert (production) | 20 files | 1 fixed | 8 | — |
| Hardcoded `/home/mike-anderson/` paths | 10 | 1 fixed | 8 in competition/ | done |
| Ruff auto-fixable (I001/UP037/UP035/etc) | 98 | — | — | **DONE** |
| Missing `__init__.py` in production dirs | 4 fixed | — | — | done |

---

## 1. God Objects (>500 lines — hard limit)

Files exceeding the 500L hard limit (CLAUDE.md: "above 500 = hard limit, refactor immediately"):

| Lines | File | Judgment | Action |
|---|---|---|---|
| 2113 | `api/__init__.py` | **P0 FLAG** — FastAPI god file. All 92 route handlers in one file. | Split by domain: `/routes/genesis.py`, `/routes/compound.py`, `/routes/swarm.py`, etc. |
| 1443 | `compound/executor.py` | **P0 FLAG** — 11-step pipeline, but mixing execution, metrics, healing, and JEPA. | Extract `_metrics_step.py`, `_healing_step.py` into compound/ subpackage |
| 1434 | `inference/task_classifier.py` | P1 — Large but justified. Contains classifier logic + fixture data. | Extract fixture data to `task_classifier_data.py` |
| 1213 | `swarm/cost_aware_router.py` | P1 — Router + 45-model catalog + cost math. | Extract `model_catalog.py` |
| 1181 | `compound/journey_tracker.py` | P1 — Multiple tracker responsibilities. | Separate SurrealDB persistence from in-memory tracking |
| 1174 | `worldviews/tradition_data.py` | SKIP — Pure data constants (16 traditions × 10 steps). Legitimately large. | None |
| 1130 | `core/persistence/surreal_client.py` | P1 — Client + schema + migration in one file | Extract schema definitions |
| 1115 | `universe/capability_eval.py` | P1 | Review for split |
| 1068 | `competition/nemotron_solver/solve.py` | SKIP — Competition notebook-style, not production. | None |
| 1065 | `security/attack_patterns.py` | SKIP — Data file (attack pattern constants). | None |

**Immediate action**: `api/__init__.py` (2113L) and `compound/executor.py` (1443L) are P0 god objects that must be split. Both are actively developed and growing.

---

## 2. L359 Exception Anti-Pattern

**1,607 `except Exception` clauses** found in production code.

From CLAUDE.md (L359): `except (SubclassError, Exception)` is a stealth bare-except because `Exception` is a supertype. Wide catches should name 3–5 specific types.

### Categories found

**Acceptable** (top-level boundaries, `__main__`, MCP servers, CI hooks):
```python
# OK: genuine top-level boundary
except Exception as e:
    logger.critical(f"Server crashed: {e}")
    sys.exit(1)
```

**Violation** (mid-stack swallowing):
```python
# VIOLATION: swallows specific errors, prevents caller retry
try:
    result = await call_model(prompt)
except Exception:
    return None  # caller never knows what failed
```

### Priority files to fix first

Files with the highest `except Exception` density in core compound loop:
1. `compound/executor.py` — executor must propagate specific inference errors
2. `compound/journey_tracker.py` — SurrealDB errors must be typed
3. `inference/task_classifier.py` — classification errors must be `ClassificationError`

**Recommended pattern** (from L359 guidance):
```python
# Before (stealth bare-except):
except Exception as e:
    logger.warning(f"Failed: {e}")
    return default

# After (typed, specific):
except (httpx.TimeoutException, httpx.ConnectError, json.JSONDecodeError) as e:
    logger.warning(f"Network/parse failure: {e}")
    return default
except RuntimeError as e:
    logger.error(f"Model error: {e}")
    raise
```

**Scale**: 1,607 clauses cannot be fixed in one session. Recommend a phased approach:
- Phase 1: Core compound loop files (~15 files, ~200 clauses)
- Phase 2: Inference + swarm (~20 files)
- Phase 3: Competition/ (low priority — notebook-style)

---

## 3. Security Findings

### S107 — Hardcoded password (5 hits): **FALSE POSITIVES — SKIP**
All 5 are ML tokenizer special tokens: `bos_token="<BOS>"`, `eos_token="<EOS>"`, `unk_token="<UNK>"`.
Ruff's S107 pattern-matches on parameter names containing "token". These are NOT passwords.

### S105 — Hardcoded credential string: **FIXED**
```python
# BEFORE (genesis_persistence.py:30)
SURREAL_PASS = "root"

# AFTER — now env-backed with dev default
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
```
Note: SurrealDB is localhost-only, so this was low severity. Fixed for config pattern consistency.

### S102 — exec() builtin (8 hits): **REVIEW — ACCEPTABLE WITH GUARD**
`unified_harness.py:161`: `exec(code, namespace)` runs in an isolated namespace. This is deliberate dynamic execution for the agentic harness. Must ensure `code` is never from untrusted input.

### S324 — Insecure hash functions (3 hits): **REVIEW**
Check if these are for cryptographic security (FAIL) or content checksums (ACCEPTABLE).
```bash
uv run ruff check src/cohezion/ --select=S324
```

### S310 — URL open (41 hits): **ACCEPTABLE**
All are `urllib.request.urlretrieve` / `urlopen` for HTTP. Ruff flags because `file://` URLs would be dangerous. These all use `https://` or constructed URLs, not user-supplied file:// paths.

---

## 4. sys.path.insert Violations

### P0 FIXED: Hardcoded home path
```python
# BEFORE: physics/usd_simulator.py:13
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

# AFTER: sys import removed entirely (module already on package path)
```

### P1 Production files (8 — scripts running from repo root):
These use `PROJECT_ROOT / "src"` or `Path(__file__).parent.parent.parent` patterns — acceptable for standalone scripts that must be invokable outside of `uv run`. However they indicate the scripts aren't properly installed as package entry points.

**Pattern to adopt** (from CLAUDE.md L367):
```python
# Use the venv python directly, never sys.path.insert in production
# Add as pyproject.toml entry point instead:
# [project.scripts]
# cohezion-guard = "cohezion.healing.scripts.trajectory_guard:main"
```

### Notebooks/competition (competition/ scripts):
These are Kaggle notebook-style files. `sys.path.insert` is expected. SKIP.

---

## 5. Hardcoded `/home/mike-anderson/` Paths

All 8 remaining instances are in `competition/` scripts (Kaggle notebook-style).
These are acceptable for competition code but should not migrate to production.

**Fixed**: `physics/usd_simulator.py` (removed hardcoded path entirely).

**Remaining in competition/ — ACCEPTABLE** (8 files):
- `competition/experience_solver.py:159`
- `competition/orchestrator/review_paper.py:81`
- `competition/neurogolf/meta_train.py:73`
- `competition/neurogolf/validate_100.py:84`
- `competition/kaggle_submission_arc.py:48`
- `competition/sei_accelathon/assessment.py:43`
- `competition/evaluate_solver.py:13`
- `competition/arc_prize_paper_track/ablation_study.py:114`

---

## 6. Ruff Auto-Fixes Applied

**98 violations fixed** in this session via `ruff --fix`:

| Rule | Count | What Was Fixed |
|---|---|---|
| UP037 | 46 | Quoted annotations → native PEP 604 `X \| Y` syntax |
| I001 | 38 | Import sort order |
| SIM114 | 2 | Duplicate if/elif arms → consolidated |
| UP017 | 2 | `datetime.timezone.utc` → `datetime.UTC` |
| RUF022 | 4 | Unsorted `__all__` |
| Other | 6 | Misc auto-fixable |

**Remaining (not auto-fixable, require judgment):** 226 violations.

---

## 7. Missing `__init__.py` — FIXED

Added 4 missing package init files:
- `src/cohezion/patterns/__init__.py`
- `src/cohezion/memory/__init__.py`
- `src/cohezion/knowledge/__init__.py`
- `src/cohezion/evo/__init__.py`

---

## Priority Remediation Queue

### This Sprint (P0)
1. **Split `api/__init__.py`** — 2113L → router modules by domain
2. **Split `compound/executor.py`** — 1443L → extract metrics/healing steps
3. **L359 Phase 1** — Fix `except Exception` in compound loop (executor, journey_tracker, task_classifier)

### Next Sprint (P1)
4. `inference/task_classifier.py` — extract fixture data constant file
5. `swarm/cost_aware_router.py` — extract `model_catalog.py`
6. Convert 8 standalone scripts to proper `pyproject.toml` entry points (eliminate sys.path.insert)
7. S324 hash function review (3 hits)

### Ongoing
8. L359 Phase 2 — inference/ + swarm/ modules
9. Monitor `api/__init__.py` growth — add CI line count gate

---

## What Changed This Session

| Action | Files | Status |
|---|---|---|
| `ruff --fix` auto-fixes | ~40 files | ✅ done |
| `SURREAL_PASS` → env-backed | `genesis_persistence.py` | ✅ done |
| Remove hardcoded path | `physics/usd_simulator.py` | ✅ done |
| Add missing `__init__.py` | 4 dirs | ✅ done |
| OKF `type:` frontmatter | 250 skills | ✅ done (prior session) |
| `cohezion infer` CLI | `__main__.py` | ✅ done (prior session) |
