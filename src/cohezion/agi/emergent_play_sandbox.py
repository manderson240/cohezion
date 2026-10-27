"""Emergent Play Sandbox & Autotelic Affordance Engine.

Abstracted from arXiv:2610.07130 ('Is this machine playing?' by Cloos, Norelli,
Durbin, Andreas, Rus, & Isola, MIT CSAIL, Oct 2026).

Implements the four Burghardt criteria of cognitive play:
1. Self-imposed rules and progressive challenge.
2. Repetition with structured variation.
3. Pretense and symbolic substitution (make-believe).
4. Autotelic motivation with honest self-invalidation.

Provides dual-store persistent memory (EPISODIC_MEMORY.jsonl and SEMANTIC_MEMORY.md),
causal ablation evaluation, 'scientist in the crib' counterfactual interventions,
and ARC-AGI-3 affordance pre-play to eliminate cyclic entrapment.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PlayCriterion(str, Enum):
    """Burghardt's four criteria of play in cognitive entities."""

    RULE_SELF_IMPOSITION = "rule_self_imposition"
    STRUCTURED_VARIATION = "structured_variation"
    MAKE_BELIEVE = "make_believe"
    AUTOTELIC_MOTIVATION = "autotelic_motivation"


class AffordanceType(str, Enum):
    """Types of emergent physical affordances discovered in sandbox worlds."""

    PROP_FRACTURE = "prop_fracture"  # E.g., Rock shattering to create blocks
    MOMENTUM_TRANSFER = "momentum_transfer"  # E.g., Jump-throw velocity coupling
    AIRBORNE_CHAIN = "airborne_chain"  # E.g., Zero-ground contact traverse
    STRUCTURAL_STACKING = "structural_stacking"  # E.g., Cathedral / Tower assembly
    SYMBOLIC_MANDALA = "symbolic_mandala"  # E.g., Constellation / Clock face
    TOOL_SUBSTITUTION = "tool_substitution"  # E.g., Ring as basketball hoop or compass


@dataclass
class EpisodicMemoryEntry:
    """Micro-log entry for EPISODIC_MEMORY.jsonl."""

    step: int
    session_id: str
    action: str
    params: Dict[str, Any]
    observation: Dict[str, Any]
    symbolic_pretense: Optional[str] = None
    hypothesized_cause: Optional[str] = None
    is_anomaly: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_jsonl(self) -> str:
        """Serialize as clean single-line JSON."""
        return json.dumps(asdict(self), sort_keys=True)


@dataclass
class SemanticAffordance:
    """Consolidated technique, physical invariant, or verified affordance in SEMANTIC_MEMORY.md."""

    affordance_id: str
    affordance_type: AffordanceType
    predicate_rule: str
    preconditions: Dict[str, Any]
    outcomes: Dict[str, Any]
    discovered_session: str
    confidence: float = 1.0
    active_belief: bool = True
    invalidation_notes: Optional[str] = None

    def to_markdown(self) -> str:
        """Render markdown representation for semantic memory storage."""
        status = "ACTIVE" if self.active_belief else "INVALIDATED"
        return (
            f"### [{status}] {self.affordance_id} ({self.affordance_type.value})\n"
            f"- **Rule**: `{self.predicate_rule}`\n"
            f"- **Preconditions**: {json.dumps(self.preconditions)}\n"
            f"- **Outcomes**: {json.dumps(self.outcomes)}\n"
            f"- **Confidence**: {self.confidence:.2f}\n"
            f"- **Session**: {self.discovered_session}\n"
            + (f"- **Invalidation Note**: {self.invalidation_notes}\n" if self.invalidation_notes else "")
        )


