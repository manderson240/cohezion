"""Stateless Language Agents (SLA): Scaling Long-Horizon Automated Research.
========================================================================
Reference: arXiv:2610.07625 (FAIR at Meta, UT Austin, Georgia Tech).

Core Principle: "Stateful Search with Stateless Agents"
-------------------------------------------------------
Prevailing conversational agent swarms suffer exponential token bloat,
attention degradation ("history fatigue"), and redundant search paths.
SLA resolves this by maintaining all search state, candidate DAGs,
evaluation logs, and diagnostics strictly inside the deterministic harness.

Agents (both Advisor and Workers) are stateless, single-turn mathematical
functions f(C_reconstructed) with zero conversational history replay.

Key Mechanisms:
1. Harness-Reconstructed Role-Specific Contexts.
2. Failure Disambiguation in Evidence Summaries:
   - INCONCLUSIVE_FAILURE: SyntaxError, runtime exception, OOM, timeout
     (hypothesis remains untested; does not penalize search branch).
   - MEASURED_NON_IMPROVEMENT: Code executed cleanly but score <= baseline
     (valid negative empirical evidence).
   - MEASURED_IMPROVEMENT: Code executed cleanly and score > baseline.
3. Local Candidate Retention with Global Reset:
   Workers retain and iterate on local candidates for up to k trials to allow
   multi-step refinement to mature before resetting to the global best.
4. Token Efficiency:
   Stateless Advisor uses <0.6% of tokens to coordinate parallel workers,
   achieving >84% token reduction vs stateful conversational swarms.
"""

from __future__ import annotations

import ast
import asyncio
import enum
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CandidateOutcome(str, enum.Enum):
    """Categorized evaluation outcomes per arXiv:2610.07625 Section 3."""

    MEASURED_IMPROVEMENT = "MEASURED_IMPROVEMENT"
    MEASURED_NON_IMPROVEMENT = "MEASURED_NON_IMPROVEMENT"
    INCONCLUSIVE_FAILURE = "INCONCLUSIVE_FAILURE"


@dataclass
class ResearchCandidate:
    """Immutable record of an evaluated code candidate in the harness state tree."""

    candidate_id: str
    code: str
    score: float
    outcome: CandidateOutcome
    diagnostics: str
    direction_id: str
    hypothesis: str
    worker_id: str
    epoch: int
    trial_index: int
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def short_hash(self) -> str:
        return hashlib.sha256(self.code.encode("utf-8")).hexdigest()[:8]


@dataclass
class AdvisorAssignment:
    """Explicit research directive issued from Stateless Advisor to a Worker."""

    worker_id: str
    direction_id: str
    hypothesis: str
    instructions: str
    reset_to_best: bool = False


@dataclass
class EvidenceSummary:
    """Role-specific context synthesized for the Stateless Advisor."""

    epoch: int
    global_best_candidate_id: Optional[str]
    global_best_score: float
    total_candidates: int
    direction_stats: Dict[str, Dict[str, Any]]
    formatted_markdown: str


