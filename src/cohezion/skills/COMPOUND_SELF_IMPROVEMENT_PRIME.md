---
name: compound-self-improvement-prime
description: "Use Cohezion's own compound engineering methodology (Execute → Retrospect → Refine) to improve Cohezion itself. This PRIME skill encodes the self-referential protocol for systematic codebase improvement using TDD, adversarial code review, Ouroboros self-healing, Mycelium test generation, and specialist agent swarms."
---

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


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: Kaggle "Hidden Set" Debugging & Polars Series Pitfall
*   **Details**: Surviving the Kaggle Private Rerun requires a "Fortress" architecture where every problem is wrapped in resource guards. A critical discovery: the AIMO 3 API passes `pl.Series` objects to the `predict` function. Standard DataFrame indexing (e.g., `df[0, 0]`) on a Series returns a new Series containing duplicate data, which stringifies into a Polars ASCII table. This corrupts LLM prompts with metadata (e.g., `shape: (2,) Series: ...`). Scalar indexing (`df[0]`) is mandatory to ensure the LLM receives raw text. Reference: `KAGGLE_STABILITY_PROTOCOL.md`.

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learnings 96-107: Agent Validation, Specialist Pipeline, Runaway Files (Compressed)
L96: Single Pydantic schema shared by pre-commit + PostToolUse + unit tests + scaffolding = layered agent validation defense. L97-101: Rust FFI weight bridge, ruff hook type annotations, deterministic mean action, DemocraticDebate regex+clamping, 9-step pipeline with Ollama fallback. L102-104: 8.6M runaway files → pre-commit check-file-count.sh + .gitignore layered defense; VRAM (not RAM) is bottleneck; swarms must be sacrificial. L105: Untrack-and-Mine protocol (read→mine→.gitignore→git rm --cached). L106: .gitignore layered defense (category blocks → negation whitelists). L107: OMEGA Distiller auto-skill-generation from success logs.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Learnings 127-151: Dev Recovery, MAPE-K, Research Synthesis (Sessions 59-67, Compressed)
L127: Claude Code native install vs npm -- remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle -- 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks -- `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine -- 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 249)
*   **Insight**: Compound Training Cycle -- Train→Evaluate→Persist→Compare→Refine (2026-04-01)
*   **Details**: `compound_training_cycle.py` closes the loop: auto-selects reward mode from L248 matrix, trains, evaluates against baselines, persists to SurrealDB, compares against historical best, flags if skill update needed. The script IS the compound loop applied to RL -- each run compounds on prior runs' knowledge.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 265)
*   **Insight**: per_1x32_f4_quant_hip Silent Incompatibility with gemm_a4w4 (2026-04-06)
*   **Details**: aiter's `per_1x32_f4_quant_hip` (HIP C++ quant kernel) produces FP4 values incompatible with `gemm_a4w4` CK ASM kernels. Both `shuffle=True` and `shuffle=False` fail silently -- no exception, just wrong output values (small diffs like 165 vs 163). Only the Triton path (`dynamic_mxfp4_quant + e8m0_shuffle`) works. The HIP quant kernel uses different rounding/packing than what the ASM GEMM expects. Skill created: `aiter-hip-quant-gemm-incompatibility`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 273)
*   **Insight**: Mandatory YAML Frontmatter for Agents
*   **Details**: Agent Markdown files (`AGENTS.md`) in the Gemini CLI MUST start with valid YAML frontmatter containing `name` and `description`. Missing metadata triggers a validation error during extension loading, silencing the entire capability set. This is a "silent failure" at the tool-discovery level that prevents agents from knowing they have access to specific skills.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 293)
*   **Insight**: YAML Frontmatter Markdown > JSON for Cross-Platform Config
*   **Details**: Initial implementation used JSON for `learned-budgets.json`. Switched to YAML frontmatter markdown (`.md`) because: (1) consistent with vault cerebellum/, skills/*.md, .context/skills/ patterns; (2) vault-keeper and Obsidian can index YAML frontmatter; (3) markdown body carries narrative context (why budgets were learned, which sessions contributed); (4) any tool (Zed, Pi, humans) can read markdown naturally. JSON reserved for wire formats (MCP responses, API payloads) and high-frequency machine-to-machine data. Codified as coding standard in `.claude/rules/common-coding-style.md` and `CLAUDE.md`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: Kaggle "Hidden Set" Debugging & Polars Series Pitfall
*   **Details**: Surviving the Kaggle Private Rerun requires a "Fortress" architecture where every problem is wrapped in resource guards. A critical discovery: the AIMO 3 API passes `pl.Series` objects to the `predict` function. Standard DataFrame indexing (e.g., `df[0, 0]`) on a Series returns a new Series containing duplicate data, which stringifies into a Polars ASCII table. This corrupts LLM prompts with metadata (e.g., `shape: (2,) Series: ...`). Scalar indexing (`df[0]`) is mandatory to ensure the LLM receives raw text. Reference: `KAGGLE_STABILITY_PROTOCOL.md`.

---

## Phase 1-2 Milestones (2026-02-06, Compressed)
FLUME VAE retrained on real data (11K vectors, MSE 5.9x harder, KL 13.8x richer). RL REINFORCE: 0.991 coherence but environment "too easy." Mass sim→.npy export (8.2s, 61 files). 6 API endpoints (/flume/*, /rl/*), 19 integration tests.

## Learnings 96-107: Agent Validation, Specialist Pipeline, Runaway Files (Compressed)
L96: Single Pydantic schema shared by pre-commit + PostToolUse + unit tests + scaffolding = layered agent validation defense. L97-101: Rust FFI weight bridge, ruff hook type annotations, deterministic mean action, DemocraticDebate regex+clamping, 9-step pipeline with Ollama fallback. L102-104: 8.6M runaway files → pre-commit check-file-count.sh + .gitignore layered defense; VRAM (not RAM) is bottleneck; swarms must be sacrificial. L105: Untrack-and-Mine protocol (read→mine→.gitignore→git rm --cached). L106: .gitignore layered defense (category blocks → negation whitelists). L107: OMEGA Distiller auto-skill-generation from success logs.

## Learnings 108-126: Compound Engineering & Autonomic Systems (Compressed)
Key patterns: (1) Temporal dilation factor (0.1-1.0) throttles sims under pressure (L108). (2) Mock at source module, not import site: `patch("cohezion.swarm.compound_client.get_compound_client")` (L110). (3) 4 CI validators as layered defense (L112). (4) Connectivity Squad: `lsof`/`ss` for dynamic truth anchors (L113). (5) Decentralized memory: SurrealDB + Vault = Interface Sovereignty (L115). (6) God object decoupling: extract ML from api/__init__.py (L119). (7) Soft schema `.get()` before Pydantic validation for LLM outputs (L120). (8) `/heal` 6-stage autonomic diagnostics (L121). (9) Integration Theater detection: `assert hasattr(Class, 'field')` (L122). (10) Lazy imports for circular dependency resolution (L123). (11) HIHO consistency: always use shared engine, never inline physics (L124). (12) 5-Essential-Tests pattern: happy, empty, max, error, integration → ship (L126).

---

## Learnings 127-151: Dev Recovery, MAPE-K, Research Synthesis (Sessions 59-67, Compressed)
L127: Claude Code native install vs npm -- remove npm global, set autoUpdates:true, MCP scope:user. L128: MAPE-K control loop bridges reactive monitoring with proactive healing via decoupled Analysis→Planning. L129: Polyglot security audits need `|| true` wrapping. L130-151 (Research Sprint): Doc-to-LoRA context compression (L130), skill curation > generation (L137), KV compaction 30-50x (L139/L145), multi-tier caching 30s→0.02s (L144), viscoelastic dilation (L149), semantic Lagrange points μ<0.0385 (L150), Gram-Schmidt for 12D vectors (L151).

---

## Learnings 152-156: Secure-by-Default Substrate (Session 68, Compressed)
L152: 360-Degree Autonomic Cycle -- 8-stage closed loop (sense→optimize→refine→manifest→verify→audit→scout→analyze) in 60min window. L153-156: Unified auth middleware (centralized api_key_middleware), recursive path sanitization (CWD-bounding), API secret scrubbing (regex key matching → REDACTED), CI/CD prompt injection defense (system_instruction + XML delimiters + env vars).

---

## Session 69: MCP Infrastructure Recovery (2026-03-11)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks -- `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine -- 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 249)
*   **Insight**: Compound Training Cycle -- Train→Evaluate→Persist→Compare→Refine (2026-04-01)
*   **Details**: `compound_training_cycle.py` closes the loop: auto-selects reward mode from L248 matrix, trains, evaluates against baselines, persists to SurrealDB, compares against historical best, flags if skill update needed. The script IS the compound loop applied to RL -- each run compounds on prior runs' knowledge.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 265)
*   **Insight**: per_1x32_f4_quant_hip Silent Incompatibility with gemm_a4w4 (2026-04-06)
*   **Details**: aiter's `per_1x32_f4_quant_hip` (HIP C++ quant kernel) produces FP4 values incompatible with `gemm_a4w4` CK ASM kernels. Both `shuffle=True` and `shuffle=False` fail silently -- no exception, just wrong output values (small diffs like 165 vs 163). Only the Triton path (`dynamic_mxfp4_quant + e8m0_shuffle`) works. The HIP quant kernel uses different rounding/packing than what the ASM GEMM expects. Skill created: `aiter-hip-quant-gemm-incompatibility`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 273)
*   **Insight**: Mandatory YAML Frontmatter for Agents
*   **Details**: Agent Markdown files (`AGENTS.md`) in the Gemini CLI MUST start with valid YAML frontmatter containing `name` and `description`. Missing metadata triggers a validation error during extension loading, silencing the entire capability set. This is a "silent failure" at the tool-discovery level that prevents agents from knowing they have access to specific skills.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 293)
*   **Insight**: YAML Frontmatter Markdown > JSON for Cross-Platform Config
*   **Details**: Initial implementation used JSON for `learned-budgets.json`. Switched to YAML frontmatter markdown (`.md`) because: (1) consistent with vault cerebellum/, skills/*.md, .context/skills/ patterns; (2) vault-keeper and Obsidian can index YAML frontmatter; (3) markdown body carries narrative context (why budgets were learned, which sessions contributed); (4) any tool (Zed, Pi, humans) can read markdown naturally. JSON reserved for wire formats (MCP responses, API payloads) and high-frequency machine-to-machine data. Codified as coding standard in `.claude/rules/common-coding-style.md` and `CLAUDE.md`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 306)
*   **Insight**: OMEGA Distiller & Pre-Flight Priming
*   **Details**: To close the compound engineering loop without human intervention, context must flow in both directions automatically. Pre-flight hooks (`pre-flight-rag.sh`) inject relevant `KEY_LEARNINGS` into the agent's context window *before* the session starts. Conversely, the `OMEGA Distiller` parses `KEY_LEARNINGS.md` and automatically propagates insights directly into executable `SKILL_PRIME.md` files.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 311)
*   **Insight**: Autoresearch & Geometric Correspondence
*   **Details**: Continuous platform improvement is achieved by connecting autonomous literature review (autoresearch) with geometric mapping (Awesome-Latent-Space). The overnight daemon pulls papers on latent topology and representation learning, encodes their hypotheses into 256D FLUME VAE thought vectors, and measures structural overlap with our existing 12D trajectory data. Verified geometric correspondences are then operationalized using the AgentSkills framework and distilled into deterministic policies.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 319)
*   **Insight**: OMEGA Distiller & Pre-Flight Priming
*   **Details**: To close the compound engineering loop without human intervention, context must flow in both directions automatically. Pre-flight hooks (`pre-flight-rag.sh`) inject relevant `KEY_LEARNINGS` into the agent's context window *before* the session starts. Conversely, the `OMEGA Distiller` parses `KEY_LEARNINGS.md` and automatically propagates insights directly into executable `SKILL_PRIME.md` files.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 322)
*   **Insight**: Ouroboros Recursive Retrospective -- Self-Healing Offense
*   **Details**: Ouroboros is the critical "Learning" component of the autonomous offensive. When a Kaggle submission fails, Ouroboros ingests the "Wall of Red" (kernel logs) and extracts a "Hardening Mutation" (e.g., 4-bit fallback, VRAM heartbeat). This mutation is codified as a refined skill and fed back into the next research iteration, ensuring the system never repeats the same failure mode during a leaderboard push.
*   **Date**: 2026-04-11