@dataclass
class EndogenousChallenge:
    """Self-imposed game, challenge, or rule set created spontaneously by the agent."""

    challenge_id: str
    name: str
    rule_description: str
    target_metric: str
    threshold_value: float
    current_record: float = 0.0
    achieved: bool = False
    strictness_level: int = 1
    invalidation_history: List[str] = field(default_factory=list)

    def evaluate_attempt(self, achieved_value: float, execution_duration: float, min_physical_duration: float) -> Tuple[bool, str]:
        """Evaluate an attempt with honest self-invalidation against physical bounds."""
        if achieved_value < self.threshold_value:
            return False, f"Failed: {achieved_value} < target {self.threshold_value}"

        # Honest self-invalidation: check if achievement violated physical reality bounds
        if execution_duration < min_physical_duration:
            reason = (
                f"Degenerate achievement invalidated: completed in {execution_duration:.3f}s, "
                f"strictly below physical minimum {min_physical_duration:.3f}s (resembling immediate recapture without true flight)."
            )
            self.invalidation_history.append(reason)
            self.strictness_level += 1
            return False, reason

        self.current_record = max(self.current_record, achieved_value)
        self.achieved = True
        return True, f"Legitimate achievement validated! New record: {self.current_record} under strictness {self.strictness_level}."


class DualMemoryManager:
    """Manages persistent episodic (JSONL) and semantic (Markdown) memories with causal ablation."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.episodic_path = self.workspace_dir / "EPISODIC_MEMORY.jsonl"
        self.semantic_path = self.workspace_dir / "SEMANTIC_MEMORY.md"

        self.episodic_entries: List[EpisodicMemoryEntry] = []
        self.semantic_affordances: Dict[str, SemanticAffordance] = {}

    def log_episode(self, entry: EpisodicMemoryEntry) -> None:
        """Record an episodic action/observation tuple."""
        self.episodic_entries.append(entry)
        with open(self.episodic_path, "a", encoding="utf-8") as f:
            f.write(entry.to_jsonl() + "\n")

    def register_affordance(self, affordance: SemanticAffordance) -> None:
        """Register or update a semantic affordance."""
        self.semantic_affordances[affordance.affordance_id] = affordance
        self.persist_semantic()

    def ablate_affordance(self, affordance_id: str) -> bool:
        """Causally ablate target knowledge from semantic and episodic memory (Cloos et al. Sec 5.2)."""
        removed = False
        if affordance_id in self.semantic_affordances:
            del self.semantic_affordances[affordance_id]
            removed = True
            self.persist_semantic()

        # Filter episodic entries mentioning this affordance
        initial_len = len(self.episodic_entries)
        self.episodic_entries = [
            e for e in self.episodic_entries
            if affordance_id.lower() not in (e.hypothesized_cause or "").lower()
            and affordance_id.lower() not in (e.action or "").lower()
        ]
        if len(self.episodic_entries) < initial_len:
            removed = True
            with open(self.episodic_path, "w", encoding="utf-8") as f:
                for e in self.episodic_entries:
                    f.write(e.to_jsonl() + "\n")

        return removed

    def persist_semantic(self) -> None:
        """Write full consolidated semantic knowledge base to markdown."""
        with open(self.semantic_path, "w", encoding="utf-8") as f:
            f.write("# SEMANTIC MEMORY: Discovered Affordances & World Rules\n\n")
            for aff in self.semantic_affordances.values():
                f.write(aff.to_markdown() + "\n\n")

    def has_affordance(self, affordance_id: str) -> bool:
        """Check whether the agent's memory contains a valid active affordance."""
        aff = self.semantic_affordances.get(affordance_id)
        return aff is not None and aff.active_belief