class EvidenceSummarizer:
    """Synthesizes role-specific evidence summaries for the Stateless Advisor.

    Strictly disambiguates INCONCLUSIVE_FAILURE (syntax/runtime errors) from
    MEASURED_NON_IMPROVEMENT (empirical negative results) so the Advisor does
    not prematurely abandon directions obstructed merely by implementation bugs.
    """

    @staticmethod
    def classify_outcome(
        score: float,
        baseline_score: float,
        is_error: bool,
        error_msg: str = "",
    ) -> CandidateOutcome:
        """Deterministically classify evaluation outcome."""
        if is_error:
            return CandidateOutcome.INCONCLUSIVE_FAILURE
        if score > baseline_score:
            return CandidateOutcome.MEASURED_IMPROVEMENT
        return CandidateOutcome.MEASURED_NON_IMPROVEMENT

    @classmethod
    def summarize(
        cls,
        candidates: List[ResearchCandidate],
        epoch: int,
        global_best_candidate: Optional[ResearchCandidate],
        higher_is_better: bool = True,
    ) -> EvidenceSummary:
        """Build partitioned evidence summary across all research directions."""
        direction_stats: Dict[str, Dict[str, Any]] = {}

        for c in candidates:
            d_id = c.direction_id
            if d_id not in direction_stats:
                direction_stats[d_id] = {
                    "direction_id": d_id,
                    "hypothesis": c.hypothesis,
                    "improvements": 0,
                    "non_improvements": 0,
                    "inconclusive_failures": 0,
                    "best_score": c.score if c.outcome != CandidateOutcome.INCONCLUSIVE_FAILURE else -float("inf"),
                    "candidates_count": 0,
                    "recent_diagnostics": [],
                }

            st = direction_stats[d_id]
            st["candidates_count"] += 1

            if c.outcome == CandidateOutcome.MEASURED_IMPROVEMENT:
                st["improvements"] += 1
                if higher_is_better and c.score > st["best_score"]:
                    st["best_score"] = c.score
            elif c.outcome == CandidateOutcome.MEASURED_NON_IMPROVEMENT:
                st["non_improvements"] += 1
                if higher_is_better and c.score > st["best_score"]:
                    st["best_score"] = c.score
            elif c.outcome == CandidateOutcome.INCONCLUSIVE_FAILURE:
                st["inconclusive_failures"] += 1
                if c.diagnostics:
                    st["recent_diagnostics"].append(c.diagnostics[-200:])

        # Format markdown for the Advisor prompt
        lines: List[str] = [
            f"### Research Evidence Summary (Epoch {epoch})",
            f"- **Global Best Score**: {global_best_candidate.score if global_best_candidate else 'N/A'}",
            f"- **Total Candidates Evaluated**: {len(candidates)}",
            "",
            "| Direction ID | Hypothesis | Improvements | Non-Improvements | Inconclusive (Errors) | Best Score |",
            "| :--- | :--- | :---: | :---: | :---: | :---: |",
        ]

        for d_id, st in direction_stats.items():
            hyp_preview = st["hypothesis"][:40] + ("..." if len(st["hypothesis"]) > 40 else "")
            best_s = f"{st['best_score']:.4f}" if st["best_score"] != -float("inf") else "None"
            lines.append(
                f"| `{d_id}` | {hyp_preview} | {st['improvements']} | {st['non_improvements']} | {st['inconclusive_failures']} | {best_s} |"
            )

        lines.append("")
        lines.append("#### Direction Diagnostic Insights:")
        for d_id, st in direction_stats.items():
            if st["inconclusive_failures"] > 0:
                recent_err = st["recent_diagnostics"][-1] if st["recent_diagnostics"] else "Unknown runtime error"
                lines.append(
                    f"- `{d_id}`: {st['inconclusive_failures']} implementation failures (Hypothesis remains UNTESTED). Recent error: `{recent_err.strip()}`"
                )
            elif st["non_improvements"] > 0 and st["improvements"] == 0:
                lines.append(
                    f"- `{d_id}`: Empirical non-improvement observed across {st['non_improvements']} trials."
                )

        best_id = global_best_candidate.candidate_id if global_best_candidate else None
        best_score = global_best_candidate.score if global_best_candidate else -float("inf")

        return EvidenceSummary(
            epoch=epoch,
            global_best_candidate_id=best_id,
            global_best_score=best_score,
            total_candidates=len(candidates),
            direction_stats=direction_stats,
            formatted_markdown="\n".join(lines),
        )


