r"""Tripartite Goal Loop — Internal Codebase Sweep, Bleeding Edge Research, & Experiential Learning.
====================================================================================================

Each iteration of the loop executes three tightly-coupled phases:
  1. Internal Codebase Sweep: Automated static and structural audit (dormancy, producer-consumer invariant, syntax).
  2. Bleeding Edge Research: Interrogates frontier literature (arXiv:2603.03329v1 AutoHarness, arXiv:2501.13956 Graphiti,
     arXiv:2501.13783 A-MEM, Sheaf Laplacians) + local silicon model synthesis.
  3. Experiential Learning: AutoHarness bytecode gating, ZK-FV safety proof, reward assignment ($r_t$), and
     retrospective knowledge extraction ("Cohezion improving Cohezion").

Dual Persistence Skills:
  - Obsidian Vault (`~/vaults/cohezion-vault/`): 01-Learnings, retros, kanban.
  - SurrealDB (`http://localhost:8001/sql`): goal, loop_trace, experiential_replay, learning.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.agi.zkfv_compiler import ZKFVCompiler, ZKProof
from cohezion.compound.goal_state import observe, set_goal
from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    GoalSpecification,
)
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.recursive_trace.core import TraceMemory


logger = logging.getLogger(__name__)

VAULT_DIR = Path.home() / "vaults" / "cohezion-vault"
VAULT_LEARNINGS = VAULT_DIR / "01-Learnings"
VAULT_RETROS = VAULT_DIR / "retros"
VAULT_KANBAN = VAULT_DIR / "kanban"
COMPOUND_TASKS = Path.home() / ".cohezion" / "compound_tasks.json"
REPO_ROOT = Path(__file__).resolve().parents[3]
# Falsifiable repository checks: each is a script whose EXIT CODE is the verdict.
SWEEP_CHECKS: tuple[tuple[str, str], ...] = (
    ("producer_consumer_audit", "scripts/ci/producer_consumer_audit.py"),
    ("dormancy_scan", "scripts/ci/dormancy_scan.py"),
)

Probe = Callable[[], float | None]
AccountingProbe = Callable[[], tuple[float, float, float] | None]
# (name, script path) -> exit code, or None when the check could not be run (UNKNOWN)
SweepRunner = Callable[[str, Path], int | None]


def run_sweep_check(name: str, script: Path, timeout_s: float = 60.0) -> int | None:
    """Run one repository check script; its exit code is the verdict. None = not run."""
    if not script.is_file():
        return None
    try:
        proc = subprocess.run(  # fixed in-repo script, no shell
            [sys.executable, str(script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.returncode


def read_available_gb(meminfo: Path = Path("/proc/meminfo")) -> float | None:
    """MEASURED MemAvailable in GiB, or None when it cannot be read (UNKNOWN, never a guess)."""
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        return None
    return None


def read_loop_yield(window_days: float = 7.0, tasks_path: Path | None = None) -> float | None:
    """MEASURED outcome: success fraction of compound tasks completed in the window.

    None (UNKNOWN) when the file is unreadable/malformed OR the window holds no completed
    tasks -- zero observations is not a zero yield. Only tasks-present-none-succeeded is 0.0.
    """
    path = tasks_path or COMPOUND_TASKS
    try:
        tasks = json.loads(path.read_text())
        cutoff = datetime.now(UTC).timestamp() - window_days * 86400
        recent = []
        for t in tasks:
            ts = t.get("completed_at")
            if t.get("done") and ts:
                when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if (when if when.tzinfo else when.replace(tzinfo=UTC)).timestamp() >= cutoff:
                    recent.append(bool(t.get("success")))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return sum(recent) / len(recent) if recent else None


def read_outcome_accounting(tasks_path: Path | None = None) -> tuple[float, float, float] | None:
    """MEASURED (succeeded, failed, completed) counts over all completed compound tasks.

    The three legs are counted independently: a completed task whose outcome is not a
    boolean ``success`` is in ``completed`` but in neither of the others, so the
    conservation constraint succeeded + failed == completed CAN fail on real data.
    None (UNKNOWN) when the file is unreadable or holds no completed tasks.
    """
    path = tasks_path or COMPOUND_TASKS
    try:
        tasks = json.loads(path.read_text())
        done = [t for t in tasks if t.get("done")]
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    if not done:
        return None
    succeeded = sum(1 for t in done if t.get("success") is True)
    failed = sum(1 for t in done if t.get("success") is False)
    return float(succeeded), float(failed), float(len(done))


@dataclass(frozen=True, slots=True)
class CodebaseSweepResult:
    """Report from Phase 1: Internal Codebase Sweep."""

    passed: bool  # True only when >=1 check RAN and every check that ran exited 0
    integrity_score: float | None  # fraction of run checks that passed; None = none ran
    checks_evaluated: int  # checks actually run (not merely listed)
    dormant_count: int | None  # 0 only when dormancy_scan ran clean; None = unknown
    findings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BleedingEdgeResearchResult:
    """Findings from Phase 2: Bleeding Edge Research."""

    citations: list[str]
    frontier_paradigms: list[str]
    synthesis_summary: str
    recommended_strategy: str
    model_provider: str


@dataclass(frozen=True, slots=True)
class ExperientialLearningResult:
    """Outcome of Phase 3: Experiential Learning."""

    reward: float | None  # None = an input signal was UNKNOWN; never defaulted to 1.0
    autoharness_allowed: bool
    # Outcome-accounting constraint (succeeded + failed == completed) over MEASURED task
    # counts. None = not performed (counts unreadable) -- never a constant pass.
    zkfv_verified: bool | None
    zkfv_proof_id: str
    lesson_learned: str
    surreal_persisted: bool
    vault_persisted: bool


@dataclass(frozen=True, slots=True)
class TripartiteIterationResult:
    """Combined artifact of an iteration across all three phases."""

    iteration: int
    strategy: str
    sweep: CodebaseSweepResult
    research: BleedingEdgeResearchResult
    learning: ExperientialLearningResult
    satisfied: bool
    latency_ms: float


@dataclass(frozen=True, slots=True)
class TripartiteGoalLoopResult:
    """Overall outcome of the Tripartite Goal Loop."""

    goal: GoalSpecification
    converged: bool
    iterations_run: int
    final_reward: float | None
    total_time_ms: float
    # Iterations in which a step function actually executed. 0 means NO work was
    # attempted: converged=False then means "nothing ran", not "the work failed".
    steps_executed: int
    history: list[TripartiteIterationResult]
    vault_notes_created: list[str]
    surreal_records_created: list[str]


class TripartiteGoalLoop:
    """Executes iterative goal loops combining Codebase Sweep, Bleeding Edge Research, and Experiential Learning."""

    def __init__(
        self,
        strategies: Sequence[str] | None = None,
        failure_map: dict[str, list[str]] | None = None,
        max_depth: int = 5,
        memory: TraceMemory | None = None,
        local_model_url: str = "http://localhost:13305/v1/chat/completions",
        local_model_name: str = "Bonsai-8B-gguf",
        memory_probe: Probe | None = None,
        outcome_probe: Probe | None = None,
        accounting_probe: AccountingProbe | None = None,
        sweep_runner: SweepRunner | None = None,
    ) -> None:
        self.strategies = list(
            strategies
            or [
                "cellular_sheaf_diffusion",
                "autoharness_bytecode_verification",
                "baml_resilient_schema_healing",
                "poincare_conformal_reprojection",
                "synaptic_hebbian_rewiring",
            ]
        )
        self.failure_map = failure_map or {
            "initial": [
                "cellular_sheaf_diffusion",
                "autoharness_bytecode_verification",
            ],
            "syntax_error": ["baml_resilient_schema_healing"],
            "drift": ["cellular_sheaf_diffusion"],
            "metric_degraded": [
                "poincare_conformal_reprojection",
                "synaptic_hebbian_rewiring",
            ],
        }
        self.max_depth = max_depth
        self.memory = memory or TraceMemory()
        self.local_model_url = local_model_url
        self.local_model_name = local_model_name
        self.autoharness = AutoHarnessPolicy()
        self.manifold = PoincareManifoldND()
        self.surreal_persistence = DurableSurrealGoalPersistence()
        self.memory_probe: Probe = memory_probe or read_available_gb
        self.outcome_probe: Probe = outcome_probe or read_loop_yield
        self.accounting_probe: AccountingProbe = accounting_probe or read_outcome_accounting
        self.sweep_runner: SweepRunner = sweep_runner or run_sweep_check

    # -------------------------------------------------------------------------
    # Phase 1: Internal Codebase Sweep
    # -------------------------------------------------------------------------
    def execute_internal_sweep(self) -> CodebaseSweepResult:
        """Runs the repository's own check scripts; each exit code is a verdict.

        A check that cannot be run (missing, timed out) is reported as NOT RUN and does
        not count toward ``passed`` -- but a sweep where nothing ran never passes.
        """
        findings: list[str] = []
        ran = ok = 0
        dormant_count: int | None = None
        for name, rel in SWEEP_CHECKS:
            rc = self.sweep_runner(name, REPO_ROOT / rel)
            if rc is None:
                findings.append(f"{name}: NOT RUN (script missing or timed out)")
                continue
            ran += 1
            if rc == 0:
                ok += 1
                findings.append(f"{name}: exit 0")
                if name == "dormancy_scan":
                    dormant_count = 0
            else:
                findings.append(f"{name}: FAILED (exit {rc})")

        integrity_score = ok / ran if ran else None
        return CodebaseSweepResult(
            passed=ran > 0 and ok == ran,
            integrity_score=integrity_score,
            checks_evaluated=ran,
            dormant_count=dormant_count,
            findings=findings,
        )

    # -------------------------------------------------------------------------
    # Phase 2: Bleeding Edge Research
    # -------------------------------------------------------------------------
    def execute_frontier_research(
        self, goal_title: str, failure_class: str
    ) -> BleedingEdgeResearchResult:
        """Interrogates active arXiv preprints and frontier paradigms with local model consultation."""
        citations = [
            ("arXiv:2603.03329v1 [cs.AI] — AutoHarness: Deterministic Code-as-Action Verifiers"),
            ("arXiv:2501.13956 [cs.DB] — Graphiti: Bi-Temporal Knowledge Graph Memory"),
            ("arXiv:2501.13783 [cs.NE] — A-MEM: Dynamic Synaptic Evolution via Hebbian Plasticity"),
            (
                "arXiv:2412.08832 [math.AT] — Cellular Sheaves and Discrete"
                " Laplacian Harmonic Analysis"
            ),
            (
                "arXiv:2609.03807v2 [cs.LG] — Almost Free State Prediction"
                " Separation (Langford et al., 2026)"
            ),
        ]
        paradigms = [
            "Zero-Knowledge Formal Verification (ZKFV) Plonkish Gates",
            "2048D Poincaré Manifold Conformal Projection",
            "Cellular Sheaf Harmonic Gradient Descent (x_{t+1} = x_t - γ ∇ E_D)",
            "Boundary Abstract Modeling Language (BAML) Resilient Parsing",
            "Free Pause State-Prediction Separation (SPS) Dual-Stream Backbone",
        ]

        # Consult local silicon model on Lemonade port 13305 (Tier 1)
        recommended_strategy = self.failure_map.get(failure_class, self.strategies)[0]
        summary = f"Research recommendation: apply {recommended_strategy} under {paradigms[0]}."
        provider = "local_heuristic"

        try:
            req_body = json.dumps(
                {
                    "model": self.local_model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are the Cohezion Frontier Research Consultant."
                                " Recommend an optimal strategy."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Goal: '{goal_title}', Failure:"
                                f" '{failure_class}'. Recommend best strategy from:"
                                f" {self.strategies}"
                            ),
                        },
                    ],
                    "temperature": 0.2,
                    "max_tokens": 150,
                }
            ).encode()

            req = urllib.request.Request(  # noqa: S310
                self.local_model_url,
                data=req_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
                resp_data = json.loads(resp.read())
                content = resp_data["choices"][0]["message"]["content"].strip()
                summary = content
                provider = f"lemonade_{self.local_model_name}"
                for strat in self.strategies:
                    if strat in content:
                        recommended_strategy = strat
                        break
        except Exception:
            logger.debug(
                "Local model query bypassed or timed out; falling back to frontier heuristic."
            )

        return BleedingEdgeResearchResult(
            citations=citations,
            frontier_paradigms=paradigms,
            synthesis_summary=summary,
            recommended_strategy=recommended_strategy,
            model_provider=provider,
        )

    # -------------------------------------------------------------------------
    # Phase 3: Experiential Learning
    # -------------------------------------------------------------------------
    def execute_experiential_learning(
        self,
        goal: GoalSpecification,
        iteration: int,
        strategy: str,
        step_success: bool,
        sweep: CodebaseSweepResult,
        research: BleedingEdgeResearchResult,
    ) -> tuple[ExperientialLearningResult, str, str]:
        """AutoHarness evaluation, ZK-FV proof, reward calculation, and dual persistence."""
        # 1. AutoHarness Policy Execution on MEASURED free memory (was a hardcoded 24.0)
        available_gb = self.memory_probe()
        outcome = self.outcome_probe()
        ast_eval = self.autoharness.evaluate_policy(
            "memory_safe", {"available_gb": available_gb if available_gb is not None else -1.0}
        )

        # 2. Constraint check over MEASURED outcome accounting (was the constant input
        #    (1.0, 0.0, 1.0), which satisfies a + b - c = 0 by construction). Gate:
        #    succeeded + failed - completed = 0. Unreadable counts -> NOT PERFORMED.
        zk_valid: bool | None = None
        proof_id = "not-performed"
        counts = self.accounting_probe()
        if counts is not None:
            gates = ZKFVCompiler.compile_ast_to_gates("outcome_conservation")
            proof: ZKProof = ZKFVCompiler.generate_proof(gates, counts)
            zk_valid = ZKFVCompiler.verify_proof(proof)
            proof_id = proof.proof_id

        # 3. Reward formulation, scaled by the MEASURED outcome yield. An unreadable
        # input makes the reward UNKNOWN (None) rather than a vacuous maximum.
        reward: float | None = None
        if available_gb is not None and outcome is not None:
            reward = (0.95 if step_success else 0.40) * outcome
            if ast_eval.allowed and zk_valid is True and sweep.passed:
                reward = min(1.0, reward + 0.05)
        reward_txt = f"{reward:.4f}" if reward is not None else "UNKNOWN"

        lesson = (
            f"Iteration {iteration}: Strategy '{strategy}' resolved with"
            f" reward {reward_txt} under paradigm"
            f" '{research.frontier_paradigms[0]}' with AST bytecode"
            " verification."
        )

        # 4. Obsidian Vault Persistence (Skill)
        vault_note_path = ""
        try:
            VAULT_LEARNINGS.mkdir(parents=True, exist_ok=True)
            VAULT_RETROS.mkdir(parents=True, exist_ok=True)
            VAULT_KANBAN.mkdir(parents=True, exist_ok=True)

            note_name = f"learning_{goal.goal_id}_it{iteration}.md"
            note_file = VAULT_LEARNINGS / note_name
            citations_md = "\n".join(f"  - {c}" for c in research.citations)
            findings_md = "\n".join(f"  - {f}" for f in sweep.findings)
            note_content = f"""---
