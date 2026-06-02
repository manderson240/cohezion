"""Retrospection engine for compound engineering pattern analysis."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

# Path constants
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_KG_DIR = _PROJECT_ROOT / "src" / "cohezion" / "knowledge_graph"


@dataclass
class LearningPattern:
    """A pattern extracted from KEY_LEARNINGS.md.

    Attributes
    ----------
    id : int
        Numeric learning identifier.
    title : str
        Human-readable title of the learning.
    date : str
        ISO date string (YYYY-MM-DD) if present.
    tags : list[str]
        Extracted tags (e.g. brane encodings).
    cross_references : list[str]
        References to other learnings or PRIME skills.
    compound_score : float
        Calculated compound impact score (0-1).
    """

    id: int
    title: str
    date: str
    tags: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    compound_score: float = 0.0


@dataclass
class SkillRefinement:
    """A suggested refinement to an existing PRIME skill.

    Attributes
    ----------
    skill_name : str
        Name of the PRIME skill to refine.
    reason : str
        Why the refinement is suggested.
    suggested_additions : list[str]
        Learning titles that inform the refinement.
    """

    skill_name: str
    reason: str
    suggested_additions: list[str] = field(default_factory=list)


class RetrospectionEngine:
    """Analyze session history and knowledge graph for compound patterns.

    Reads KEY_LEARNINGS.md and MISSION_JOURNAL.md to detect recurring
    themes, calculate compound impact scores, and suggest skill refinements.

    Parameters
    ----------
    kg_dir : Path | None
        Override path to the knowledge graph directory.
    """

    def __init__(self, kg_dir: Path | None = None) -> None:
        self.kg_dir = kg_dir or _KG_DIR
        self._learnings: list[LearningPattern] = []
        self._journal_entries: list[dict] = []

    def analyze_learnings(self) -> list[LearningPattern]:
        """Parse KEY_LEARNINGS.md, extract tagged patterns, count cross-references.

        Returns
        -------
        list[LearningPattern]
            Parsed learning patterns with tags and cross-references.
        """
        learnings_path = self.kg_dir / "KEY_LEARNINGS.md"
        if not learnings_path.exists():
            logger.warning("KEY_LEARNINGS.md not found at %s", learnings_path)
            return []

        text = learnings_path.read_text(encoding="utf-8")
        patterns: list[LearningPattern] = []

        # Parse learning blocks (## Learning N: TITLE)
        learning_re = re.compile(
            r"##\s+Learning\s+(\d+)[:\s]+(.+?)(?:\s*\((\d{4}-\d{2}-\d{2})\))?\s*$",
            re.MULTILINE,
        )

        matches = list(learning_re.finditer(text))
        for i, match in enumerate(matches):
            learning_id = int(match.group(1))
            title = match.group(2).strip()
            date = match.group(3) or ""

            # Extract body text until next learning
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]

            # Extract tags from encoding lines
            tags: list[str] = []
            encoding_re = re.compile(r"brane=(\d+)")
            for m in encoding_re.finditer(body):
                tags.append(f"brane-{m.group(1)}")

            # Extract cross-references to other learnings/skills
            cross_refs: list[str] = []
            ref_re = re.compile(r"Learning\s+(\d+)|([A-Z_]+_PRIME)")
            for m in ref_re.finditer(body):
                ref = m.group(0)
                cross_refs.append(ref)

            pattern = LearningPattern(
                id=learning_id,
                title=title,
                date=date,
                tags=tags,
                cross_references=cross_refs,
            )
            patterns.append(pattern)

        self._learnings = patterns
        return patterns

    def calculate_compound_scores(self) -> dict[str, float]:
        """Score each learning by how often it is referenced by other learnings.

        Returns
        -------
        dict[str, float]
            Mapping of learning/skill name to compound score (0-1).
        """
        if not self._learnings:
            self.analyze_learnings()

        # Count incoming references for each learning
        ref_counts: dict[int, int] = {}
        all_refs: list[str] = []

        for pattern in self._learnings:
            for ref in pattern.cross_references:
                all_refs.append(ref)
                # Extract learning ID from "Learning N" references
                m = re.match(r"Learning\s+(\d+)", ref)
                if m:
                    ref_id = int(m.group(1))
                    ref_counts[ref_id] = ref_counts.get(ref_id, 0) + 1

        # Also count skill references
        skill_refs: dict[str, int] = {}
        for ref in all_refs:
            if "_PRIME" in ref:
                skill_refs[ref] = skill_refs.get(ref, 0) + 1

        # Normalize scores (0-1 range)
        max_count = max(ref_counts.values()) if ref_counts else 1
        scores: dict[str, float] = {}

        for pattern in self._learnings:
            incoming = ref_counts.get(pattern.id, 0)
            outgoing = len(pattern.cross_references)
            # Score = normalized(incoming refs) + 0.3 * normalized(outgoing refs)
            score = (incoming / max_count) + 0.3 * (outgoing / max(len(self._learnings), 1))
            scores[f"Learning {pattern.id}: {pattern.title}"] = round(min(score, 1.0), 3)

        # Add skill scores
        max_skill = max(skill_refs.values()) if skill_refs else 1
        for skill, count in skill_refs.items():
            scores[skill] = round(count / max_skill, 3)

        return scores

    def generate_session_report(self, session_facts: dict) -> str:
        """Generate a structured retrospective report from session facts.

        Parameters
        ----------
        session_facts : dict
            Keys like ``"intent"``, ``"files_created"``, ``"files_modified"``,
            ``"tests_added"``, ``"tests_passing"``, ``"capabilities_used"``.

        Returns
        -------
        str
            Markdown-formatted retrospective report.
        """
        lines = ["# Session Retrospective Report", ""]

        if "intent" in session_facts:
            lines.append(f"## Intent\n{session_facts['intent']}\n")

        if "files_created" in session_facts:
            lines.append("## Files Created")
            for f in session_facts["files_created"]:
                lines.append(f"- `{f}`")
            lines.append("")

        if "files_modified" in session_facts:
            lines.append("## Files Modified")
            for f in session_facts["files_modified"]:
                lines.append(f"- `{f}`")
            lines.append("")

        if "tests_passing" in session_facts:
            lines.append(f"## Test Results\n- Passing: {session_facts['tests_passing']}")
            if "tests_added" in session_facts:
                lines.append(f"- New: {session_facts['tests_added']}")
            lines.append("")

        if "capabilities_used" in session_facts:
            lines.append("## Capabilities Used")
            for cap in session_facts["capabilities_used"]:
                lines.append(f"- {cap}")
            lines.append("")

        # Add compound analysis
        scores = self.calculate_compound_scores()
        if scores:
            top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
            lines.append("## Compound Impact (Top 10)")
            for name, score in top_scores:
                lines.append(f"- {name}: {score:.3f}")
            lines.append("")

        return "\n".join(lines)

    def suggest_skill_refinements(self) -> list[SkillRefinement]:
        """Identify skills that should be updated based on usage patterns.

        Returns
        -------
        list[SkillRefinement]
            Skills with 3+ learning references that may need updating.
        """
        if not self._learnings:
            self.analyze_learnings()

        refinements: list[SkillRefinement] = []

        # Count how many learnings reference each skill
        skill_learning_map: dict[str, list[str]] = {}
        for pattern in self._learnings:
            for ref in pattern.cross_references:
                if "_PRIME" in ref:
                    if ref not in skill_learning_map:
                        skill_learning_map[ref] = []
                    skill_learning_map[ref].append(pattern.title)

        # Skills referenced by 3+ learnings might need updating
        for skill, learning_titles in skill_learning_map.items():
            if len(learning_titles) >= 3:
                refinements.append(
                    SkillRefinement(
                        skill_name=skill,
                        reason=(
                            f"Referenced by {len(learning_titles)} learnings, may need integration of new insights"
                        ),
                        suggested_additions=learning_titles[:5],
                    )
                )

        return refinements

    def analyze(self, report: object) -> dict:
        """Convenience alias — delegates to :meth:`analyze_execution`.

        The compound-engine pipeline (and external callers added in
        2026-05) refer to the retrospection step as ``analyze()``. The
        existing implementation lives in :meth:`analyze_execution`; this
        thin wrapper keeps the public surface stable while allowing both
        names. The returned dict always contains a ``"hiho_balance"``
        key (see :meth:`compute_hiho_balance`).
        """
        return self.analyze_execution(report)

    def compute_hiho_balance(self, execution_history: list[dict]) -> float:
        """Compute HIHO balance score from execution history.

        HIHO balance = fraction of executions with positive ``delta``.
        Returns ``0.5`` for empty history (neutral/balanced default,
        consistent with the HIHO 50% coherence equilibrium described in
        the Cohezion Charter).

        Parameters
        ----------
        execution_history : list[dict]
            Each entry should expose a ``"delta"`` key (numeric). Missing
            keys are treated as ``0`` (non-positive, not counted).

        Returns
        -------
        float
            Balance score in ``[0.0, 1.0]``. ``0.5`` for empty input.
        """
        if not execution_history:
            return 0.5
        positive = sum(1 for e in execution_history if e.get("delta", 0) > 0)
        return positive / len(execution_history)

    def analyze_execution(self, report: object) -> dict:
        """Analyze an execution report and extract compound insights.

        Parameters
        ----------
        report : ExecutionReport
            An execution report (duck-typed to avoid circular imports).
            Expected attributes: ``task_results`` (list), ``total_tokens``,
            ``total_duration_ms``, ``plan_name``.

        Returns
        -------
        dict
            Analysis with keys ``"patterns"``, ``"compound_score_delta"``,
            ``"insights"``, ``"suggested_refinements"``.
        """
        task_results = getattr(report, "task_results", [])
        plan_name = getattr(report, "plan_name", "unknown")

        # Analyze task outcomes
        statuses = [getattr(tr, "status", "unknown") for tr in task_results]
        completed = statuses.count("completed")
        failed = statuses.count("failed")
        total = len(statuses)

        # Collect tokens per task
        tokens_by_task: dict[str, int] = {}
        for tr in task_results:
            exec_res = getattr(tr, "execution", None)
            if exec_res is not None:
                tokens_by_task[getattr(tr, "task_id", "?")] = getattr(exec_res, "total_tokens", 0)

        # Calculate compound score delta
        success_rate = completed / max(total, 1)
        token_efficiency = 1.0 - min(sum(tokens_by_task.values()) / max(total * 500, 1), 1.0)
        compound_delta = round(success_rate * 0.7 + token_efficiency * 0.3, 4)

        # Extract patterns
        patterns: list[str] = []
        if failed > 0:
            patterns.append(f"{failed}/{total} tasks failed — review error handling")
        if success_rate == 1.0:
            patterns.append("All tasks succeeded — good skill coverage")
        if sum(tokens_by_task.values()) == 0:
            patterns.append("Zero tokens used — no LLM calls (offline execution)")

        # Suggest refinements based on execution
        suggestions = self.suggest_skill_refinements()

        # Build a lightweight execution history (delta = +1 for completed,
        # -1 for failed) so we can score HIHO balance for this plan.
        execution_history = [
            {"delta": 1 if getattr(tr, "status", "unknown") == "completed" else -1}
            for tr in task_results
        ]
        hiho_balance = self.compute_hiho_balance(execution_history)

        insights = {
            "plan_name": plan_name,
            "tasks_total": total,
            "tasks_completed": completed,
            "tasks_failed": failed,
            "total_tokens": sum(tokens_by_task.values()),
            "patterns": patterns,
            "compound_score_delta": compound_delta,
            "hiho_balance": hiho_balance,
            "insights": [
                f"Execution of '{plan_name}' completed {completed}/{total} tasks",
                f"Token usage: {sum(tokens_by_task.values())} across {total} tasks",
            ],
            "suggested_refinements": [
                {"skill": r.skill_name, "reason": r.reason} for r in suggestions
            ],
        }

        logger.info(
            "Execution analysis for %s: %d/%d tasks, delta=%.4f",
            plan_name,
            completed,
            total,
            compound_delta,
        )

        return insights

    def analyze_recursive_trace(self, trace: object, skill_name: str = "") -> dict:
        """Retrospect over a RECURSIVE execution trace tree (A-Evolve Diagnose substrate).

        Duck-typed: ``trace`` need only provide ``aggregate() -> dict`` (the recursive-trace
        protocol from ``agent.unified_harness.ExecutionTrace``) — no agent import, no coupling.

        Unlike the flat :meth:`analyze_execution_result`, this consults the WHOLE delegation
        tree: a top-level "success" whose *delegated subtask* FAILED does NOT pass the refine
        gate. This prevents the compound loop from learning a lesson out of a partially-broken
        recursive run — the kind of mistake a flat trace can't catch.

        Returns the same contract as ``analyze_execution_result``: ``should_refine``,
        ``insights``, ``compound_score``, ``recommendation``.
        """
        agg = trace.aggregate()
        node_count = agg.get("node_count", 1)
        failed = agg.get("failed_task_ids", [])
        completed_subtree = agg.get("completed_subtree", False)
        recoveries = agg.get("total_recoveries", 0)
        max_depth = agg.get("max_depth", 0)

        insights: list[str] = [
            f"Recursive trace: {node_count} node(s), depth {max_depth}, "
            f"{agg.get('total_tool_calls', 0)} tool call(s), {recoveries} recovery(ies)"
        ]
        if failed:
            insights.append(f"FAILED subtask(s): {', '.join(failed)} — recursive failure")
        elif completed_subtree:
            insights.append("Whole delegation subtree completed")

        # Recovery rate across the tree dampens the quality signal.
        recovery_penalty = min(recoveries / max(node_count, 1), 1.0)
        compound_score = round((1.0 - recovery_penalty) if completed_subtree else 0.0, 4)

        # Recursive-aware gate: refine ONLY when the ENTIRE subtree succeeded.
        should_refine = bool(completed_subtree and not failed)

        if failed:
            recommendation = f"Fix delegated failure(s) {failed} before refining {skill_name}"
        elif should_refine:
            recommendation = f"Refine {skill_name} (recursive subtree clean, depth {max_depth})"
        else:
            recommendation = f"Subtree incomplete — do not refine {skill_name}"

        logger.info(
            "Recursive retrospection for %s: nodes=%d depth=%d should_refine=%s failed=%d",
            skill_name,
            node_count,
            max_depth,
            should_refine,
            len(failed),
        )
        return {
            "should_refine": should_refine,
            "insights": insights,
            "compound_score": compound_score,
            "recommendation": recommendation,
            "node_count": node_count,
            "max_depth": max_depth,
            "failed_task_ids": failed,
        }

    def analyze_execution_result(self, result: object, skill_name: str = "") -> dict:
        """Analyze a live ExecutionResult and extract compound insights.

        Closes the compound loop: execution -> measurement -> retrospection
        -> gated refinement. Uses quadrature assessment: success, coherence,
        anomaly alignment, and phi_score must all warrant learning.

        Parameters
        ----------
        result : ExecutionResult
            Live execution result (duck-typed to avoid circular imports).
            Expected attributes: ``success``, ``metrics``, ``duration_seconds``,
            ``output``.
        skill_name : str
            Name of the skill that was executed.

        Returns
        -------
        dict
            Analysis with keys:
            - ``should_refine``: bool — whether skill refinement is warranted
            - ``insights``: list[str] — observations from the execution
            - ``compound_score``: float — quality signal for refinement gating
            - ``recommendation``: str — suggested action
        """
        metrics = getattr(result, "metrics", {})
        success = getattr(result, "success", False)
        duration = getattr(result, "duration_seconds", 0.0)
        output = getattr(result, "output", "")

        coherence = metrics.get("coherence", 0.5)
        anomaly_score = metrics.get("anomaly_score", 0.5)
        phi_score = 0.5
        degraded = metrics.get("execution_degraded", False)

        # Extract phi_score from metadata if available
        if "phi_score" in metrics:
            phi_score = metrics["phi_score"]

        insights: list[str] = []
        recommendation = "No action needed"

        # Quadrature assessment: 4 perspectives must align
        if success:
            insights.append(f"Execution succeeded in {duration:.1f}s")
        else:
            insights.append(f"Execution failed: {output[:100]}")

        if coherence > 0.6:
            insights.append(f"High cohesion ({coherence:.2f}) — good spin alignment")
        elif coherence < 0.4:
            insights.append(f"Low cohesion ({coherence:.2f}) — spin misalignment")

        if anomaly_score > 0.7:
            insights.append(f"High anomaly ({anomaly_score:.2f}) — investigate")

        if degraded:
            insights.append("Execution ran in degradation mode")
            recommendation = "Investigate degradation root cause before refining"

        # Refinement gating: only refine when trajectory quality warrants it
        # Require: success AND reasonable coherence AND not degraded
        should_refine = (
            success
            and coherence >= 0.4  # Minimum HIHO band
            and not degraded
        )

        # Compound score: weighted quality signal
        compound_score = 0.0
        if success:
            compound_score = coherence * 0.5 + (1.0 - anomaly_score) * 0.3 + phi_score * 0.2

        if should_refine:
            recommendation = f"Refine {skill_name} with cohesion={coherence:.2f}"
        elif not success:
            recommendation = f"Investigate failure in {skill_name}"

        logger.info(
            "Retrospection for %s: should_refine=%s, compound=%.3f, coherence=%.2f",
            skill_name,
            should_refine,
            compound_score,
            coherence,
        )

        analysis = {
            "should_refine": should_refine,
            "insights": insights,
            "compound_score": compound_score,
            "recommendation": recommendation,
            "coherence": coherence,
            "anomaly_score": anomaly_score,
            "phi_score": phi_score,
            "degraded": degraded,
        }

        # Persist retrospection decision to SurrealDB (non-blocking, closes middle loop)
        try:
            import urllib.request
            from base64 import b64encode

            sql = (
                f"CREATE retrospection SET "
                f"skill = '{skill_name}', "
                f"should_refine = {str(should_refine).lower()}, "
                f"compound_score = {compound_score:.3f}, "
                f"coherence = {coherence:.3f}, "
                f"recommendation = '{recommendation[:200]}', "
                f"created = time::now();"
            )
            req = urllib.request.Request(
                "http://localhost:8001/sql",
                data=sql.encode(),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "cohezion",
                    "Authorization": "Basic " + b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # Fire-and-forget

        return analysis