class StatelessAdvisor:
    """Single-turn stateless coordinator (arXiv:2610.07625).

    Consumes <0.6% of system tokens. Reconstructs role-specific context
    from EvidenceSummary, plans search directions, and emits explicit
    assignments to parallel workers.
    """

    def __init__(
        self,
        task_description: str,
        initial_directions: List[Dict[str, str]],
        llm_caller: Optional[Callable[[str], Awaitable[str]]] = None,
    ) -> None:
        self.task_description = task_description
        self.initial_directions = initial_directions
        self.llm_caller = llm_caller

    def build_prompt(
        self,
        summary: EvidenceSummary,
        active_worker_ids: List[str],
    ) -> str:
        """Construct the compact, single-turn context for the Advisor."""
        prompt_parts = [
            "# Stateless Research Advisor Consultation",
            f"**Task Description**: {self.task_description}",
            "",
            summary.formatted_markdown,
            "",
            f"**Active Workers to Assign**: {', '.join(active_worker_ids)}",
            "",
            "## Directives:",
            "1. Allocate each worker to an explicit direction_id and scientific hypothesis.",
            "2. Note: INCONCLUSIVE_FAILURE indicates code bugs/syntax issues, NOT bad ideas. Do not prematurely abandon high-potential directions due to implementation bugs.",
            "3. If a direction has multiple MEASURED_NON_IMPROVEMENT results, pivot or damp allocation.",
            "4. Specify `reset_to_best: True` if the worker should abandon their local branch and restart from the global best.",
            "",
            "Please output your assignments in JSON format:",
            "```json",
            "[",
            '  {"worker_id": "worker_0", "direction_id": "dir_1", "hypothesis": "...", "instructions": "...", "reset_to_best": false}',
            "]",
            "```",
        ]
        return "\n".join(prompt_parts)

    async def assign(
        self,
        summary: EvidenceSummary,
        active_worker_ids: List[str],
    ) -> List[AdvisorAssignment]:
        """Generate worker assignments via single-turn query."""
        if not self.llm_caller:
            # Deterministic / heuristic fallback if no LLM caller provided
            return self._heuristic_assignment(summary, active_worker_ids)

        prompt = self.build_prompt(summary, active_worker_ids)
        response = await self.llm_caller(prompt)

        assignments = self._parse_assignments(response, active_worker_ids)
        if not assignments:
            logger.warning("Advisor LLM output failed to parse into assignments. Using Jev decision allocation.")
            assignments = await self.assign_via_jev(summary, active_worker_ids)
            if not assignments:
                logger.warning("Jev allocation exhausted. Using heuristic fallback.")
                return self._heuristic_assignment(summary, active_worker_ids)
        return assignments

    async def assign_via_jev(
        self,
        summary: EvidenceSummary,
        active_worker_ids: List[str],
    ) -> List[AdvisorAssignment]:
        """Categorical worker-to-direction assignment using LLM-as-Jev (arXiv:2610.02076).

        Formats directions as prefix-free options [1]..[K] and uses Jev scoring
        to eliminate JSON parsing failures.
        """
        from cohezion.decision.llm_as_jev import JevCandidate, JevPromptFormatter, JevTrieScorer

        dirs = list(summary.direction_stats.keys())
        for init in self.initial_directions:
            if init["direction_id"] not in dirs:
                dirs.append(init["direction_id"])

        if not dirs:
            return []

        candidates: List[JevCandidate] = []
        for idx, d_id in enumerate(dirs, start=1):
            st = summary.direction_stats.get(d_id, {})
            hyp = st.get("hypothesis")
            if not hyp:
                for init in self.initial_directions:
                    if init["direction_id"] == d_id:
                        hyp = init.get("hypothesis", "Iterate hypothesis")
                        break
            hyp = hyp or "Iterate hypothesis"
            desc = (
                f"{hyp} | Imprv: {st.get('improvements', 0)}, "
                f"NonImprv: {st.get('non_improvements', 0)}, "
                f"Failures: {st.get('inconclusive_failures', 0)}"
            )
            candidates.append(JevCandidate(index=idx, label=d_id, description=desc))

        assignments: List[AdvisorAssignment] = []
        scorer = JevTrieScorer(candidates)

        for w_id in active_worker_ids:
            if not self.llm_caller:
                break
            jev_prompt = JevPromptFormatter.format_prompt(
                context=(
                    f"Advisor Coordination for {self.task_description}\n"
                    f"Global Best: {summary.global_best_score}\n"
                    f"Target Worker: {w_id}"
                ),
                candidates=candidates,
                instruction=f"Select the highest priority research direction for {w_id}:",
            )
            resp = await self.llm_caller(jev_prompt)
            decision = scorer.score_from_completion(resp)
            chosen_cand = decision.selected_candidate
            st = summary.direction_stats.get(chosen_cand.label, {})
            reset = st.get("non_improvements", 0) >= 3

            assignments.append(
                AdvisorAssignment(
                    worker_id=w_id,
                    direction_id=chosen_cand.label,
                    hypothesis=chosen_cand.description.split(" | ")[0],
                    instructions=f"Focus on {chosen_cand.label} (Jev confidence: {decision.confidence:.2%})",
                    reset_to_best=reset,
                )
            )

        return assignments

    def _heuristic_assignment(
        self,
        summary: EvidenceSummary,
        active_worker_ids: List[str],
    ) -> List[AdvisorAssignment]:
        """Deterministic round-robin assignment across available directions."""
        assignments: List[AdvisorAssignment] = []
        dirs = list(summary.direction_stats.keys())

        # If no prior directions or initial directions remain unexplored, seed them
        for init in self.initial_directions:
            if init["direction_id"] not in dirs:
                dirs.append(init["direction_id"])

        if not dirs:
            dirs = ["direction_default"]

        for idx, w_id in enumerate(active_worker_ids):
            target_dir = dirs[idx % len(dirs)]
            # Find matching hypothesis from initial or stats
            hyp = "Optimize candidate algorithm"
            for init in self.initial_directions:
                if init["direction_id"] == target_dir:
                    hyp = init.get("hypothesis", hyp)
                    break
            if target_dir in summary.direction_stats:
                hyp = summary.direction_stats[target_dir]["hypothesis"]

            st = summary.direction_stats.get(target_dir, {})
            # If direction has severe non-improvement, reset to best
            reset = st.get("non_improvements", 0) >= 3

            assignments.append(
                AdvisorAssignment(
                    worker_id=w_id,
                    direction_id=target_dir,
                    hypothesis=hyp,
                    instructions=f"Implement hypothesis for {target_dir}",
                    reset_to_best=reset,
                )
            )
        return assignments

    def _parse_assignments(
        self,
        response: str,
        active_worker_ids: List[str],
    ) -> List[AdvisorAssignment]:
        """Extract structured JSON assignments from LLM completion."""
        import json

        text = response.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            raw_list = json.loads(text)
            if not isinstance(raw_list, list):
                return []
            result: List[AdvisorAssignment] = []
            for item in raw_list:
                w_id = item.get("worker_id")
                if w_id in active_worker_ids:
                    result.append(
                        AdvisorAssignment(
                            worker_id=w_id,
                            direction_id=item.get("direction_id", "dir_general"),
                            hypothesis=item.get("hypothesis", "Iterate candidate"),
                            instructions=item.get("instructions", ""),
                            reset_to_best=bool(item.get("reset_to_best", False)),
                        )
                    )
            return result
        except Exception as e:
            logger.debug("Failed to parse advisor assignments json: %s", e)
            return []


