# observer-patch-holography lint report

**Repo:** `/home/mike-anderson/dev/observer-patch-holography/`
**Branch:** `main` (in sync with `origin/main`)
**Linter:** ruff 0.15.1 (no project ruff config; defaults applied)
**Patch generated:** Yes — `observer-patch-holography-lint-autofix.patch` (62 lines, 5 files)

## Status: PATCH READY

Repo was clean before the run. ruff scanned all 339 Python files. Repo restored to original state after capture.

## Lint counts

| | Count |
|---|---|
| Before | 32 |
| Auto-fixed | 5 |
| **After (residual)** | **27** |
| Files modified by patch | 5 |

## Top rules in baseline

| Rule | Count | Description |
|---|---|---|
| F841 | 13 | Unused local variable |
| E402 | 12 | Module-level import not at top of file |
| F401 | 5 | Unused imports — auto-fixable |
| E731 | 2 | Lambda assigned to a variable |

## Top residual rules (NOT auto-fixable)

| Rule | Count | Why not fixed |
|---|---|---|
| F841 | 13 | unused local — likely needs human review (intentional debug locals?) |
| E402 | 12 | imports after env mutation — almost always intentional in scientific scripts |
| E731 | 2 | lambda-to-def conversion — autofix unsafe |

## Files in patch

```
code/ibm_quantum_cloud/programs/stage1_markov_fingerprint.py
code/particles/calibration/implied_p_consistency_audit.py
code/particles/neutrino/test_no_oscillation_import.py
code/particles/neutrino/test_no_pmns_import.py
code/particles/scripts/refresh_reference_values_from_pdg.py
```

## Recommendations

1. The 5-fix patch is purely unused-import removal — very safe.
2. The 12 E402 violations are typical in scientific code that sets `os.environ` before importing CUDA/MPI/etc — review before enforcing.
3. The 13 F841 unused-local cases may flag debug/inspection scaffolding worth keeping; review case-by-case.

## How to apply

```bash
cd /home/mike-anderson/dev/observer-patch-holography
git apply /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda/research/patches/observer-patch-holography-lint-autofix.patch
git diff
ruff check .            # confirm 27 residual
git commit -am "style: ruff auto-fixes (5 unused imports across 5 files)"
```
