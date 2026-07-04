# Onboarding Audit — 2026-06-25

**Scope:** Clone-to-first-test path. Checks: README quickstart, CONTRIBUTING.md, 01-getting-started.md accuracy vs pyproject.toml, CI workflow presence and correct pytest invocation.

**Summary:** 6/8 steps pass. Two issues: (1) `01-getting-started.md` uses `uv pip install -e .` instead of the idiomatic `uv sync`; (2) a `pip install` reference for optional `pocket-tts` should become `uv add`. The core path (clone → `uv sync` → `make validate` → `uv run pytest`) is accurate and current.

---

## Findings Table

| Step | Artifact | Status | Notes |
|------|---------|--------|-------|
| 1 | `README.md` exists | ✅ PASS | Present with quick start, architecture table, AMD inference docs |
| 2 | README quickstart accurate | ✅ PASS | `git clone`, `uv sync`, `make validate`, `make train` — all correct |
| 3 | `CONTRIBUTING.md` exists | ✅ PASS | Present at repo root |
| 4 | `01-getting-started.md` exists | ✅ PASS | Present in `docs/tutorials/` |
| 5 | `uv sync` as package manager | ⚠️ WARN | `01-getting-started.md` uses `uv pip install -e .` (older pattern); README uses `uv sync` (correct) |
| 6 | `pyproject.toml` specifies Python 3.11 | ✅ PASS | `requires-python = "==3.11.*"` |
| 7 | CI workflow exists and uses `uv run pytest` | ✅ PASS | `ci.yml`, `test-coverage.yml`, `surrealdb-tests.yml` all invoke `uv run pytest` |
| 8 | No `pip install` in critical onboarding path | ⚠️ WARN | `01-getting-started.md` mentions `uv pip install pocket-tts`; `INDEX.md` has `pip install pocket-tts` (should be `uv add pocket-tts`) |

---

## Critical Path Accuracy

```
# What README says:
git clone https://github.com/manderson240/cohezion.git && cd cohezion
uv sync          # ✅ correct
make validate    # ✅ correct (23 checks, ~18s)
make train       # ✅ correct
make demo        # ✅ correct

# What 01-getting-started.md says:
uv pip install -e .   # ⚠️ works but not idiomatic — should be `uv sync`
uv run uvicorn cohezion.api:app --reload --port 8080   # ✅ correct
```

---

## Recommended Actions

| Priority | Action |
|----------|--------|
| P2 | Update `01-getting-started.md`: replace `uv pip install -e .` with `uv sync` |
| P3 | Update `INDEX.md` + `01-getting-started.md`: replace `pip install pocket-tts` with `uv add pocket-tts` |
| — | No README quickstart changes needed — already accurate |
| — | CI workflows are current and well-configured |