class StatelessWorker:
    """Single-turn stateless research worker (arXiv:2610.07625).

    Executes isolated code mutations for an assigned hypothesis.
    Maintains NO conversational memory across invocations. Receives only:
    1. Assigned hypothesis & instructions.
    2. Working code candidate.
    3. Last trial diagnostic/error (if local trial).
    """

    def __init__(
        self,
        worker_id: str,
        llm_caller: Optional[Callable[[str], Awaitable[str]]] = None,
    ) -> None:
        self.worker_id = worker_id
        self.llm_caller = llm_caller

    def build_prompt(
        self,
        assignment: AdvisorAssignment,
        working_code: str,
        diagnostics: Optional[str] = None,
        trial_index: int = 0,
    ) -> str:
        """Construct isolated, single-turn context for the worker."""
        prompt_parts = [
            f"# Worker Code Proposal (Worker: {self.worker_id}, Local Trial: {trial_index})",
            f"**Assigned Direction**: `{assignment.direction_id}`",
            f"**Scientific Hypothesis**: {assignment.hypothesis}",
            f"**Advisor Instructions**: {assignment.instructions}",
            "",
            "## Working Base Code:",
            "```python",
            working_code.strip(),
            "```",
        ]

        if diagnostics and diagnostics.strip():
            prompt_parts.extend([
                "",
                "## Previous Trial Diagnostics / Error Feedback:",
                "```",
                diagnostics.strip()[-1000:],  # Bound error feedback to 1000 chars
                "```",
                "Carefully inspect the above error and fix the underlying issue while realizing the hypothesis.",
            ])

        prompt_parts.extend([
            "",
            "## Instructions:",
            "Synthesize the complete, updated Python code that realizes the assigned hypothesis.",
            "Output your code strictly in a ```python block. Ensure syntax is 100% valid.",
        ])

        return "\n".join(prompt_parts)

    async def propose_code(
        self,
        assignment: AdvisorAssignment,
        working_code: str,
        diagnostics: Optional[str] = None,
        trial_index: int = 0,
    ) -> str:
        """Generate code mutation via single-turn call."""
        if not self.llm_caller:
            # Deterministic code mutation fallback for testing
            return self._heuristic_mutation(working_code, assignment, trial_index)

        prompt = self.build_prompt(assignment, working_code, diagnostics, trial_index)
        response = await self.llm_caller(prompt)
        return self._extract_code(response, working_code)

    def _heuristic_mutation(
        self,
        base_code: str,
        assignment: AdvisorAssignment,
        trial_index: int,
    ) -> str:
        """Simple comment / variable injection for tests."""
        comment = f"# SLA mutated by {self.worker_id} for {assignment.direction_id} trial {trial_index}\n"
        return comment + base_code

    def _extract_code(self, response: str, fallback_code: str) -> str:
        """Extract clean python code block from response."""
        if "```python" in response:
            code = response.split("```python", 1)[1].split("```", 1)[0].strip()
            if code:
                return code
        elif "```" in response:
            code = response.split("```", 1)[1].split("```", 1)[0].strip()
            if code:
                return code
        return fallback_code


