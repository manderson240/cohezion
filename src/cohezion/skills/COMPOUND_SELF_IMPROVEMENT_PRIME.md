# COMPOUND_SELF_IMPROVEMENT_PRIME

**Version**: 1.0.0
**Created**: 2026-03-21
**Domain**: Meta-Engineering, Compound Loop, Self-Healing
**Expertise Level**: Advanced (requires understanding of compound engineering pipeline)

## Purpose

Use Cohezion's own compound engineering methodology (Execute → Retrospect → Refine) to improve Cohezion itself. This PRIME skill encodes the self-referential protocol for systematic codebase improvement using TDD, adversarial code review, Ouroboros self-healing, Mycelium test generation, and specialist agent swarms.

**Meta-Principle**: The system achieves HIHO stability (0.5 coherence) by being simultaneously "the code being improved" and "the improvement mechanism."

## Prerequisites

- CompoundExecutor with vault integration operational
- Ouroboros (healer + detector) available
- Mycelium (CoverageLoop + ShadowScripter) functional
- Swarm specialist agents configured (5 streams: Architect, Engineer, Biologist, QHW, QAlgo)
- Vault-first knowledge management active
- Test suite baseline established (run `uv run pytest tests/ -q` to verify)

## Input Parameters

```yaml
improvement_goal: str
  # What aspect of Cohezion needs improvement
  # Examples: "Add precipitation_gate() to AxiomaticState"
  #           "Optimize configuration files for portfolio readiness"
  #           "Create UniverseManager interface for 3 simulators"

target_files: list[str]
  # Specific files to modify (e.g., ["src/cohezion/universe/engine.py"])

context_files: list[str]
  # Reference files for context (e.g., ["src/cohezion/skills/hiho_reality_sim.md"])

quality_thresholds:
  test_coverage_min: float = 95.0  # Minimum test coverage for new code
  coherence_threshold: float = 0.5  # HIHO alignment check before execution
  swarm_consensus_min: float = 0.7  # Minimum agreement among specialist agents

enable_tdd: bool = true
  # Use Test-Driven Development (write tests first, then implementation)

enable_adversarial_review: bool = true
  # Run multi-agent code review after implementation

enable_ouroboros: bool = true
  # Use self-healing for emergent issues

max_iterations: int = 3
  # Maximum refinement cycles before escalation
```

## Execution Protocol

### Phase 1: Alignment Analysis (Request Coherence Check)

**Components**: RequestAlignmentAnalyzer, SkillSelector, JourneyTracker

```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(
    request=improvement_goal,
    available_skills=skill_selector.find_relevant_skills(keywords),
    agent_coherence=journey_tracker.get_coherence_history(),
    computational_budget=token_budget
)

if alignment.coherence < 0.5:  # HIHO threshold
    logger.warning(f"Low alignment: {alignment.issues}")
    action = "decompose_or_escalate"
    # Break into smaller improvements or request human clarification
else:
    action = "proceed"
```

**Success Criteria**: Coherence ≥ 0.5 (HIHO stability)

**Outputs**:
- Alignment score
- Estimated token budget
- Decomposition plan if needed

### Phase 2: Experience Retrieval (Vault Query)

**Components**: VaultLogger, CompoundExecutor.get_experience_guidance()

```python
from cohezion.compound.executor import CompoundExecutor

executor = CompoundExecutor(mcp_client=mcp_client)
guidance = executor.get_experience_guidance(
    task_description=improvement_goal,
    context={"target_files": target_files, "domain": "meta-engineering"}
)

# guidance contains:
# - similar_experiments: list[dict]  # Prior attempts, outcomes, learnings
# - relevant_patterns: list[dict]    # Reusable code patterns
# - known_pitfalls: list[str]        # Historical failure modes
```

**Success Criteria**: At least 1 relevant experiment or pattern retrieved

**Outputs**: Historical guidance dictionary for use in execution

### Phase 3: Test-Driven Implementation (Mycelium Loop)

**Components**: CoverageLoop, ShadowScripter, CompoundExecutor

