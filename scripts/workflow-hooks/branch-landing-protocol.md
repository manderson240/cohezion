# Branch-Landing Protocol — ambient CI/CD-to-main via local inference (MANDATORY)

**Origin (2026-07-23):** two landings went to the wrong place — a package committed
straight to vault `main` (no branch/PR/CI/semver), and cz_gateway rode on an unrelated
`fix/repo-health-enforcement` branch (mixed concerns, 5 ahead of main). This rule makes
"land on the right branch → get to main via CI/CD + semver" an **ambient workflow**
driven by hooks, not something the agent has to remember. It is the escalation-gate layer
on top of `git-operations.md` (which supplies the read-only-by-default posture).

Grounded against what leaders ship (2026 research): GitHub Merge Queue / Graphite / Aviator
/ Mergify (rebase-on-main → re-run gates → fast-forward, human clicks merge); OPA/Conftest +
GitHub Rulesets (block-at-commit/push policy-as-code — our guard hook IS this, local-first);
semantic-release / release-please (Conventional Commits → semver bump on land); and the
uniform finding that **no agent platform (Claude Code, Cursor, Devin, Copilot Workspace,
OpenHands) permits agent self-merge** — the agent prepares, a human approves the trunk write.

## The three deterministic guardrails (always on, $0, no inference)

1. **`git-branch-guard.sh`** (PreToolUse[Bash]) — refuses `git commit` on main/master and
   any direct push to main/master. Escape hatch: `CZ_ALLOW_MAIN=1`. This PREVENTS both
   2026-07-23 failures at the moment the command runs, in every repo.
2. **`branch-hygiene.sh`** (SessionStart) — emits `[branch-hygiene] on <branch>, N ahead of
   <base>, on-main=<yes|no>` when sitting on main, or ≥5 ahead. Report-only.
3. Both are policy-as-code (the OPA/Conftest pattern) embedded in the harness, not a SaaS.

## Trigger: `[branch-hygiene] on <branch>, N ahead ...`

When the SessionStart hook emits this, react at the next natural pause (defer if the user has
an urgent task — the state persists):

- **on-main=yes** → you are about to work on main. STOP before the first edit: propose a
  `feat/|fix/|chore/` branch (`cz worktree create <slug>` or `git switch -c`), and only then
  proceed. Never accumulate work on main.
- **on-main=no, N large** → inspect the ahead-range for MIXED CONCERNS
  (`git log --oneline <base>..HEAD` + `git diff --stat <base>..HEAD`). If two unrelated
  threads share the branch (the cz-vs-repo-health case), propose splitting: cherry-pick the
  coherent subset onto a fresh `feat/<slug>` off `origin/<base>`, leave the rest. Surface the
  split; do not execute git history moves without the user's go (`git-operations.md`).

## Trigger: `[land:ready] <branch>` (the ambient lander)

Emitted by the `land-ready-signal.sh` Stop hook as a **cheap once-per-branch nudge** when a
feature branch is clean and ahead of main. It is NOT a "gates passed" signal — it means "this
branch has landable work." **Do not auto-run the expensive pipeline on the nudge** (gates +
review cost time/inference and "clean + ahead" ≠ "done"). Instead: surface it briefly, and
run the pipeline below only when the user confirms (`land it`, or approves when asked). Defer
silently if the user is mid-task — the nudge is once-per-branch, not nagging.

On confirmation, **spawn a background agent** (local inference; off Claude cap) to prepare the
landing — it prepares EVERYTHING up to a fast-forwardable trunk write, and stops there:

1. **[DETERMINISTIC] Sync + re-test on the merge result** (merge-queue semantics): merge
   `origin/<base>` into the branch (never rebase a pushed branch); resolve with judgment
   (union additive-vs-additive; verify claims against live systems).
2. **[DETERMINISTIC] Run the local gate stack** — `scripts/ci/automerge_guard.sh` (7 gates:
   ruff format, ruff check ADVISORY, ruff_ratchet, pytest unit, import smoke, pytest
   inference, version_governance) + gate 8 `~/.claude/rules/harness_check.py` (deep
   invariants) + `scripts/ci/dormancy_scan.py` (blocking). No new ✗ vs the pre-branch
   baseline = pass. These need NO inference — free and certain (Opis / SkillsBench: prove it
   structurally first).
3. **[LOCAL + OLLAMA-CLOUD] Multiperspective adversarial review** — the hard gate that puts
   us AHEAD of other agent platforms (they use single-model or human-only review). Run the
   diff through ≥2 independent local reviewers (scientific-rigor / edge-case / security) via
   the fleet, then one Ollama-Cloud pass for a stronger independent lens. **The producer
   never signs its own done** (`verification-depth.md`, DeadReckon): the agent that wrote the
   code is not the agent that clears it. 2/3 consensus to proceed; divergence escalates one
   tier, not to Claude.
4. **[DETERMINISTIC] Propose the semver bump** — from Conventional Commits in the ahead-range
   (semantic-release / release-please pattern) via `scripts/ci/version_governance.py`:
   additive feature → minor, fix → patch, breaking → major. Edit `pyproject.toml`; surface
   the proposed version.
5. **[HUMAN] Surface "ready to land"** — branch, gates verdict, review consensus, semver
   bump, and the exact fast-forward command. **STOP.** The `git push origin HEAD:<base>` is
   withheld until the user explicitly approves (`git-operations.md`; every leading agent
   platform withholds the trunk write from the agent). On approval, follow the `cohezion-land`
   skill: ancestry check → `git push origin <branch>` → `git push origin HEAD:<base>` →
   log provenance to SurrealDB `automerge_log`.

## What runs where (the quarter-on-a-string split applied to workflow)

- **Deterministic ($0, no inference):** the guard, the hygiene signal, all 8+ gates, semver.
- **Local inference ($0):** the first adversarial-review pass (fleet, :13305).
- **Ollama Cloud (off Claude cap):** the second independent review lens, for a genuine
  gate-quality decision — never for routine steps.
- **Claude cap:** only the human-facing synthesis + the gated push on approval.

## Guardrails (do not regress)

- **Never `git push HEAD:main` autonomously** — the trunk write is always human-approved.
  Hooks PREPARE and GATE; they never mutate the trunk. (`git-operations.md`, "user presses
  send" — `feedback_user_sends_all_external_comms`.)
- **Fast-forward, never squash** — squash silently drops functions (Learning 363 / the
  six-dropped-surfaces incident). `automerge_guard.sh`'s `gh pr merge --squash` is
  gates-ONLY; the actual land uses the `cohezion-land` ff-push.
- **Producer ≠ verifier** — the review agent must have fresh context and assume the diff is
  broken; a read-only reviewer that reasons but cannot run the gates does not clear a landing.
- **One retro per `[land:ready]`; the user's priority wins** (defer, the marker persists).

## Future (proposed, not yet built)

- **OTel spans per gate** (`cicd.pipeline.run`, `vcs.change`, `merge.gate.review_model`) so a
  blocked branch is trace-debuggable — the OpenTelemetry CI/CD semconv the research flagged.
- **`[land:ready]` auto-emission** from a Stop hook once gates are green, closing the loop
  from "I noticed you're ready" to "here's the prepared landing."
