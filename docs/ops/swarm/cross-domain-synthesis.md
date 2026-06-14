---
kind: design-note
date: 2026-06-08
thread: swarm-orchestration
triggered_by: item 495 (Erdős/Leiden audit)
status: verified
---

# Cross-Domain Synthesis as a SWARM Value Multiplier

## The Erdős Unit-Distance Breakthrough as Reference Case

In May–June 2026, an OpenAI team proved a new lower bound for the Erdős unit-distance
problem — a 80-year-old combinatorics/geometry conjecture asking how many pairs of unit
distance can exist among n points in the plane. The breakthrough came from algebraic number
theory, a domain that single-specialist mathematicians anchored on combinatorics/geometry
had not applied to this problem.

Will Sawin (arXiv:2605.20579) then amplified the seed further using Golod-Shafarevich
criterion arguments over algebraic number fields — proving an explicit bound of n^{1.014},
which disproofs Erdős's conjecture and establishes the new state of the art.

**The key insight**: neither the OpenAI team nor Sawin were solving a new problem. They were
applying a DIFFERENT DOMAIN'S tools (algebraic number theory) to an old problem anchored to
a SINGLE domain (combinatorics). The cross-domain leap is what a single geometry specialist
misses due to anchoring bias.

## Why This Is the Reference Case for SWARM_ORCHESTRATION_PRIME Multi-Perspective Debate

The SWARM orchestration pattern in Cohezion runs multiple concurrent perspectives on a
problem before reaching consensus. The Erdős breakthrough provides the canonical empirical
justification:

1. **Single-domain specialists anchor**: a mathematician thinking entirely within
   combinatorics/geometry cannot see the algebraic number theory angle. No amount of
   effort within the domain helps.

2. **Multi-perspective recall breaks the anchor**: in the SWARM pattern, a reasoning-specialist
   perspective and a code-specialist perspective and a math-specialist perspective share their
   intermediate findings. The algebraic lens only appears because a different "perspective
   agent" brings it.

3. **The amplifier effect (Sawin's role)**: once the seed insight is discovered, specialists
   from adjacent domains can exploit it quickly. The SWARM's coalition phase (2/3 consensus
   after debate) mirrors this: a strong seed from one perspective gets amplified by the others.

4. **Quality gate necessity**: the Erdős breakthrough required VERIFICATION — the algebraic
   construction was validated against the original combinatorics problem statement. The SWARM
   quality gate (the "discriminating" check in each SWARM output) enforces the same: a cross-
   domain insight doesn't advance until verified against the original constraint.

## Operational Mapping

| SWARM_ORCHESTRATION_PRIME concept | Erdős analog |
|---|---|
| Multi-perspective concurrent spawn | Different specialists approaching the unit-distance problem from geometry, combinatorics, number theory simultaneously |
| 2/3 consensus threshold | At least 2 of 3 approaches had to agree a construction worked before claiming disproof |
| Amplification round (SWARM Round 2) | Sawin's explicit-bound improvement upon the OpenAI seed |
| Quality gate: must beat incumbent on held-out test | Any construction must achieve > n^1 unit distances to beat the Erdős conjecture |
| Fail-soft: if no perspective wins → honest NULL | If no algebraic construction beat the geometric bound → stay at Erdős's n^{1+c/log log n} |

## Directive for Future SWARM Design

> **When the best single-domain solution appears stuck, spawn perspectives from N≥2
> ADJACENT domains before concluding the problem is hard.** The meta-skill the Erdős
> breakthrough teaches is not "think harder within your domain" but "recruit a different
> domain's tools." The SWARM parallel architecture makes this cheap: spawning 3 concurrent
> perspective agents costs the same wall-clock time as 1 sequential attempt.

This principle is now a standing design constraint for any SWARM arm that handles:
- Mathematical optimization problems (routing, scoring, ranking)
- Measurement design (metrics, thresholds, calibration)
- Architecture decisions (where single-discipline thinking anchors on familiar patterns)

## References

- arXiv:2605.20579 — "An explicit lower bound for the unit distance problem" (Will Sawin)
  Describes the OpenAI team's prior contribution and Sawin's algebraic number theory improvement.
- `src/cohezion/skills/SWARM_ORCHESTRATION_PRIME.md` — the SWARM orchestration skill
- `src/cohezion/swarm/team_executor.py` — the production swarm executor
- CLAUDE.md §"Deployment Ethics" — context for responsible multi-agent deployment