```python
from cohezion.mycelium.loop import CoverageLoop
from cohezion.mycelium.scripter import ShadowScripter

scripter = ShadowScripter(model_name="qwen3-coder")
loop = CoverageLoop(scripter=scripter, test_output_dir="tests/")

# Step 3.1: Generate tests FIRST (TDD)
for target_file in target_files:
    with open(target_file, "r") as f:
        code_context = f.read()

    # Synthesize comprehensive test suite
    test_code = await scripter.synthesize_test_suite(
        file_path=target_file,
        code_context=code_context
    )

    # Write tests to tests/ directory
    test_file = f"tests/test_{os.path.basename(target_file)}"
    with open(test_file, "w") as f:
        f.write(test_code)

# Step 3.2: Run tests (should FAIL initially - red phase of TDD)
result = subprocess.run(
    ["uv", "run", "pytest", test_file, "-v"],
    capture_output=True
)
assert result.returncode != 0, "Tests should fail before implementation"

# Step 3.3: Implement code to make tests pass (green phase)
implementation = await executor.execute_task(
    task=improvement_goal,
    context={
        "guidance": guidance,
        "test_file": test_file,
        "target_files": target_files
    }
)

# Step 3.4: Iterative coverage improvement (refactor phase)
final_coverage = await loop.execute(
    file_path=target_file,
    code_context=code_context,
    target_coverage=quality_thresholds["test_coverage_min"],
    max_iterations=max_iterations
)
```

**Success Criteria**:
- Tests written before implementation (TDD discipline)
- Final coverage ≥ quality_thresholds["test_coverage_min"]
- All tests passing

**Outputs**:
- Test files written to tests/
- Implementation code added to target_files
- Coverage report

### Phase 4: Adversarial Code Review (Swarm Consensus)

**Components**: TeamExecutor, Specialist Agents (5 streams)

```python
from cohezion.swarm.team_execution import TeamExecutor
from cohezion.swarm.swarm_types import SwarmConfig

# Configure specialist agents
config = SwarmConfig(
    agents=[
        {"role": "architect", "model": "qwen3-coder", "weight": 1.0},
        {"role": "engineer", "model": "qwen3-coder", "weight": 1.0},
        {"role": "biologist", "model": "deepseek-r1:14b", "weight": 0.8},
        {"role": "qhw", "model": "phi3:mini", "weight": 0.6},
        {"role": "qalgo", "model": "qwen3-coder", "weight": 1.0}
    ],
    consensus_threshold=quality_thresholds["swarm_consensus_min"]
)

executor = TeamExecutor(config=config)

# Each agent reviews the implementation
review_prompt = f"""
TASK: Review the following implementation for {improvement_goal}

CODE CHANGES:
{get_diff(target_files)}

TESTS:
{get_test_content(test_file)}

Your review must assess:
1. Correctness (does it implement what was requested?)
2. HIHO Coherence (does it maintain 0.5 stability?)
3. Test coverage (are edge cases handled?)
4. Integration (does it align with existing patterns?)
5. Physics validity (if applicable, does it match Smith's 12 parameters?)

Provide: APPROVE | REJECT | REVISE_AND_RESUBMIT
Rationale: <explanation>
"""

reviews = await executor.execute_swarm(
    prompt=review_prompt,
    task_context={"improvement_goal": improvement_goal}
)

# Calculate consensus
consensus = calculate_consensus(reviews, threshold=config.consensus_threshold)

if consensus.decision == "APPROVE":
    logger.info(f"Swarm consensus: APPROVED ({consensus.score:.2f})")
elif consensus.decision == "REVISE":
    logger.warning(f"Swarm requests revision: {consensus.issues}")
    # Return to Phase 3 with revision guidance
else:
    logger.error(f"Swarm rejection: {consensus.rationale}")
    # Escalate to human review
```

**Success Criteria**:
- Consensus ≥ quality_thresholds["swarm_consensus_min"]
- No blocking issues raised by specialists
- At least 3/5 agents approve

**Outputs**:
- Consensus decision (APPROVE/REJECT/REVISE)
- Aggregated review feedback
- Revision guidance if needed

### Phase 5: Ouroboros Self-Healing (Anomaly Detection)

