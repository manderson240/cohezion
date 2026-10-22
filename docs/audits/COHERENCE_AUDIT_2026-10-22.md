---
type: audit
title: Coherence Audit 2026-10-22
date: 2026-10-22
scope: origin/main b3342cf18 (1.27.1)
status: tranche-1-landed
tags: [coherence, portfolio, security, repo-hygiene]
---

# Coherence Audit — 2026-10-22

**Standard:** a senior reviewer with five minutes and no context should be able to tell what
Cohezion is, trust the numbers it claims, run one thing that works, and find nothing that
undermines confidence (leaked secrets, garbage in the root, claims the code does not back).
That is the bar a portfolio piece has to clear before anyone reads the physics.

**Scope of this audit:** `origin/main` at `b3342cf18` (version 1.27.1), measured on 2026-10-22.
Every number below was produced by a command on that tree, not recalled from a document.

**What landed with this audit (tranche 1):** see [Landed](#landed-in-this-change). Everything
else is report-only. Per the non-destructive wiring policy nothing is proposed for deletion;
duplicates are proposed for integration into a canonical sibling.

---

## 1. Measured state

| Dimension | Measured | Where the number came from |
|---|---|---|
| Source | 448,696 lines of Python under `src/cohezion/` | `find … \| xargs cat \| wc -l` |
| Top-level packages | 105 tracked; the working checkout shows 120 directories, 15 of them untracked (4 empty) | `ls -d src/cohezion/*/` |
| Tests | 13,905 collected in 29 s | `uv run pytest tests/ --collect-only -q` |
| CI on main | last 6 runs green, 9–12 min each; CodeQL green | `gh run list --workflow ci.yml --branch main` |
| Skills | 302 PRIME skill files in `src/cohezion/skills/` | `ls src/cohezion/skills/*.md \| wc -l` |
| Docs | 2,100 files; 107 top-level markdown files in `docs/`; `tutorials/` alone holds 721 files | `find docs -type f` |
| Scripts | 1,404 Python files across 472 subdirectories of `scripts/` | `find scripts -name '*.py'` |
| Repository root | 69 non-hidden items before this change, 59 after (guard warns above 50, fails above 75) | `root_health_guard.py` |
| Branches | 308 remote, 186 local; 54 local branches already merged into main and never deleted | `git branch -r`, `git branch --merged origin/main` |
| Worktrees | 87 registered, 2 pointing at directories that no longer exist | `git worktree list` |
| LFS | 22 media files (`.wav`, `.mp3`, `.mp4`, about 10 MB) committed raw where `.gitattributes` says they should be pointers | clone output: "22 files that should have been pointers" |
| Ignore debt | 188 tracked files match existing `.gitignore` rules (`*.log`, `run_*`, `overnight*`, `team_*`, `conductor/`, …) | `git ls-files -i -c --exclude-standard` |
| Lock drift | none on main (`uv.lock` and `pyproject.toml` both 1.27.1); the main *checkout* sits on a branch at 1.22.3 | `awk` on `uv.lock` at both refs |

---

## 2. Findings, ranked by how fast they lose a reviewer

### F1 — Secrets in the public repository (critical, user action required)

- `cloud-vault-mcp/run_mcp.py` on public `main` assigned the vault MCP API key as a string literal.
  The same key is the one the running `cohezion-vault.service` uses. **Fixed in this change**
  (the launcher now requires `MCP_API_KEY` from the environment and exits 2 without it), but the
  literal stays in history until rotated. Rotation is the fix; the code change only stops re-leaking.
- Commit `3eecb6278` (2026-08-13) added a real `.env` with roughly twenty live credentials
  (HF, Kaggle, Telegram, OpenAI, GitHub, Tavily, BlueQubit, O'Reilly, Radeon Cloud, MCP). Untracking
  it on 2026-09-08 did not remove it from history. Every one of those keys is compromised until rotated.
- `.secrets.baseline` dates from 2026-02-09 and allowlists the `run_mcp.py` finding, which is why
  `detect-secrets` never objected. The baseline needs regenerating after rotation.
- The vault MCP server itself (`cloud-vault-mcp/src/mcp_server/main.py`) used to *warn* rather than
  refuse when `MCP_API_KEY` was unset. Given that this server was reachable from the internet with no
  auth on 2026-10-20, it now fails closed at every entrypoint (**fixed in this change**, with
  `MCP_ALLOW_UNAUTHENTICATED=1` as the explicit opt-out for isolated development hosts).

**Action (user only):** rotate every key named above; then regenerate `.secrets.baseline`. A history
rewrite is optional and does not un-leak anything; it only shrinks the attack surface for future clones.

### F2 — The root directory reads as a scratch disk (high)

Before this change the root carried an empty file named `EOF`, a tracked SQLite database
(`runs/autocontext.sqlite3`), a tracked 250 KB JPEG, a one-off experiment script, a `satus/`
directory (typo of status), prompt drafts (`spdd/`), 10 MB of narration audio (`status_update/`),
a stray vault fragment and scenario fixtures. None of them had a consumer in `src/`, `scripts/`,
`tests/`, the Makefile or CI. The working checkout additionally held about 50 untracked loose files
(competition submissions, `*_response.json`, analysis scripts, logs, a zip) plus three files whose
names are shell accidents (`--nets`, `**2026-10-15`, and one named after a Python fragment).

**Landed:** the nine tracked items moved to `docs/archive/root-sweep-2026-10-22/`; `EOF` removed;
root-anchored ignore rules added so this class cannot recur. Root count 69 → 59.
**Remaining to reach the guard's target (<50):** candidates with no code consumer are
`tests_mycelium/`, `onnx_models/`, `AGENT_COORDINATION.md`, `AGENT-SURFACES.md`,
`autoresearch-dashboard.md`, and the six `autoresearch*` files (which do have hook consumers and
would need the hooks re-pointed if grouped under one directory). The three shell-accident files in
the working checkout are untracked and should simply be deleted by the owner.

### F3 — Claims the code does not back (high)

| Claim | Where | Measured |
|---|---|---|
| "182 skills" (4 places) | README | 302 |
| "12,000+ test suite" | README | 13,905 collected |
| "6,133 tests collected" | CLAUDE.md | 13,905 collected |
| "95%+ hit rates in internal runs" | README (semantic cache) | no artifact in the repo reproduces it |
| "50+ checks" for `make validate` | README, Makefile | 27 steps (CLAUDE.md said 23); corrected in all three |

**Landed:** skill, test and validator counts corrected in README, CLAUDE.md and the Makefile. The
cache hit-rate claim is left in place and flagged: either attach the run that produced it under
`docs/benchmarks/` or soften the wording.

### F4 — Package-level duplication (medium, structural)

105 top-level packages is too many to hold in one head, and eleven of them come in near-duplicate
name pairs. Proposed canonical targets (integration, never deletion; verify consumers with
`git grep` and the codebase graph before each move):

| Keep (canonical) | Fold in | Files | Note |
|---|---|---|---|
| `data_mesh/` (23) | `datamesh/` (8) | 31 | same concept, two spellings |
| `sandbox/` (7) | `sandboxing/` (2) | 9 | |
| `simulation/` (13) | `simulations/` (5) | 18 | `simulations/` is already matched by an ignore rule — its files are tracked by accident |
| `benchmarks/` (9) | `benchmark/` (1) | 10 | |
| `agents/` (38) | `agent/` (6) | 44 | |
| `competition/` (69) | `competitions/` (39) | 108 | large; audit both before choosing |
| `research/` (23) | `researcher/` (9) | 32 | `researcher/` is the daily-researcher orchestrator; may deserve to stay as `research/daily/` |
| `infra/` (1) | `infrastructure/` (1) | 2 | both nearly empty |
| `eval/` (9) | `evaluation/` (empty, untracked) | 9 | remove the empty directory from the working checkout |
| `pipeline/` (5) | `pipelines/` (empty, untracked) | 5 | same |
| `api/` (59) | `api.py` (1) | 60 | root-level module shadows the package name; move or rename |

**Not a duplicate:** `model/` (the `CohezionLM` implementation) versus `models/` (pydantic/dataclass
definitions). The names collide; the contents do not. Rename one for clarity, do not merge.

**Also inside `src/`:** `src/cohezion-archive/` is a second, archived copy of swarm modules (182 tracked files) living
beside the live package. It belongs under `docs/archive/` or in git history, not on the import path.

### F5 — Documentation sprawl (medium)

2,100 files; 107 top-level markdown documents in `docs/`, including acknowledged duplicates
(`INSTALL.md`/`INSTALLATION.md`; `DEPLOY.md`/`DEPLOYMENT.md`/`DEPLOYMENT_PLAN.md`/`deployment-guide.md`).
`docs/tutorials/` holds 721 files, which is not a tutorial set but a dump. `sessions/` (125),
`archaeology/` (142), `reconcile/` (96) and `archived-status/` (44) are session residue that should
live under `docs/archive/` with one index each. The target shape is: README → `docs/README.md` →
no more than ~25 living top-level documents, everything else under `archive/` with a dated index.

### F6 — Branch and worktree debt (medium, hygiene)

308 remote branches, 186 local, 54 of the local ones fully merged. 87 registered worktrees, two
dangling. The main checkout itself sits on `security/codeql-wave2`, 21 commits ahead and 56 behind
main, with 131 modified files, 9 tracked dotfiles showing as deleted (including `.gitignore` and
`.pre-commit-config.yaml`, which is why the root looked even noisier than it is) and 687 untracked
files. A reviewer who clones sees none of this, but every agent session that starts here does.

**Proposed:** `git branch -d` the 54 merged locals; `git worktree prune`; archive or delete remote
branches whose PRs are merged; restore the deleted dotfiles in the main checkout
(`git checkout -- .gitignore .gitattributes .pre-commit-config.yaml …`) after confirming no session
depends on their absence.

### F7 — Enforcement that is declared but not installed (medium)

22 media files are committed raw although `.gitattributes` routes them to LFS. The `lfs-pointer-check`
hook that CLAUDE.md says "enforces this automatically" is a pre-commit hook, and pre-commit is not
installed in this checkout. The same applies to the 188 tracked files that match ignore rules: they
were added with `-f` or before the rule existed, and nothing re-checks. **Proposed:** `git add
--renormalize` the 22 media files in one commit (converts them to pointers without rewriting history),
install pre-commit in the main checkout, and add a CI step that fails when `git ls-files -i -c
--exclude-standard` grows.

### F8 — Version drift between main and the working checkout (low)

An earlier draft of this audit reported `uv.lock` pinned at 1.22.3 against a 1.27.x
`pyproject.toml`. That reading came from the main *checkout*, which sits on `security/codeql-wave2`
at version 1.22.3; on `origin/main` the lock and the project file agree (1.27.1, now 1.27.2 with
the lock updated in this change). The real finding is the one in F6: the primary checkout is 56
commits behind main and five minor versions old, so anything measured there about "the repo" is
measured against a stale branch. **Proposed:** keep the primary checkout on main; do branch work
in worktrees or clones (see F6).

---

## 3. Landed in this change

1. `cloud-vault-mcp/run_mcp.py` carries no key; `cloud-vault-mcp/src/mcp_server/main.py` refuses to start without `MCP_API_KEY` (every entrypoint).
2. Root sweep: `EOF` removed; `satus/`, `spdd/`, `status_update/`, `runs/`, `reports/`, `vaults/`,
   `knowledge/`, `particles-casberry.jpeg`, `skill_density_experiment.py` moved to
   `docs/archive/root-sweep-2026-10-22/`.
3. Root-anchored `.gitignore` rules for loose code, data, results and JS tooling (verified to hide
   no currently tracked file).
4. README, CLAUDE.md and Makefile counts corrected to measured values (302 skills, 13,905 tests, 27 validator steps).
5. Version 1.27.1 → 1.27.2 with a CHANGELOG entry.

---

## 4. Remediation plan

| Tranche | Owner | Content | Done when |
|---|---|---|---|
| T0 | user | Rotate every key in F1; regenerate `.secrets.baseline` | no literal in `run_mcp.py` matches a live key; baseline has no `run_mcp.py` entry |
| T1 | this PR | F2 sweep, F3 counts, ignore rules, launcher fix | merged |
| T2 | done (branch `chore/lfs-ignore-debt`) | F7: 22 media files renormalized; hygiene ratchet gates ignore debt + LFS pointers | fresh clone reports 0 non-pointer LFS files; ignore-debt baseline 188 measured and gated |
| T3 | agent session | F6: delete merged locals, prune worktrees, restore dotfiles in the main checkout | `git branch --merged origin/main` lists only main; `git worktree list` has no dangling entries |
| T4 | agent session per pair | F4: one PR per duplicate pair, integrate-then-empty, consumers re-pointed, tests green | package count ≤ 95; no name-pair duplicates; `src/cohezion-archive/` gone from `src/` |
| T5 | agent session | F5: merge the acknowledged duplicate docs; move session residue under `docs/archive/`; cap living top-level docs at ~25 | `ls docs/*.md \| wc -l` ≤ 25 and `docs/README.md` indexes all of them |
| T6 | user + agent | Portfolio narrative: README leads with the three things a reviewer can run in ten minutes (`examples/quickstart.py`, `make validate`, `make train`), each with the exact expected output; attach the artifact behind every remaining quantitative claim | every number in the README links to a file or command that reproduces it |

The order is deliberate: T0 and T1 remove disqualifiers; T2–T3 stop the bleeding; T4–T5 are the
structural work that makes the codebase legible; T6 is the presentation layer and only pays off once
the layers under it are true.

---

## 5. What the portfolio pitch should be

Cohezion's defensible, differentiated story is narrow and strong: **a self-improving agent
orchestration loop that runs end-to-end on consumer AMD silicon at zero marginal inference cost,
with a physics-grounded RL environment and a reproducible benchmark behind it.** The 105 packages,
302 skills and 2,100 documents are evidence of effort, not of that story. A reviewer should meet the
story first, run it second, and discover the breadth third. Every tranche above serves that order.