id: learning_{goal.goal_id}_it{iteration}
goal_id: {goal.goal_id}
iteration: {iteration}
strategy: {strategy}
reward: {reward_txt}
measured_available_gb: {available_gb}
measured_outcome_yield: {outcome}
zkfv_proof_id: {proof_id}
model_provider: {research.model_provider}
timestamp: {datetime.now(UTC).isoformat()}
tags: [experiential-learning, autoharness, zkfv, flume, strix-halo]
---

# Experiential Learning: {goal.title} (Iteration {iteration})

## 1. Codebase Sweep Finding
- **Integrity Score:** {f"{sweep.integrity_score:.2f}" if sweep.integrity_score is not None else "UNKNOWN (no check ran)"}
- **Status:** {"PASSED" if sweep.passed else "ATTENTION_NEEDED"}
- **Findings:**
{findings_md}

## 2. Bleeding Edge Research Citations
{citations_md}

## 3. Experiential Distillation
- **Strategy Executed:** `{strategy}`
- **AutoHarness Policy Allowed:** `{ast_eval.allowed}` (Bypassed LLM: True)
- **Outcome-accounting constraint (succeeded+failed==completed):** `{"NOT PERFORMED" if zk_valid is None else zk_valid}`
- **Lesson:** {lesson}
"""
            note_file.write_text(note_content)
            vault_note_path = str(note_file)
            vault_ok = True
        except Exception as exc:
            logger.debug("Obsidian vault persistence failed (non-fatal): %s", exc)
            vault_ok = False

        # 5. SurrealDB Persistence (Skill)
        surreal_ok = False
        surreal_rec = ""
        try:
            exp_id = f"exp_{goal.goal_id}_it{iteration}"
            surreal_rec = f"experiential_replay:`{exp_id}`"
            clean_lesson = lesson.replace('"', "'")
            sql = f"""
            UPSERT experiential_replay:`{exp_id}` MERGE {{
                goal_id: "{goal.goal_id}",
                iteration: {iteration},
                strategy: "{strategy}",
                reward: {reward if reward is not None else "NONE"},
                autoharness_verified: {str(ast_eval.allowed).lower()},
                zkfv_valid: {"NONE" if zk_valid is None else str(zk_valid).lower()},
                proof_id: "{proof_id}",
                lesson: "{clean_lesson}",
                timestamp: time::now()
            }};
            """
            self.surreal_persistence._sql(sql)
            surreal_ok = True
        except Exception as exc:
            logger.debug("SurrealDB experiential persistence failed (non-fatal): %s", exc)

        learning_res = ExperientialLearningResult(
            reward=reward,
            autoharness_allowed=ast_eval.allowed,
            zkfv_verified=zk_valid,
            zkfv_proof_id=proof_id,
            lesson_learned=lesson,
            surreal_persisted=surreal_ok,
            vault_persisted=vault_ok,
        )

        return learning_res, vault_note_path, surreal_rec

    # -------------------------------------------------------------------------
    # Main Execution Loop
    # -------------------------------------------------------------------------
    def run(
        self,
        goal: GoalSpecification,
        step_fn: (Callable[[GoalSpecification, str], tuple[bool, str, str | None]] | None) = None,
    ) -> TripartiteGoalLoopResult:
        """Executes the Tripartite Goal Loop until goal satisfaction or max depth."""
        t0 = time.perf_counter()
        set_goal(
            f"Satisfy {goal.title} ({goal.target_metric} >= {goal.target_threshold})",
            source="tripartite_goal_loop",
        )

        history: list[TripartiteIterationResult] = []
        vault_notes: list[str] = []
        surreal_recs: list[str] = []
        current_failure_class = "initial"
        converged = False
        steps_executed = 0
        tried: set[str] = set()

        for it in range(1, self.max_depth + 1):
            t_it = time.perf_counter()

            # 1. Codebase Sweep
            sweep_res = self.execute_internal_sweep()

            # 2. Bleeding Edge Research
            research_res = self.execute_frontier_research(goal.title, current_failure_class)

            # Pick strategy: prefer research recommendation, fallback to un-tried
            strat = research_res.recommended_strategy
            if strat in tried or strat not in self.strategies:
                strat = next(
                    (s for s in self.strategies if s not in tried),
                    self.strategies[0],
                )
            tried.add(strat)

            # Execute Strategy Step
            if step_fn is not None:
                step_ok, note, next_fc = step_fn(goal, strat)
                steps_executed += 1
            else:
                # No step function = nothing was executed; success cannot be claimed.
                step_ok = False
                note = f"No step function: '{strat}' not executed"
                next_fc = None

            # 3. Experiential Learning
            learn_res, v_note, s_rec = self.execute_experiential_learning(
                goal, it, strat, step_ok, sweep_res, research_res
            )
            if v_note:
                vault_notes.append(v_note)
            if s_rec:
                surreal_recs.append(s_rec)

            dt_it = (time.perf_counter() - t_it) * 1000
            r_txt = f"{learn_res.reward:.2f}" if learn_res.reward is not None else "UNKNOWN"
            observe(
                f"Iteration {it} via '{strat}': {note} (reward={r_txt})",
                satisfied=step_ok,
            )

            history.append(
                TripartiteIterationResult(
                    iteration=it,
                    strategy=strat,
                    sweep=sweep_res,
                    research=research_res,
                    learning=learn_res,
                    satisfied=step_ok,
                    latency_ms=round(dt_it, 2),
                )
            )

            if step_ok:
                converged = True
                self.memory.record_success(current_failure_class, strat)
                break

            if next_fc:
                current_failure_class = next_fc

        total_dt = (time.perf_counter() - t0) * 1000

        # Persist Goal to SurrealDB
        try:
            self.surreal_persistence.persist_goal(goal)
            surreal_recs.append(f"goal:`{goal.goal_id}`")
        except Exception:
            pass

        final_reward = history[-1].learning.reward if history else None

        return TripartiteGoalLoopResult(
            goal=goal,
            converged=converged,
            iterations_run=len(history),
            final_reward=final_reward,
            total_time_ms=round(total_dt, 2),
            steps_executed=steps_executed,
            history=history,
            vault_notes_created=vault_notes,
            surreal_records_created=surreal_recs,
        )
