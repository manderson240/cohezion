---
name: group-evolving-agents-prime
description: "Group-level agent evolution with cross-agent experience sharing. Implements concepts from GEA (Weng et al., 2025, arXiv:2602.04837) integrated with Cohezion's compound engineering loop."
---

# SKILL: GROUP_EVOLVING_AGENTS_PRIME

## DOMAIN EXPERTISE
Group-level agent evolution with cross-agent experience sharing. Implements
concepts from GEA (Weng et al., 2025, arXiv:2602.04837) integrated with
Cohezion's compound engineering loop.

## KEY TEXTS & CONCEPTS
- **Group Evolution**: Unit of evolution is a *group* of agents, not an individual.
  Parent groups are selected via Performance-Novelty scoring, enabling cross-pollination
  of evolutionary innovations across agent lineages.
- **Performance-Novelty Selection**: `score(i) = alpha_i * sqrt(nov(i))` where alpha
  is task performance and nov is KNN cosine-distance novelty. Performance dominates;
  novelty provides mild exploration bias.
- **Task-Success Vectors**: Binary vectors z_i in {0,1}^D representing which probe
  tasks an agent has solved. Enables discrete capability fingerprinting.
- **Experience Pool Aggregation**: S = union(T_j) for all agents in parent group.
  All evolutionary traces (patches, logs, outcomes) shared across the group.
- **Reflect-Evolve Pipeline**: Analyze aggregated experience -> generate evolution
  directives -> apply framework-level patches -> validate offspring.
- **Monotonic Archive**: Successfully validated agents are retained permanently.
  Archive grows with each generation, preserving diverse evolutionary paths.

## CONVERGENCE WITH COHEZION (PRE-EXISTING)

The following Cohezion components independently developed concepts that parallel GEA:

| GEA Concept | Cohezion Pre-Existing | Module |
|---|---|---|
| Experience Pool | ExperienceCollector (3-tier: Parquet/SurrealDB/Vault) | `flume/experience_collector.py` |
| Reflect Module | RetrospectionEngine + InflectionDetector | `compound/inflection_detector.py` |
| Evolve Module | SkillRefiner (PRIME skill updates) | `compound/skill_refiner.py` |
| Archive | Vault + PRIME Skill Registry (124 skills) | `skills/*.md` |
| Group Consensus | SkillConsensusVoter + DemocraticDebate | `compound/skill_consensus_voter.py` |
| Performance-Novelty Balance | HIHO Stability (0.5 coherence target) | `skills/HIHO_STABILITY_PRIME.md` |
| Agent Capability Vectors | 256D ExperienceEncoder | `flume/experience_encoder.py` |
| Trajectory Tracking | JourneyTracker (12D FLUME) | `compound/journey_tracker.py` |
| Cosine Similarity Matching | TrajectorySearchEngine | `compound/trajectory_search.py` |
| Degradation Detection | DegradationDetector + ModelQualityClassifier | `compound/degradation_detector.py` |
| Experience Persistence | PersistenceAccumulator (novelty-gated) | `compound/exp_persistence/accumulator.py` |
| Feedback Loop | CompoundFeedbackLoop (auto-retry) | `compound/feedback_loop.py` |

## NOVEL GEA CONTRIBUTIONS INTEGRATED

1. **Group-Level Parent Selection** -- formal algorithm for selecting agent groups
   using combined performance * sqrt(novelty) scoring.
2. **Task-Success Vectors** -- discrete binary capability fingerprints (vs Cohezion's
   continuous 256D/12D representations).
3. **KNN Novelty Metric** -- population-relative diversity via M-nearest-neighbor
   cosine distance in task-success space.
4. **Cross-Agent Trace Aggregation** -- formalized shared experience pool where every
   agent accesses all siblings' traces (patches, logs, outcomes).
5. **Monotonic Archive with Ancestor Tracking** -- explicit lineage tracking showing
   how many unique ancestors contributed to each agent's capabilities.

## INSTRUCTION
1. **Build Candidates**: Convert agent execution histories into `AgentCandidate` list
   with `TaskSuccessVector` and novelty scores.
2. **Select Parents**: Use `PerformanceNoveltySelector.select_parent_group()` with
   GEA's `score = alpha * sqrt(nov)` criterion.
3. **Aggregate Experience**: Pool traces from all parents via
   `GroupEvolutionEngine.aggregate_experience()`. Apply quality filtering (>= 0.3)
   to address noise concerns.
4. **Generate Directives**: Reflect on shared pool to produce `EvolutionDirective`
   targeting workflow/tool/prompt/skill improvements.
5. **Apply Patches**: Feed directives to existing `SkillRefiner.refine()` to update
   PRIME skill definitions.
6. **Validate & Archive**: Run offspring through probe tasks. Add passing agents to
   archive via `add_to_archive()`.
7. **Monitor HIHO**: Verify coherence stays near 0.5 -- if GEA selection pressure
   pushes too far toward exploitation, HIHO damping re-balances.

```python
from cohezion.compound.group_evolution import (
    GroupEvolutionEngine,
    PerformanceNoveltySelector,
    NoveltyScorer,
)

engine = GroupEvolutionEngine(
    selector=PerformanceNoveltySelector(group_size=2),
    novelty_scorer=NoveltyScorer(m_neighbors=4),
)

# Build candidates from execution history
candidates = engine.build_candidates(agents, task_ids)

# GEA Algorithm 1: select parent group
parents = engine.select_parents(candidates)

# GEA Algorithm 2: aggregate experience, generate directives
pool = engine.aggregate_experience(parents, trace_sources)
for parent in parents:
    directives = engine.generate_directives(pool, parent.agent_id)
    # Feed directives to SkillRefiner
```

## ATTRIBUTION

Based on concepts from:
> Weng, Z., Antoniades, A., Nathani, D., Zhang, Z., Pu, X., & Wang, X. E.
> (2025). Group-Evolving Agents: Open-Ended Self-Improvement via Experience
> Sharing. *arXiv preprint arXiv:2602.04837*.

This implementation is an independent realization inspired by the paper's
concepts. No code from the original authors was used. At time of integration,
no official code release or license was available. Convergent concepts (see
table above) were developed independently in the Cohezion codebase prior to
the paper's publication.

## FUTURE HOOKS
- **Compound Loop Integration**: Wire `GroupEvolutionEngine` into the
  `CompoundExecutor` 11-step pipeline as an optional evolution phase.
- **Vault Archive Persistence**: Persist archive entries to SurrealDB for
  cross-session evolution continuity.
- **FLUME VAE Bridge**: Map task-success vectors to 256D FLUME space for
  unified trajectory+capability representation.
- **Democratic Debate Evolution**: Use existing DemocraticDebate to run
  GEA-style group reflection rounds with agent personas.

## VERSION
v1.0

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME
- HIHO_STABILITY_PRIME
- TEAM_ORCHESTRATION_PRIME
- EXPERIENCE_VAE_TRAINING_PRIME