**Components**: HealerAgent, AnomalyDetector, DegradationDetector

```python
from cohezion.ouroboros.healer import HealerAgent
from cohezion.compound.degradation_detector import DegradationDetector

detector = DegradationDetector()
healer = HealerAgent(model_name="qwen3-coder")

# Check for degradation after changes
anomaly_report = detector.detect_anomalies(
    before_state=journey_tracker.get_snapshot(before_timestamp),
    after_state=journey_tracker.get_snapshot(after_timestamp),
    thresholds={"coherence_drop_max": 0.1, "thermal_max": 0.8}
)

if anomaly_report["anomalies_detected"]:
    logger.warning(f"Anomalies detected: {anomaly_report}")

    # Synthesize patch
    patch = await healer.synthesize_patch(anomaly_report)

    # Apply patch (with human approval for critical changes)
    if anomaly_report["severity"] == "critical":
        logger.error("Critical anomaly - human review required")
        escalate_to_human(patch)
    else:
        apply_patch(patch)
        logger.info(f"Self-healing patch applied: {patch}")
```

**Success Criteria**:
- No critical anomalies detected
- Coherence remains ≥ 0.5 (HIHO stability)
- Thermal load < 0.8

**Outputs**:
- Anomaly report
- Self-healing patches (if needed)
- Updated system state

### Phase 6: Retrospection & Pattern Extraction (Vault Logging)

**Components**: RetrospectionEngine, VaultLogger, CompoundExecutor

```python
from cohezion.compound.retrospection_engine import RetrospectionEngine

retro = RetrospectionEngine()

# Extract learnings from execution
learnings = retro.extract_learnings(
    execution_trajectory=journey_tracker.get_journey(session_id),
    metrics=metrics_collector.get_session_metrics(),
    outcomes={"tests_passing": True, "coverage": final_coverage}
)

# Log to vault
for learning in learnings["key_insights"]:
    if learning["type"] == "decision":
        vault_log_decision(
            project="cohezion",
            title=learning["title"],
            context=learning["context"],
            decision=learning["decision"],
            rationale=learning["rationale"]
        )
    elif learning["type"] == "pattern":
        vault_extract_pattern(
            source_path=target_files[0],
            pattern_name=learning["pattern_name"],
            description=learning["description"],
            code_example=learning["code_example"],
            domain="meta-engineering"
        )

# Log experiment for future reference
vault_log_experiment(
    project="cohezion",
    hypothesis=f"Improve Cohezion via compound loop: {improvement_goal}",
    method="TDD + Adversarial Review + Ouroboros + Mycelium",
    result=f"Coverage: {final_coverage}%, Consensus: {consensus.score:.2f}",
    learnings=learnings["summary"]
)
```

**Success Criteria**:
- At least 3 learnings extracted
- All decisions logged to vault
- Reusable patterns identified

**Outputs**:
- Vault decision logs
- Vault experiment logs
- Extracted patterns for future reuse

### Phase 7: Skill Refinement (Self-Improvement Loop Closure)

**Components**: SkillRefiner, SkillConsensusVoter

```python
from cohezion.compound.skill_refiner import SkillRefiner

refiner = SkillRefiner()

# Analyze this skill's performance
skill_metrics = {
    "success_rate": 1.0 if consensus.decision == "APPROVE" else 0.0,
    "test_coverage": final_coverage,
    "coherence_maintained": journey_tracker.get_coherence() >= 0.5,
    "token_efficiency": metrics_collector.get_token_metrics()["efficiency"]
}

# Propose refinements
refinements = refiner.propose_refinements(
    skill_name="COMPOUND_SELF_IMPROVEMENT_PRIME",
    metrics=skill_metrics,
    execution_logs=journey_tracker.get_journey(session_id)
)

# Multi-agent validation of refinements
if refinements["proposed_changes"]:
    consensus = await SkillConsensusVoter().vote(
        skill_name="COMPOUND_SELF_IMPROVEMENT_PRIME",
        proposed_changes=refinements["proposed_changes"]
    )

    if consensus >= 0.7:
        # Update this skill definition
        apply_skill_refinements(
            "COMPOUND_SELF_IMPROVEMENT_PRIME",
            refinements["proposed_changes"]
        )
        logger.info("Skill refined based on execution outcomes")
```

