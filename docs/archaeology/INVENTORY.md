# Archaeology Inventory - Root Cleanup Plan

**Date:** 2026-04-19
**Target:** Reduce root item count from ~487 to ~100
**Strategy:** Batch git mv operations, 1 commit per category

---

## Current State

| Metric | Count |
|--------|-------|
| Total items | ~487 |
| Top-level files | ~355 |
| Directories | ~143 |
| Status/markdown files | ~96 |
| Data/artifact directories | ~106 |

---

## Category 1: AIMO Competition Outputs (7 items)

**Target:** `research/challenges/aimo/`

| Item | Destination | Notes |
|------|-------------|-------|
| `aimo3_competition/` | `research/challenges/aimo/` | Competition workspace |
| `aimo3_data/` | `research/challenges/aimo/data/` | Input data |
| `aimo3_solver/` | `research/challenges/aimo/solver/` | Solver code |
| `aimo_v22_final/` | `research/challenges/aimo/competition_outputs/v22/` | Final outputs |
| `aimo_v23_out/` | `research/challenges/aimo/competition_outputs/v23/` | V23 outputs |
| `aimo_v23_output/` | `research/challenges/aimo/competition_outputs/v23/` | V23 outputs 2 |
| `aimo_v39_output/` | `research/challenges/aimo/competition_outputs/v39/` | V39 outputs |
| `debug_aimo_v39/` | `research/challenges/aimo/debug/v39/` | Debug logs |

---

## Category 2: Status File Archive (96 items)

**Target:** `docs/status/archive/`

These are ephemeral status/SESSION/BREAKTHROUGH/report files that captured state at specific moments. They have historical value but clutter the root.

**Pattern matches:**
- `*STATUS*` - Status reports
- `*COMPLETE*` - Completion markers
- `*SESSION*` - Session summaries
- `*HANDOFF*` - Handoff documents (except latest)
- `*BREAKTHROUGH*` - Breakthrough reports
- `*PROGRESS*` - Progress updates
- `*REPORT*` - Various reports

---

## Category 3: Luma AMD Speedrun (2 items)

**Target:** Keep `luma_speedrun/` at root (active), move competition outputs

| Item | Destination |
|------|-------------|
| `submissions/` | `research/challenges/luma_amd_speedrun/` (if exists) |

---

## Category 4: Legacy Archive Directories (6 items)

**Target:** Clean or move to `docs/archaeology/backups/`

| Item | Action |
|------|--------|
| `.antigravity/` | Review - may be code experiment |
| `.archived/` | Move to `docs/archaeology/backups/.archived/` |
| `.autonomy/` | Review - may contain valuable configs |
| `.branch-preservation/` | Move to `docs/archaeology/backups/.branch-preservation/` |
| `.chief/` | Review - may contain valuable configs |
| `.cohezion/` | Review - cache directory |
| `.code-review-graph/` | Move to `docs/archaeology/backups/.code-review-graph/` |
| `.context/` | Move to `docs/archaeology/backups/.context/` |

---

## Category 5: Executed Commit Sequence

```bash
# Commit 1: AIMO outputs
git mv aimo3_competition research/challenges/aimo/
git mv aimo3_data research/challenges/aimo/data/
git mv aimo3_solver research/challenges/aimo/solver/
...

git commit -m "chore(archaeology): Move AIMO competition outputs to research/challenges/...

Moves 7 aimo-related directories from root to organized research structure.
Preserves git history. Part of root archaeology cleanup."

# Commit 2: Status file archive
...

# Commit 3: Legacy directory archive
...
```

---

## Success Criteria

- [ ] Root item count ≤ 150 (from ~487)
- [ ] All moves preserve git history (`git mv`)
- [ ] No functional code broken
- [ ] README.md, AGENTS.md, pyproject.toml, src/, tests/, docs/scripts remain at root
