---
adr_number: 003
title: Skill Consensus Voter — Multi-Agent Voting Over Single-Agent Authority
date: 2026-04-23
status: ACCEPTED
deciders: cohezion-project
consulted: [compound team, skill refiner, retrospection engine]
informed: [executor pipeline step 5, vault keepers]
authored_by: synthetic-sniffing-panda Wave Ω10 retroactive ADR
---

# ADR-003: Skill Consensus Voter — Multi-Agent Voting Over Single-Agent Authority

## Status

ACCEPTED, 2026-04-23. This ADR is RETROACTIVE — no prior explicit decision document exists; the framing is reconstructed from `src/cohezion/compound/skill_consensus_voter.py` and the SPIN-coherence manuscript's §4.3 multi-agent Kuramoto interpretation.

## Context

Skill refinement (ADR-001 step 5) modifies the executor's PRIME-format skill definitions in response to recent execution outcomes. If a single agent — even a high-quality one — has unilateral authority to mutate skills, three failure modes follow. First, *single-point drift*: a noisy execution chain causes the agent to refine in a direction the rest of the system would reject if asked. Second, *adversarial steering*: prompt injection or compromised input that fools one agent will be silently encoded into the skill library, contaminating all future executions. Third, *over-confidence ratchet*: an agent that successfully refines a skill once gets implicit "this agent is right" weighting in subsequent rounds, eventually producing a dictator that cannot be overridden.

The cohezion architecture treats skills as the *substrate of compounding* — every skill mutation is read by every subsequent execution that retrieves it from the vault. Skill drift is therefore not a per-task bug; it is a corruption of the compounding surface itself. The decision-making protocol over skills must be at least as robust as the guardrail pipeline (ADR-001 step 6), and ideally more so.

The constraints: (a) skill refinement must remain online — batch-only refinement defeats the compound thesis, (b) the protocol must be transparent enough that an external auditor can replay the votes, (c) confidence in the refinement must be a continuous quantity (not just "passed/failed"), and (d) the protocol must degrade gracefully when only a single agent is available.

## Decision