**Success Criteria**:
- Skill metrics analyzed
- Refinement proposals validated by consensus
- Skill definition updated if improvements identified

**Outputs**:
- Updated COMPOUND_SELF_IMPROVEMENT_PRIME.md (self-modifying)
- Skill registry updated
- Version incremented

## Success Metrics

| Metric | Threshold | Measurement Method |
|--------|-----------|-------------------|
| Test Coverage | ≥ 95% | `pytest --cov` on target files |
| Swarm Consensus | ≥ 0.7 | Weighted average of specialist approvals |
| HIHO Coherence | ≥ 0.5 | `journey_tracker.get_coherence()` |
| Regression Count | 0 | Compare test suite before/after |
| Vault Learnings | ≥ 3 | Count of decisions + patterns logged |
| Token Efficiency | <10K tokens/feature | Total tokens / features implemented |
| Iteration Count | ≤ 3 | Refinement cycles before success |

## Failure Modes & Mitigations

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| Low coherence (<0.5) | RequestAlignmentAnalyzer | Decompose into smaller tasks |
| Swarm deadlock (no consensus) | TeamExecutor timeout | Human arbitration + context refinement |
| Test failures persist | CoverageLoop max_iterations | Escalate to manual debugging |
| Coherence collapse | DegradationDetector | Ouroboros self-healing + rollback |
| Token budget exceeded | GlobalMetricsAggregator | Pause, optimize prompt, resume |
| Critical anomaly | HealerAgent severity check | Human review before patch application |

## Example Invocation

```python
from cohezion.compound.executor import CompoundExecutor
from cohezion.skills import load_skill

# Load this skill
skill = load_skill("COMPOUND_SELF_IMPROVEMENT_PRIME")

# Configure parameters
params = {
    "improvement_goal": "Add precipitation_gate() to AxiomaticState in engine.py",
    "target_files": ["src/cohezion/universe/engine.py"],
    "context_files": ["src/cohezion/skills/hiho_reality_sim.md"],
    "quality_thresholds": {
        "test_coverage_min": 95.0,
        "coherence_threshold": 0.5,
        "swarm_consensus_min": 0.7
    },
    "enable_tdd": True,
    "enable_adversarial_review": True,
    "enable_ouroboros": True,
    "max_iterations": 3
}

# Execute compound loop
executor = CompoundExecutor(mcp_client=mcp_client)
result = await executor.execute_skill(
    skill_name="COMPOUND_SELF_IMPROVEMENT_PRIME",
    params=params
)

# Check result
if result.success:
    print(f"Improvement complete: {result.output}")
    print(f"Coverage: {result.metrics['coverage']}%")
    print(f"Vault logs: {result.vault_experiment_path}")
else:
    print(f"Improvement failed: {result.output}")
    print(f"Escalation needed: {result.metrics['escalation_reason']}")
```

## Historical Context

**Created**: 2026-03-21 during portfolio transformation session
**Motivation**: User requested: "We need to continue with compound engineering solutions delivered with TDD and adversarial code review and automated repository management and self-healing code with Ouroboros and the mycelium as well as teams of specialist agents (save the definitions for reuse)."

**Key Insight**: This skill encodes Cohezion's self-referential improvement protocol - the system reads its own instructions to improve itself, achieving HIHO stability (0.5 coherence) by being simultaneously "code being improved" and "improvement mechanism."

## Related Skills

- `TDD_PRIME.md` - Test-Driven Development methodology
- `ADVERSARIAL_CODE_REVIEW_PRIME.md` - Multi-agent validation patterns
- `VAULT_KNOWLEDGE_MANAGEMENT_PRIME.md` - Persistent learning across sessions
- `HIHO_REALITY_SIM_PRIME.md` - Smith's precipitation physics (context for coherence checks)

## Version History

- **1.0.0** (2026-03-21): Initial creation with 7-phase protocol (Alignment → Vault → TDD → Review → Healing → Retrospection → Refinement)