class SLAHarness:
    """Stateful Research Harness for Stateless Language Agents (arXiv:2610.07625).

    The harness owns the system state tree, manages local candidate retention
    over k trials with global reset, and coordinates stateless Advisor & Workers.
    """

    def __init__(
        self,
        initial_code: str,
        task_description: str,
        initial_directions: List[Dict[str, str]],
        evaluator_fn: Callable[[str], Awaitable[Tuple[float, str, bool]]],
        worker_ids: Optional[List[str]] = None,
        local_retention_k: int = 3,
        higher_is_better: bool = True,
        advisor_caller: Optional[Callable[[str], Awaitable[str]]] = None,
        worker_callers: Optional[Dict[str, Callable[[str], Awaitable[str]]]] = None,
    ) -> None:
        self.task_description = task_description
        self.initial_code = initial_code
        self.evaluator_fn = evaluator_fn
        self.worker_ids = worker_ids or ["worker_0", "worker_1"]
        self.local_retention_k = local_retention_k
        self.higher_is_better = higher_is_better

        # Harness State
        self.candidates: Dict[str, ResearchCandidate] = {}
        self.global_best_candidate: Optional[ResearchCandidate] = None
        self.epoch: int = 0

        # Worker local tracking: worker_id -> (current_candidate_id, trial_count, last_diagnostics)
        self.worker_local_state: Dict[str, Dict[str, Any]] = {}
        for w_id in self.worker_ids:
            self.worker_local_state[w_id] = {
                "candidate_id": "seed",
                "trial_count": 0,
                "direction_id": "seed",
                "last_diagnostics": "",
            }

        # Token ledger
        self.total_advisor_tokens: int = 0
        self.total_worker_tokens: int = 0

        # Submodules
        self.advisor = StatelessAdvisor(
            task_description=task_description,
            initial_directions=initial_directions,
            llm_caller=advisor_caller,
        )
        self.workers: Dict[str, StatelessWorker] = {
            w_id: StatelessWorker(
                worker_id=w_id,
                llm_caller=worker_callers.get(w_id) if worker_callers else None,
            )
            for w_id in self.worker_ids
        }

    async def initialize(self) -> ResearchCandidate:
        """Evaluate initial seed code and establish baseline candidate."""
        score, diag, is_err = await self.evaluator_fn(self.initial_code)
        outcome = CandidateOutcome.INCONCLUSIVE_FAILURE if is_err else CandidateOutcome.MEASURED_NON_IMPROVEMENT

        seed_candidate = ResearchCandidate(
            candidate_id="seed",
            code=self.initial_code,
            score=score,
            outcome=outcome,
            diagnostics=diag,
            direction_id="baseline",
            hypothesis="Baseline initialization",
            worker_id="system",
            epoch=0,
            trial_index=0,
        )
        self.candidates["seed"] = seed_candidate
        self.global_best_candidate = seed_candidate

        for w_id in self.worker_ids:
            self.worker_local_state[w_id]["candidate_id"] = "seed"
            self.worker_local_state[w_id]["trial_count"] = 0

        logger.info(
            "SLAHarness initialized. Seed score: %.4f (Outcome: %s)",
            score,
            outcome.value,
        )
        return seed_candidate

    async def run_epoch(self) -> Dict[str, Any]:
        """Execute one complete SLA research epoch (arXiv:2610.07625 Section 3).

        1. Synthesize EvidenceSummary for Advisor.
        2. Query Stateless Advisor for worker direction assignments.
        3. For each worker:
           - Enforce Local Retention or Global Reset.
           - Query Stateless Worker for proposed code.
           - Run sandbox evaluator and classify outcome.
           - Update local candidate retention or reset state.
           - Update global best if improved.
        """
        self.epoch += 1
        t_start = time.perf_counter()

        # Step 1: Synthesize EvidenceSummary
        summary = EvidenceSummarizer.summarize(
            candidates=list(self.candidates.values()),
            epoch=self.epoch,
            global_best_candidate=self.global_best_candidate,
            higher_is_better=self.higher_is_better,
        )

        # Step 2: Stateless Advisor assigns directions
        assignments = await self.advisor.assign(summary, self.worker_ids)
        assignment_map = {a.worker_id: a for a in assignments}

        # Step 3: Run Parallel Workers
        epoch_candidates: List[ResearchCandidate] = []

        async def _run_single_worker(w_id: str) -> ResearchCandidate:
            assignment = assignment_map.get(
                w_id,
                AdvisorAssignment(
                    worker_id=w_id,
                    direction_id="general_opt",
                    hypothesis="General algorithmic refinement",
                    instructions="Optimize code",
                    reset_to_best=False,
                ),
            )

            local_st = self.worker_local_state[w_id]
            curr_cand_id = local_st["candidate_id"]
            curr_cand = self.candidates.get(curr_cand_id, self.global_best_candidate)
            curr_code = curr_cand.code if curr_cand else self.initial_code

            # Enforce Reset vs Retention:
            # If reset_to_best is True, direction changed, or local trials exceeded k:
            direction_changed = local_st["direction_id"] != assignment.direction_id
            exceeded_retention = local_st["trial_count"] >= self.local_retention_k

            if assignment.reset_to_best or direction_changed or exceeded_retention:
                # Global Reset
                curr_cand = self.global_best_candidate
                curr_code = curr_cand.code if curr_cand else self.initial_code
                local_st["trial_count"] = 0
                local_st["direction_id"] = assignment.direction_id
                local_st["last_diagnostics"] = ""

            trial_idx = local_st["trial_count"]

            # Query Stateless Worker
            proposed_code = await self.workers[w_id].propose_code(
                assignment=assignment,
                working_code=curr_code,
                diagnostics=local_st["last_diagnostics"],
                trial_index=trial_idx,
            )

            # Evaluate Proposed Code
            score, diag, is_err = await self.evaluator_fn(proposed_code)

            # Classify Outcome with Failure Disambiguation
            baseline_ref = self.global_best_candidate.score if self.global_best_candidate else -float("inf")
            outcome = EvidenceSummarizer.classify_outcome(
                score=score,
                baseline_score=baseline_ref,
                is_error=is_err,
                error_msg=diag,
            )

            cand_id = str(uuid.uuid4())[:8]
            new_cand = ResearchCandidate(
                candidate_id=cand_id,
                code=proposed_code,
                score=score,
                outcome=outcome,
                diagnostics=diag,
                direction_id=assignment.direction_id,
                hypothesis=assignment.hypothesis,
                worker_id=w_id,
                epoch=self.epoch,
                trial_index=trial_idx,
                parent_id=curr_cand.candidate_id if curr_cand else None,
            )

            # Update Worker Local Retention State
            local_st["trial_count"] += 1
            local_st["last_diagnostics"] = diag

            if outcome == CandidateOutcome.MEASURED_IMPROVEMENT:
                # Worker adopts improved candidate
                local_st["candidate_id"] = cand_id
            elif outcome == CandidateOutcome.MEASURED_NON_IMPROVEMENT:
                # If local candidate is retaining, keep working on it until k trials
                if local_st["trial_count"] < self.local_retention_k:
                    local_st["candidate_id"] = cand_id
            # If INCONCLUSIVE_FAILURE, keep previous working candidate but carry error diagnostics

            return new_cand

        results = await asyncio.gather(*[_run_single_worker(w) for w in self.worker_ids])

        # Step 4: Update Harness Global State
        improvements_found = 0
        for cand in results:
            self.candidates[cand.candidate_id] = cand
            epoch_candidates.append(cand)

            if cand.outcome == CandidateOutcome.MEASURED_IMPROVEMENT:
                if self.global_best_candidate is None:
                    self.global_best_candidate = cand
                    improvements_found += 1
                else:
                    if self.higher_is_better and cand.score > self.global_best_candidate.score:
                        logger.info(
                            "Epoch %d Breakthrough! Global Best: %.4f -> %.4f (Worker %s, Dir %s)",
                            self.epoch,
                            self.global_best_candidate.score,
                            cand.score,
                            cand.worker_id,
                            cand.direction_id,
                        )
                        self.global_best_candidate = cand
                        improvements_found += 1

        elapsed = time.perf_counter() - t_start

        return {
            "epoch": self.epoch,
            "elapsed_seconds": elapsed,
            "global_best_score": self.global_best_candidate.score if self.global_best_candidate else None,
            "global_best_candidate_id": self.global_best_candidate.candidate_id if self.global_best_candidate else None,
            "improvements_found": improvements_found,
            "evaluated_candidates": len(epoch_candidates),
            "outcomes": {c.candidate_id: c.outcome.value for c in epoch_candidates},
        }

    def compute_efficiency_report(self) -> Dict[str, Any]:
        """Compute token efficiency and search performance metrics."""
        total = len(self.candidates)
        improvements = sum(1 for c in self.candidates.values() if c.outcome == CandidateOutcome.MEASURED_IMPROVEMENT)
        non_improvements = sum(1 for c in self.candidates.values() if c.outcome == CandidateOutcome.MEASURED_NON_IMPROVEMENT)
        inconclusives = sum(1 for c in self.candidates.values() if c.outcome == CandidateOutcome.INCONCLUSIVE_FAILURE)

        # Estimate token reduction vs stateful conversational replay
        # In a stateful agent with N epochs, tokens scale as O(N^2 * tokens_per_turn)
        # In SLA, tokens scale as O(N * tokens_per_turn)
        avg_tokens_per_turn = 1200
        stateful_projected_tokens = sum(i * avg_tokens_per_turn * len(self.worker_ids) for i in range(1, self.epoch + 1))
        sla_actual_projected_tokens = self.epoch * avg_tokens_per_turn * (len(self.worker_ids) + 1)
        savings_pct = (
            max(0.0, (1.0 - (sla_actual_projected_tokens / max(1, stateful_projected_tokens)))) * 100.0
            if stateful_projected_tokens > 0
            else 0.0
        )

        return {
            "total_candidates": total,
            "improvements": improvements,
            "non_improvements": non_improvements,
            "inconclusive_failures": inconclusives,
            "success_rate": improvements / max(1, total - inconclusives),
            "projected_token_savings_pct": savings_pct,
            "global_best_score": self.global_best_candidate.score if self.global_best_candidate else None,
        }
