"""Compound feedback loop -- execute -> analyze -> refine -> (optionally) regenerate."""

from __future__ import annotations

import logging
import time

from cohezion.compound.executor import CompoundExecutor, get_executor
from cohezion.compound.models import CompoundCycleReport, CompoundCycleResult
from cohezion.compound.persistence import CompoundPersistence

logger = logging.getLogger(__name__)


class CompoundFeedbackLoop:
    """Execute PRIME skills and feed results through the compound loop.

    Parameters
    ----------
    executor : CompoundExecutor | None
        Pre-configured executor. Uses singleton if ``None``.
    persistence : CompoundPersistence | None
        Persistence backend. Creates default if ``None``.
    auto_regenerate : bool
        Whether to regenerate agent code after refinement.
    """

    def __init__(
        self,
        executor: CompoundExecutor | None = None,
        persistence: CompoundPersistence | None = None,
        auto_regenerate: bool = False,
    ) -> None:
        self._executor = executor
        self._persistence = persistence or CompoundPersistence()
        self._auto_regenerate = auto_regenerate

    @property
    def executor(self) -> CompoundExecutor:
        """Return the executor, falling back to the singleton."""
        if self._executor is None:
            self._executor = get_executor()
        return self._executor

    async def run_cycle(
        self,
        skill_name: str,
        input_text: str,
        model: str | None = None,
    ) -> CompoundCycleResult:
        """Run one complete feedback cycle.

        Steps:
        1. Execute skill via CompoundExecutor
        2. Analyze execution via RetrospectionEngine
        3. Generate supplementary suggestions from execution patterns
        4. Apply refinements via SkillRefiner
        5. Record metrics and persist

        Parameters
        ----------
        skill_name : str
            PRIME skill name.
        input_text : str
            Input text for execution.
        model : str | None
            Override model for all steps.

        Returns
        -------
        CompoundCycleResult
        """
        from cohezion.core.compound.retrospection import (
            RetrospectionEngine,
            SkillRefinement,
        )
        from cohezion.core.compound.skill_refiner import SkillRefiner

        t0 = time.monotonic()

        # 1. Execute
        exec_result = await self.executor.execute_skill(
            skill_name, input_text, model=model
        )

        # 2. Build a minimal report object for RetrospectionEngine
        report = _ExecutionReportProxy(
            plan_name=skill_name,
            task_results=[
                _TaskResultProxy(
                    task_id=f"step-{s['step_index']}",
                    status="completed" if s["tokens_used"] >= 0 else "failed",
                    execution=_ExecProxy(total_tokens=s["tokens_used"]),
                )
                for s in exec_result.steps
            ],
            total_tokens=exec_result.total_tokens,
            total_duration_ms=exec_result.total_duration_ms,
        )

        retro = RetrospectionEngine()
        analysis = retro.analyze_execution(report)
        compound_delta: float = analysis.get("compound_score_delta", 0.0)
        patterns: list[str] = analysis.get("patterns", [])

        # 3. Supplementary suggestions from execution patterns
        suggestions: list[SkillRefinement] = []
        if patterns:
            suggestion_texts: list[str] = []
            for p in patterns:
                if "failed" in p.lower():
                    suggestion_texts.append(f"Execution insight: {p}")
                elif "zero tokens" in p.lower():
                    suggestion_texts.append(
                        "Offline execution -- consider adding LLM verification step"
                    )
            if suggestion_texts:
                suggestions.append(
                    SkillRefinement(
                        skill_name=skill_name,
                        reason=(
                            f"Auto-refinement from compound cycle "
                            f"(delta={compound_delta:.4f})"
                        ),
                        suggested_additions=suggestion_texts,
                    )
                )

        # Also include retrospection-generated suggestions
        retro_suggestions = retro.suggest_skill_refinements()
        suggestions.extend(retro_suggestions)

        # 4. Apply refinements
        refinements_applied = 0
        version_before = ""
        version_after = ""
        if suggestions:
            refiner = SkillRefiner(auto_regenerate=self._auto_regenerate)
            results = refiner.refine_from_suggestions(suggestions)
            for r in results:
                if r.additions:
                    refinements_applied += 1
                    if r.skill_name.upper() == skill_name.upper():
                        version_before = r.version_before
                        version_after = r.version_after

        # 5. Record metrics
        try:
            from cohezion.compound.metrics import get_collector

            collector = get_collector()
            collector.record_execution(
                skill_name=skill_name,
                success=True,
                tokens_used=exec_result.total_tokens,
                duration_ms=exec_result.total_duration_ms,
            )
            if refinements_applied > 0:
                collector.record_refinement(
                    skill_name=skill_name,
                    version_before=version_before or "unknown",
                    version_after=version_after or "unknown",
                    learnings_added=refinements_applied,
                )
            collector.record_cycle(
                skill_name=skill_name,
                executions=1,
                refinements=refinements_applied,
                compound_score_delta=compound_delta,
                total_tokens=exec_result.total_tokens,
                total_duration_ms=exec_result.total_duration_ms,
            )
        except Exception:
            logger.debug("Metrics recording failed (non-critical)")

        # 6. Persist
        cycle_result = CompoundCycleResult(
            skill_name=skill_name,
            input_text=input_text,
            execution_output=exec_result.final_output,
            execution_tokens=exec_result.total_tokens,
            execution_duration_ms=exec_result.total_duration_ms,
            compound_score_delta=compound_delta,
            patterns=patterns,
            refinements_applied=refinements_applied,
            version_before=version_before,
            version_after=version_after,
            model_usage=exec_result.model_usage,
        )

        try:
            await self._persistence.save_cycle(skill_name, cycle_result.model_dump())
        except Exception:
            logger.debug("Persistence save failed (non-critical)")

        total_ms = (time.monotonic() - t0) * 1000.0
        logger.info(
            "Feedback cycle for %s: delta=%.4f, refinements=%d, %.1f ms",
            skill_name,
            compound_delta,
            refinements_applied,
            total_ms,
        )

        return cycle_result

    async def run_multi_cycle(
        self,
        skill_name: str,
        input_text: str,
        cycles: int = 3,
        model: str | None = None,
    ) -> CompoundCycleReport:
        """Run N feedback cycles, feeding output as context for the next.

        Parameters
        ----------
        skill_name : str
            PRIME skill name.
        input_text : str
            Initial input text.
        cycles : int
            Number of cycles to run.
        model : str | None
            Override model.

        Returns
        -------
        CompoundCycleReport
        """
        results: list[CompoundCycleResult] = []
        context = input_text

        for i in range(cycles):
            logger.info("Compound cycle %d/%d for %s", i + 1, cycles, skill_name)
            result = await self.run_cycle(skill_name, context, model=model)
            results.append(result)
            # Feed output as context for next cycle
            if result.execution_output:
                context = result.execution_output

        return CompoundCycleReport(
            skill_name=skill_name,
            cycles=results,
            total_cycles=len(results),
            total_tokens=sum(r.execution_tokens for r in results),
            total_duration_ms=sum(r.execution_duration_ms for r in results),
            total_refinements=sum(r.refinements_applied for r in results),
            final_compound_score_delta=(
                results[-1].compound_score_delta if results else 0.0
            ),
        )


class _ExecProxy:
    """Minimal proxy for ExecutionResult (avoids circular imports)."""

    def __init__(self, total_tokens: int = 0) -> None:
        self.total_tokens = total_tokens


class _TaskResultProxy:
    """Minimal proxy for TaskResult."""

    def __init__(
        self,
        task_id: str,
        status: str,
        execution: _ExecProxy | None = None,
    ) -> None:
        self.task_id = task_id
        self.status = status
        self.execution = execution


class _ExecutionReportProxy:
    """Minimal proxy for ExecutionReport."""

    def __init__(
        self,
        plan_name: str,
        task_results: list[_TaskResultProxy],
        total_tokens: int = 0,
        total_duration_ms: float = 0.0,
    ) -> None:
        self.plan_name = plan_name
        self.task_results = task_results
        self.total_tokens = total_tokens
        self.total_duration_ms = total_duration_ms
