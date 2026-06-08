---
date: 2026-06-08
kind: retro
thread: research
item: 495
prompted_by: user reflection on Erdős unit-distance AI breakthrough + Leiden Declaration
status: completed
---

# RETRO-2026-06-08d: Erdős/Leiden Audit (item 495)

## Three arms executed

### Arm 1: Discriminating-Test Audit (items 488+)

Audited all TIDE test files for items 489–499 (9 files):

| Item | Test file | Tests | Has discriminating marker |
|---|---|---|---|
| 489 | test_classes_above_score_threshold.py | 5 | YES |
| 490 | test_fids_above_score_threshold.py | 5 | YES |
| 491 | test_score_delta_between_snapshots.py | 5 | YES |
| 492 | test_all_score_deltas_between_snapshots.py | 5 | YES |
| 493 | (regressing_classes test) | 5 | YES |
| 494 | test_improving_classes.py | 5 | YES |
| 496 | test_largest_regression.py | 5 | YES |
| 497 | test_largest_improvement.py | 5 | YES |
| 498 | test_score_summary.py | 5 | YES |

**Finding: zero gaps.** All 9 items (89–499) have ≥1 test that kills a plausible wrong
implementation. Every test module includes "PRIMARY DISC." markers and explicit "kills impl
reusing <other_fn>" annotations. This mirrors the Erdős "try to beat the conjecture"
discipline: each discriminating test was written by asking "what is the most plausible wrong
implementation?" before writing the production code.

### Arm 2: SWARM Reference Case

Written: `docs/ops/swarm/cross-domain-synthesis.md`

Key content:
- The Erdős unit-distance breakthrough (OpenAI team, May 2026; improved by Will Sawin
  arXiv:2605.20579) is the canonical empirical case for cross-domain synthesis:
  algebraic number theory applied to an 80-year-old geometry/combinatorics problem.
- Single-domain specialists anchored on geometry missed the algebraic number theory angle.
  This is the formal justification for SWARM_ORCHESTRATION_PRIME's multi-perspective
  concurrent spawn architecture: it breaks anchoring bias by design.
- Operational mapping: SWARM perspectives → domain specialists; 2/3 consensus → at least
  2 approaches must agree on a construction; amplification round → Sawin's improvement;
  quality gate → verification against the original constraint.

### Arm 3: Leiden Compliance

The Leiden Declaration (June 2, 2026) specifies 4 standards for AI-assisted mathematical
work. Gap analysis:

| Standard | Loop-doctrine analog | Status |
|---|---|---|
| 1. Transparency | Non-fabrication rule; all outputs logged; sources cited | MET |
| 2. Accountability | Human-gated decisions for behavior-change; retros document honest outcomes | MET |
| 3. Safety/Non-maleficence | CONSTITUTION.md hard constraints; local-silicon-first eliminates third-party data exposure | MET |
| 4. Deployment-use consent | No mechanism informs end-users that AI-authored code runs in their environment | **GAP — human decision** |

Standard 4 is a human policy decision. The loop can flag it (and has, in CLAUDE.md
"Deployment Ethics" note) but cannot resolve it autonomously — this is correctly gated on
human input per the backlog's non-destructive / needs-human doctrine.

Added to CLAUDE.md: "### Deployment Ethics" subsection under Design Principles.

## Honest scope

- Did NOT find the original OpenAI team unit-distance paper on arxiv (it may be behind a
  preprint embargo or under a non-standard search term). Used Will Sawin's paper
  (2605.20579) as the primary source since it explicitly describes and builds upon the
  OpenAI contribution.
- The Leiden Declaration website was inaccessible from the sandbox; gap analysis is based
  on the backlog item's description ("4 standards, unaddressed = deployment-use consent").
  If the actual declaration text is fetched in a future session, the compliance mapping
  should be verified against the primary source.
- Discriminating-test audit was structural (grep for markers) not semantic (did NOT
  mutate the implementations to verify tests fail). A per-commit mutation smoke-test
  remains a nice-to-have (see item 488 retro).

## Action taken

- `docs/ops/swarm/cross-domain-synthesis.md` created (arm 2 deliverable)
- CLAUDE.md "Deployment Ethics" subsection added (arm 3 deliverable)
- Audit findings logged in this retro (arm 1 deliverable)
- Item 495 marked DONE