We commit to multi-agent consensus voting on skill refinements via `SkillConsensusVoter` (`src/cohezion/compound/skill_consensus_voter.py`). Each candidate skill is decided by N agents that each rank the top-k options; votes are aggregated by one of three configurable strategies — `MAJORITY` (>50% agreement on the top choice), `WEIGHTED` (votes scaled by the agent's historical coherence score), or `UNANIMOUS` (100% required) — producing a `ConsensusResult` (lines 52-73) with the winning skill, runner-up, vote counts, and a confidence score in [0, 1]. When consensus fails the voter falls back to single-best with `fallback_used=True`, so the protocol always returns a result but the failure is surfaced. Voting metrics are persisted non-blocking to the vault for replay.

## Rationale

Multi-agent voting is the structural defence against the three failure modes above. *Single-point drift* is mitigated because no individual agent can mutate a skill alone — the majority strategy demands a co-signer, the weighted strategy demands sufficient coherence-weighted consensus. *Adversarial steering* is mitigated because an attacker would need to compromise multiple agents simultaneously, and the agents' contexts are kept distinct precisely so that a single prompt-injection vector cannot reach all of them at once. *Over-confidence ratchet* is mitigated by the weighted strategy's coupling of vote weight to historical coherence — an agent that successfully refines gets more weight, but one that refines into a degraded outcome (caught by step 10's degradation detector) loses weight on the next round.

The three-strategy menu (line 22, `VotingStrategy`) is itself a deliberate design choice: different skill domains warrant different consensus stiffness. Safety-critical skills (anything touching guardrails or persistence) can be configured to require `UNANIMOUS`; general refactor-pattern skills can use `MAJORITY`; coherence-tracked skills where some agents are reliably more attuned use `WEIGHTED`. This puts the policy decision at the *skill-domain* layer rather than baking a single global stiffness into the voter.

The Kuramoto-coupling interpretation (manuscript §4.3) is more than analogy: the WEIGHTED strategy literally implements heterogeneous-amplitude phase coupling, where each agent's "rotation" is its ranked skill choice and the coupling strength is its coherence weight. This places the voter inside the SPIN-framework's mathematical vocabulary and lets future work import established results from the synchronization literature (Strogatz, 2000; Pikovsky et al., 2001) — for example, the result that heterogeneous coupling above a critical threshold produces phase locking.

## Alternatives considered

### Option A: Leader-elects (single-agent authority, rotated)
- Pros: Simple; deterministic; no consensus failure mode.
- Cons: Re-introduces single-point drift between rotations; the elected leader becomes a target for adversarial steering for the duration of its term.
- Why rejected: Rotation does not solve the underlying robustness problem; it only smears it across more agents over time.

### Option B: Oracle-judge (one privileged "reviewer" agent decides)
- Pros: Centralized authority; the judge can be a higher-quality model than the worker agents.
- Cons: The judge becomes the single point of failure and the adversary's primary target; privileging one agent contradicts the Strix Halo "many local 3B-7B models" deployment posture.
- Why rejected: Recreates exactly the over-confidence ratchet that voting is designed to prevent.

### Option C: RLHF-style preference learning over skill diffs
- Pros: Continuous learning signal; could in principle learn nuanced skill-quality preferences.
- Cons: Requires preference data we do not have; offline batch learning conflicts with the online compound thesis; reward-hacking risk on a self-modifying system.
- Why rejected: Wrong tool for the protocol problem. RLHF could complement voting (as a future input to coherence weighting), not replace it.

### Option D (chosen): Multi-agent consensus voting (majority / weighted / unanimous)
- Pros: Robust to single-agent drift and adversarial steering; transparent and replayable; degrades gracefully via fallback; weighted strategy gives a Kuramoto-coupling interpretation usable by future analysis.
- Cons: Multiplies LM calls per refinement by N (cost); requires designing per-skill-domain stiffness policy; consensus failures need handling.
- Why chosen: The robustness of the compounding surface is the property we care most about, and voting is the cheapest mechanism that delivers it.

## Consequences

### Positive
- Skill mutations require co-signers; single-agent drift is structurally prevented.
- The weighted strategy creates a feedback loop where degraded outcomes (caught at executor step 10) lower future vote weight.
- Voting metrics are vault-persisted; an auditor can replay any refinement decision.
- Three strategies allow per-skill-domain calibration (safety-critical → unanimous; routine → majority).

### Negative
- N-agent voting multiplies LM calls by N at refinement time; cost router (ADR-002) must understand this.
- Consensus failures are real (`fallback_used=True`); the fallback to single-best partially defeats the robustness goal until the underlying disagreement is resolved.
- Coherence-history weighting requires reliable per-agent coherence tracking — a separate component (`SkillHealthTracker`) that itself can drift.

### Neutral
- The three-strategy menu adds configuration surface; teams must decide per-skill-domain stiffness.
- The voter is one component among many in step 5; replacing it does not require touching the loop.

## Implementation

- Primary files:
  - `src/cohezion/compound/skill_consensus_voter.py` (560 lines; `SkillConsensusVoter` class at line 76; `VotingStrategy` at line 22; `AgentVote` at line 31; `ConsensusResult` at line 52; `vote_on_skills` at line 122; `_vote_majority` at line 179).
  - `src/cohezion/compound/skill_selector.py` (`SkillScore`, the unit each agent ranks).
  - `src/cohezion/compound/skill_refiner.py` (consumer at executor step 5).
  - `src/cohezion/compound/skill_health_tracker.py` (provides `agent_coherence_score` for the WEIGHTED strategy).
- Test files: `tests/compound/test_skill_consensus_voter.py` (covers all three strategies + fallback path).
- Documentation: SPIN-coherence manuscript §4.3; this ADR.

## Verification

- Static check: `grep -nE "VotingStrategy\.(MAJORITY|WEIGHTED|UNANIMOUS)" src/cohezion/compound/skill_consensus_voter.py` confirms all three strategies are wired and reachable.
- Runtime check: `uv run python -c "from cohezion.compound.skill_consensus_voter import SkillConsensusVoter, VotingStrategy; help(SkillConsensusVoter.vote_on_skills)"` documents the protocol.
- Test: `uv run pytest tests/compound/test_skill_consensus_voter.py -q` — confirms majority, weighted, unanimous, and fallback paths each behave per spec.

## Reversal cost

**LOW.** The voter is a single ~560-line module with a narrow public interface (`vote_on_skills` returning `ConsensusResult`). Reverting to single-agent skill refinement requires only that the skill refiner's call site bypass the voter and use a single agent's ranking directly. Estimated effort: 1-3 person-days, plus a deliberate architectural-risk acceptance (the robustness properties this ADR establishes would be forfeited).

## Related ADRs

- Depends on: ADR-001 (the eleven-step loop's step 5 invokes the voter when configured); ADR-002 (cost routing — N-agent voting cost must be understood by the router).
- Informs: future ADR on per-skill-domain stiffness policy (currently implicit in caller code).
- Tension with: ADR-002 (cost) — voting multiplies LM calls; the trade-off favours robustness on the compounding surface.

## References

- `research/manuscripts/2026-04-23-spin-coherence-compound-loop.md` §4.3 (multi-agent Kuramoto generalization).
- Kuramoto, Y. (1975). Self-entrainment of a population of coupled non-linear oscillators. Springer.
- Strogatz, S. H. (2000). From Kuramoto to Crawford. *Physica D*, 143(1-4), 1-20. (Synchronization theory background.)
- Du, Y. et al. (2023). Improving factuality and reasoning in language models through multiagent debate. arXiv:2305.14325. (Multi-agent precedent.)