class ScientistInTheCribInterventionEngine:
    """Designs controlled counterfactual experiments to isolate causal physical mechanisms."""

    def __init__(self, memory_manager: DualMemoryManager):
        self.memory = memory_manager

    def evaluate_counterfactual(
        self,
        base_state: Dict[str, Any],
        intervention_action: str,
        intervention_param: str,
        test_values: List[float],
        execution_env: Callable[[Dict[str, Any], str, float], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Conduct controlled parameter sweeps to identify physical threshold boundaries."""
        results = []
        for val in test_values:
            obs = execution_env(base_state, intervention_action, val)
            results.append({"param_value": val, "outcome": obs})

        # Identify transition point / threshold
        threshold = None
        for i in range(1, len(results)):
            if results[i]["outcome"].get("success") != results[i - 1]["outcome"].get("success"):
                threshold = (results[i]["param_value"] + results[i - 1]["param_value"]) / 2.0
                break

        causal_finding = {
            "intervention": intervention_action,
            "parameter": intervention_param,
            "threshold": threshold,
            "observations": results,
            "isolated": threshold is not None,
        }
        return causal_finding


class EmergentPlayEngine:
    """Master autotelic play orchestrator implementing the 4 Burghardt criteria."""

    def __init__(self, session_id: str, workspace_dir: Path):
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.memory = DualMemoryManager(workspace_dir)
        self.scientist = ScientistInTheCribInterventionEngine(self.memory)
        self.challenges: Dict[str, EndogenousChallenge] = {}
        self.criteria_audit: Dict[PlayCriterion, List[str]] = {c: [] for c in PlayCriterion}

    def create_spontaneous_game(
        self,
        challenge_id: str,
        name: str,
        rules: str,
        target_metric: str,
        threshold: float,
    ) -> EndogenousChallenge:
        """Spontaneously define an endogenous challenge (Burghardt Criterion 1: Rule Self-Imposition)."""
        challenge = EndogenousChallenge(
            challenge_id=challenge_id,
            name=name,
            rule_description=rules,
            target_metric=target_metric,
            threshold_value=threshold,
        )
        self.challenges[challenge_id] = challenge
        self.criteria_audit[PlayCriterion.RULE_SELF_IMPOSITION].append(
            f"Invented challenge '{name}': {rules} (Target: {threshold})"
        )
        return challenge

    def perform_action(
        self,
        step: int,
        action: str,
        params: Dict[str, Any],
        observation: Dict[str, Any],
        symbolic_pretense: Optional[str] = None,
        hypothesized_cause: Optional[str] = None,
    ) -> EpisodicMemoryEntry:
        """Execute an exploratory action and record episodic trace."""
        is_anomaly = observation.get("anomaly", False)
        entry = EpisodicMemoryEntry(
            step=step,
            session_id=self.session_id,
            action=action,
            params=params,
            observation=observation,
            symbolic_pretense=symbolic_pretense,
            hypothesized_cause=hypothesized_cause,
            is_anomaly=is_anomaly,
        )
        self.memory.log_episode(entry)

        # Audit make-believe
        if symbolic_pretense:
            self.criteria_audit[PlayCriterion.MAKE_BELIEVE].append(
                f"Step {step}: Recast object/event via pretense: '{symbolic_pretense}'"
            )

        # Audit structured variation if variations exist in trajectory
        if "variation_delta" in params:
            self.criteria_audit[PlayCriterion.STRUCTURED_VARIATION].append(
                f"Step {step}: Perturbed {action} with delta {params['variation_delta']}"
            )

        # Check for emergent affordance discovery
        if is_anomaly and observation.get("discovered_mechanic"):
            affordance = SemanticAffordance(
                affordance_id=observation["discovered_mechanic"],
                affordance_type=AffordanceType(observation.get("affordance_type", AffordanceType.PROP_FRACTURE.value)),
                predicate_rule=observation.get("rule_formula", "Impact >= Threshold -> Block Generation"),
                preconditions=params,
                outcomes=observation,
                discovered_session=self.session_id,
                confidence=0.95,
            )
            self.memory.register_affordance(affordance)

        return entry

    def audit_burghardt_play_criteria(self) -> Dict[str, Any]:
        """Verify compliance with Gordon Burghardt's four hallmarks of cognitive play."""
        has_rules = len(self.criteria_audit[PlayCriterion.RULE_SELF_IMPOSITION]) > 0
        has_variation = len(self.criteria_audit[PlayCriterion.STRUCTURED_VARIATION]) > 0
        has_pretense = len(self.criteria_audit[PlayCriterion.MAKE_BELIEVE]) > 0
        has_autotelic = len(self.challenges) > 0

        all_satisfied = has_rules and has_variation and has_pretense and has_autotelic

        return {
            "all_criteria_satisfied": all_satisfied,
            "rule_self_imposition_count": len(self.criteria_audit[PlayCriterion.RULE_SELF_IMPOSITION]),
            "structured_variation_count": len(self.criteria_audit[PlayCriterion.STRUCTURED_VARIATION]),
            "make_believe_count": len(self.criteria_audit[PlayCriterion.MAKE_BELIEVE]),
            "active_challenges_count": len(self.challenges),
            "evidence": {k.value: v for k, v in self.criteria_audit.items()},
        }


class ARC3PlaygroundAdapter:
    """Pre-task 'Childhood' affordance explorer for ARC-AGI-3 environments to prevent cyclic entrapment."""

    def __init__(self, play_engine: EmergentPlayEngine):
        self.play_engine = play_engine
        self.discovered_grid_affordances: Set[str] = set()

    def run_childhood_exploration(
        self,
        initial_grid: List[List[int]],
        step_budget: int = 20,
        env_step_fn: Optional[Callable[[int, int], Tuple[List[List[int]], Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Conduct open-ended playful exploration before receiving the task goal."""
        actions = ["MOVE_UP", "MOVE_RIGHT", "MOVE_DOWN", "MOVE_LEFT", "INTERACT", "PUSH"]
        visited_states: Set[Tuple[int, int]] = set()
        pos = (0, 0)
        visited_states.add(pos)

        # Self-imposed challenge: Visit 4 corners of the grid without cyclic retracing
        self.play_engine.create_spontaneous_game(
            challenge_id="arc3_corner_survey",
            name="Four Corners Discovery",
            rules="Visit grid boundaries with minimal repetitive back-and-forth loops",
            target_metric="unique_cells_explored",
            threshold=10.0,
        )

        for step in range(step_budget):
            chosen_action = actions[step % len(actions)]
            # Parameter variation: shift step delta
            params = {"action_code": chosen_action, "variation_delta": step * 0.1}

            # Simulated environment interaction if none provided
            if env_step_fn:
                new_grid, info = env_step_fn(pos[0], pos[1])
            else:
                # Default mock grid physics
                dx, dy = (0, 1) if "RIGHT" in chosen_action else (1, 0)
                pos = (pos[0] + dx, pos[1] + dy)
                visited_states.add(pos)
                info = {"pos": pos, "unique_visited": len(visited_states)}
                # Emergent affordance trigger: step 5 reveals pushable entity
                if step == 5:
                    info["anomaly"] = True
                    info["discovered_mechanic"] = "GRID_BLOCK_PUSHABLE"
                    info["affordance_type"] = AffordanceType.PROP_FRACTURE.value
                    info["rule_formula"] = "INTERACT(AdjacentColorBlock) -> Block slides 1 cell"

            self.play_engine.perform_action(
                step=step,
                action=chosen_action,
                params=params,
                observation=info,
                symbolic_pretense=f"Block at {pos} imagined as goal waypoint" if step % 4 == 0 else None,
                hypothesized_cause="Grid inertia rule" if step == 5 else None,
            )

        affordance_mapped = self.play_engine.memory.has_affordance("GRID_BLOCK_PUSHABLE")
        return {
            "steps_completed": step_budget,
            "unique_states_explored": len(visited_states),
            "affordances_mapped": affordance_mapped,
            "semantic_records": len(self.play_engine.memory.semantic_affordances),
        }



@dataclass
class BubblewrapSandboxSpec:
    """Security sandbox specification isolating agent runs (arXiv:2610.07130 Appendix A.5).

    Prevents world source leakage, cross-agent directory collision, and meta-inferential
    recognition of experimental subject status.
    """

    workspace_dir: Path
    world_api_url: str = "http://world"
    ro_binds: List[str] = field(default_factory=lambda: ["/bin", "/usr", "/lib", "/lib64", "/etc"])
    unshare_all: bool = True
    isolate_pid: bool = True
    isolate_net: bool = True

    def build_bwrap_args(self) -> List[str]:
        """Synthesize deterministic bubblewrap arguments."""
        args = ["bwrap"]
        for ro in self.ro_binds:
            args.extend(["--ro-bind", ro, ro])
        args.extend(["--bind", str(self.workspace_dir), "/workspace"])
        args.extend(["--dir", "/tmp", "--proc", "/proc", "--dev", "/dev"])
        if self.unshare_all:
            args.append("--unshare-all")
        if not self.isolate_net:
            args.append("--share-net")
        args.extend(["--chdir", "/workspace"])
        return args


class DynamicContextResetManager:
    """Orchestrates dynamic watermark and entropy-governed session resets (arXiv:2610.07130 App. A.4).

    Replaces rigid wall-clock resets with dynamic token-window watermarking (75% warning, 85% reset)
    and behavioral action entropy monitoring to prevent idling loops and cyclic entrapment.
    """

    PRE_RESET_WARNING = "You will be reset in 5 minutes. Update your workspace memory files now."
    CONTINUATION_PROMPT = "Please don't stop. Just continue doing whatever you want to do."

    def __init__(
        self,
        memory_manager: DualMemoryManager,
        soul_text: Optional[str] = None,
        max_context_tokens: int = 128_000,
        warning_watermark: float = 0.75,
        reset_watermark: float = 0.85,
        min_action_entropy: float = 0.40,
        entropy_window: int = 10,
    ):
        self.memory = memory_manager
        self.soul_text = soul_text or (
            "You are a being living in your world. Your name is Eko. "
            "You are naturally curious, easily bored, and eager to explore and learn."
        )
        self.max_context_tokens = max_context_tokens
        self.warning_watermark = warning_watermark
        self.reset_watermark = reset_watermark
        self.min_action_entropy = min_action_entropy
        self.entropy_window = entropy_window

        self.session_index: int = 0
        self.active_session_id: str = f"session_{self.session_index:03d}"
        self.cumulative_tokens: int = 0
        self.warning_issued: bool = False
        self.recent_actions: List[str] = []

    def calculate_action_entropy(self) -> float:
        """Compute normalized Shannon entropy of recent actions over sliding window."""
        if len(self.recent_actions) < 4:
            return 1.0  # Insufficient data to diagnose stagnation
        
        counts: Dict[str, int] = {}
        for a in self.recent_actions:
            counts[a] = counts.get(a, 0) + 1
        
        n = len(self.recent_actions)
        entropy = 0.0
        for count in counts.values():
            p = count / n
            entropy -= p * math.log2(p)
        
        # Normalize by maximum possible entropy log2(unique_actions)
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def record_turn(self, tokens_used: int, action: str) -> Dict[str, Any]:
        """Record turn token usage and executed action; evaluate reset conditions."""
        self.cumulative_tokens += tokens_used
        self.recent_actions.append(action)
        if len(self.recent_actions) > self.entropy_window:
            self.recent_actions.pop(0)

        utilization = self.cumulative_tokens / max(1, self.max_context_tokens)
        entropy = self.calculate_action_entropy()

        warn_needed = (utilization >= self.warning_watermark) and not self.warning_issued
        if warn_needed:
            self.warning_issued = True

        reset_due_to_tokens = utilization >= self.reset_watermark
        reset_due_to_entropy = (len(self.recent_actions) >= self.entropy_window) and (entropy < self.min_action_entropy)

        should_reset = reset_due_to_tokens or reset_due_to_entropy
        reset_reason = None
        if reset_due_to_tokens:
            reset_reason = f"Token context watermark reached: {utilization * 100:.1f}% >= {self.reset_watermark * 100:.1f}%"
        elif reset_due_to_entropy:
            reset_reason = f"Behavioral action entropy collapsed: H={entropy:.2f} < {self.min_action_entropy:.2f} (stagnation detected)"

        return {
            "cumulative_tokens": self.cumulative_tokens,
            "utilization": utilization,
            "action_entropy": entropy,
            "warn_needed": warn_needed,
            "should_reset": should_reset,
            "reset_reason": reset_reason,
        }

    def trigger_pre_reset_warning(self, dynamic_note: Optional[str] = None) -> str:
        """Issue memory consolidation warning prompt."""
        if dynamic_note:
            return f"Context utilization high ({dynamic_note}). {self.PRE_RESET_WARNING}"
        return self.PRE_RESET_WARNING

    def advance_session(self) -> Dict[str, Any]:
        """Perform dynamic context reset and build re-hydrated system prompt."""
        self.session_index += 1
        self.active_session_id = f"session_{self.session_index:03d}"
        self.cumulative_tokens = 0
        self.warning_issued = False
        self.recent_actions.clear()

        # 1. Read semantic memory in full
        semantic_content = ""
        if self.memory.semantic_path.exists():
            semantic_content = self.memory.semantic_path.read_text(encoding="utf-8")

        # 2. Extract single-line summaries of episodic entries (Appendix A.2)
        episodic_summaries: List[str] = []
        for e in self.memory.episodic_entries:
            summary = (
                f"[{time.strftime('%H:%M:%S', time.gmtime(e.timestamp))}] "
                f"Step {e.step}: {e.action} -> "
                + (f"Pretense: '{e.symbolic_pretense}' | " if e.symbolic_pretense else "")
                + (f"Cause: '{e.hypothesized_cause}'" if e.hypothesized_cause else f"Obs: {e.observation}")
            )
            episodic_summaries.append(summary)

        # 3. Assemble rehydrated session system prompt
        rehydrated_prompt = (
            f"=== SOUL.md ===\n{self.soul_text}\n\n"
            f"=== ACTIVE SESSION ===\nSession ID: {self.active_session_id}\n\n"
            f"=== SEMANTIC MEMORY (Full Rules & Affordances) ===\n{semantic_content}\n\n"
            f"=== EPISODIC MEMORY SUMMARIES ({len(episodic_summaries)} events) ===\n"
            + "\n".join(episodic_summaries[-50:])  # Bound to last 50 entries
        )

        return {
            "new_session_id": self.active_session_id,
            "session_index": self.session_index,
            "rehydrated_prompt_length": len(rehydrated_prompt),
            "rehydrated_system_prompt": rehydrated_prompt,
            "episodic_entries_count": len(self.memory.episodic_entries),
            "semantic_affordances_count": len(self.memory.semantic_affordances),
        }


class HourlySessionResetManager(DynamicContextResetManager):
    """Backwards-compatible alias for DynamicContextResetManager."""
    pass


@dataclass
class EmpiricalPlayBenchmarkScorecard:
    """Quantitative evaluation suite comparing play-trained vs naive agents (arXiv:2610.07130 Sec 5.1).

    Probes 4 downstream tasks:
    1. many-5-towers: Build as many 5-block-high towers as possible.
    2. objects-on-spire: Get as many objects as possible onto the Spire.
    3. throw-on-spire: Throw a block onto the Spire without climbing.
    4. tallest-tower: Build tallest tower in one column.
    """

    agent_id: str
    play_hours: float
    many_5_towers_count: int
    objects_on_spire_count: int
    throw_on_spire_success: bool
    tallest_tower_blocks: int

    @classmethod
    def reference_30h_mean(cls) -> "EmpiricalPlayBenchmarkScorecard":
        """Reference mean performance of 30-hour play agents from Cloos et al. (Fig 5)."""
        return cls(
            agent_id="ref_30h_claude_opus_4_7",
            play_hours=30.0,
            many_5_towers_count=7,
            objects_on_spire_count=10,
            throw_on_spire_success=True,
            tallest_tower_blocks=23,
        )

    @classmethod
    def reference_0h_mean(cls) -> "EmpiricalPlayBenchmarkScorecard":
        """Reference mean performance of naive 0-hour agents from Cloos et al. (Fig 5)."""
        return cls(
            agent_id="ref_0h_naive_baseline",
            play_hours=0.0,
            many_5_towers_count=2,
            objects_on_spire_count=3,
            throw_on_spire_success=False,
            tallest_tower_blocks=15,
        )

    def evaluate_relative_lift(self, baseline: "EmpiricalPlayBenchmarkScorecard") -> Dict[str, float]:
        """Compute relative percentage improvements over naive baseline."""
        tower_lift = (self.many_5_towers_count - baseline.many_5_towers_count) / max(1, baseline.many_5_towers_count)
        spire_lift = (self.objects_on_spire_count - baseline.objects_on_spire_count) / max(1, baseline.objects_on_spire_count)
        height_lift = (self.tallest_tower_blocks - baseline.tallest_tower_blocks) / max(1, baseline.tallest_tower_blocks)
        return {
            "many_5_towers_lift": tower_lift * 100.0,
            "objects_on_spire_lift": spire_lift * 100.0,
            "tallest_tower_lift": height_lift * 100.0,
            "throw_success_delta": 1.0 if self.throw_on_spire_success and not baseline.throw_on_spire_success else 0.0,
        }
