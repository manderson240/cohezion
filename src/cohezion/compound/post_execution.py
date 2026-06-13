"""Post-execution orchestration for CompoundExecutor.

Extracted from executor.py (originally 643 lines, Steps 5–10) to reduce
cognitive load.  All methods are non-blocking: failures are logged and
swallowed so the execution result is never lost.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.executor import CompoundExecutor


logger = logging.getLogger(__name__)


class PostExecutionOrchestrator:
    """Handles everything that happens *after* a task has run.

    Anomaly detection, skill refinement, metrics recording, journey tracking,
    universe bridge, DRR gates, autoresearch dispatch, geometric/bioelectric
    enrichment, prompt artifact persistence, and mycelium learning capture.
    """

    def __init__(self, executor: "CompoundExecutor"):
        self._ex = executor

    async def run(
        self,
        *,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
        experiment_path: str,
        decision_paths: list[str],
        task_description: str,
        skill_name: str,
        operation_type: str,
        project: str,
        parsed_request: Any,
        universe_journey_id: str | None,
        _task_profile: Any,
        _context_budget: Any,
    ) -> list[str]:
        """Run the full post-execution pipeline.

        Returns the augmented *decision_paths* list (may contain new vault
        paths from inflection points, pattern extraction, etc.).
        """
        # --- Step 5: Detect anomalies ---
        try:
            from cohezion.compound.inflection_detector import Severity

            temp_result = self._make_temp_result(
                success=success,
                output=output,
                metrics=metrics,
                duration_seconds=duration_seconds,
                token_metrics=token_metrics,
            )
            anomaly = self._ex.inflection_detector.detect_anomaly(temp_result)
            metrics["anomaly_severity"] = anomaly.severity.value
            metrics["anomaly_score"] = anomaly.score
            if anomaly.severity == Severity.CRITICAL:
                logger.warning("Critical inflection point: %s issues", len(anomaly.issues))
                try:
                    dp = self._ex.log_inflection_point(
                        title=f"Critical anomaly in {skill_name}",
                        context=f"Task: {task_description}\nIssues: {'; '.join(anomaly.issues)}",
                        decision="Re-execution recommended",
                        rationale=anomaly.recommendations[0] if anomaly.recommendations else "",
                        project=project,
                    )
                    if dp:
                        decision_paths.append(dp)
                except Exception as e:
                    logger.debug("Failed to log inflection point: %s", e)
        except Exception as e:
            logger.debug("Anomaly detection failed: %s", e, exc_info=True)

        # --- Step 5.5: Alignment analysis ---
        if self._ex._enable_alignment_analysis and self._ex.alignment_analyzer and parsed_request:
            try:
                self._run_alignment_analysis(
                    parsed_request=parsed_request,
                    success=success,
                    output=output,
                    metrics=metrics,
                    duration_seconds=duration_seconds,
                    token_metrics=token_metrics,
                    task_description=task_description,
                    operation_type=operation_type,
                    project=project,
                    decision_paths=decision_paths,
                )
            except Exception as e:
                logger.debug("Alignment analysis failed: %s", e, exc_info=True)

        # --- Step 5.8: Compute coherence ---
        self._compute_coherence(metrics)

        # --- Step 5.85: V-Model DRR gate ---
        self._run_drr_gate(metrics, skill_name, task_description)

        # --- Step 5.9: Natural capital valuation ---
        self._run_natural_capital(metrics)

        # --- Step 5.91: Autoresearch dispatch ---
        self._run_autoresearch(task_description, metrics)

        # --- Step 6: Pattern extraction (skip in degradation mode) ---
        if success and experiment_path and not self._ex._degradation_mode:
            try:
                pattern_path = self._ex.logger.extract_execution_pattern(
                    source_path=experiment_path,
                    pattern_name=f"{skill_name}_{operation_type}_success",
                    description=f"Success pattern for {skill_name} {operation_type}: {task_description[:100]}",
                    code_example=f"Result metrics: {json.dumps(metrics, indent=2)}",
                    domain="compound-engineering",
                )
                if pattern_path:
                    decision_paths.append(pattern_path)
            except Exception as e:
                logger.warning("Pattern extraction failed: %s", e, exc_info=True)

        # --- Step 7.3: Retrospection ---
        should_refine = self._run_retrospection(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            token_metrics=token_metrics,
            skill_name=skill_name,
        )

        # --- Step 7: Skill refinement (gated by retrospection + DRR) ---
        drr_passed = metrics.get("drr_passed", True)
        if not drr_passed:
            should_refine = False
            logger.info(
                "Skill refinement blocked: DRR gate failed (%s)", metrics.get("drr_gate", "?")
            )
        if success and self._ex.skill_refiner and should_refine:
            try:
                exec_result = {
                    "success": success,
                    "output": output,
                    "metrics": metrics,
                    "duration_seconds": duration_seconds,
                    "token_metrics": token_metrics,
                }
                refined_path = self._ex.skill_refiner.refine(
                    skill_name=skill_name,
                    operation_type=operation_type,
                    execution_result=exec_result,
                    patterns_extracted=decision_paths,
                )
                if refined_path:
                    logger.info("Skill refined: %s", refined_path)
                    decision_paths.append(refined_path)
            except Exception as e:
                logger.debug("Skill refinement failed: %s", e, exc_info=True)

        # --- Step 7.4: Skill health tracking ---
        self._run_skill_health(skill_name, success, token_metrics, metrics)

        # --- Step 7.5: Degradation detection ---
        self._run_degradation(
            metrics,
            duration_seconds,
            token_metrics,
            task_description,
            skill_name,
            project,
            decision_paths,
        )

        # --- Step 7.6: Geometric latent mapping ---
        self._run_geometric_mapping(metrics, task_description, project, decision_paths)

        # --- Step 7.7: Bioelectric coherence ---
        self._run_bioelectric(metrics)

        # --- Step 7.7b: Model quality recording ---
        self._run_model_quality(metrics, duration_seconds, token_metrics)

        # --- Step 8: Metrics recording ---
        self._run_metrics_collection(skill_name, success, duration_seconds, token_metrics)

        # --- Step 9: Journey tracking ---
        journey_point_tracked = self._run_journey_tracking(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            token_metrics=token_metrics,
            task_description=task_description,
            operation_type=operation_type,
            skill_name=skill_name,
        )

        # --- Step 9.1: Universe snapshot ---
        self._run_universe_snapshot(metrics)

        # --- Step 9.5: Universe bridge point ---
        self._run_universe_bridge_point(universe_journey_id, journey_point_tracked, skill_name)

        # --- Step 10: Complete universe journey ---
        self._run_complete_universe_journey(universe_journey_id, success, metrics, output)

        # --- Step 10.5: Ouroboros bridge ---
        self._run_ouroboros_bridge(metrics, task_description, skill_name)

        # --- Step 10.6: Mycelium learning capture ---
        self._run_mycelium(success, skill_name, task_description)

        # --- Step 10.7: Prompt artifact persistence ---
        self._run_prompt_artifact_persistence(task_description, output, token_metrics, metrics)

        # --- Step 10.9: Context policy outcome ---
        self._run_context_policy_outcome(_task_profile, _context_budget, success, metrics)

        return decision_paths

    # =====================================================================
    # Helper factories
    # =====================================================================

    def _make_temp_result(
        self,
        *,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
    ):
        from cohezion.compound.executor import ExecutionResult

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            token_metrics=token_metrics,
        )

    # =====================================================================
    # Step runners
    # =====================================================================

    def _run_alignment_analysis(
        self,
        *,
        parsed_request,
        success,
        output,
        metrics,
        duration_seconds,
        token_metrics,
        task_description,
        operation_type,
        project,
        decision_paths,
    ):
        from cohezion.compound.inflection_detector import AnomalyDetection, Severity

        temp_result = self._make_temp_result(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            token_metrics=token_metrics,
        )
        anomaly_analysis = None
        if "anomaly_severity" in metrics:
            severity_enum = Severity(metrics.get("anomaly_severity", "info"))
            anomaly_analysis = AnomalyDetection(
                severity=severity_enum,
                score=metrics.get("anomaly_score", 0.0),
                issues=metrics.get("anomaly_issues", []),
                recommendations=metrics.get("anomaly_recommendations", []),
                should_reexecute=False,
            )
        alignment = self._ex.alignment_analyzer.analyze_alignment(
            parsed_request, temp_result, operation_type, anomaly_analysis
        )
        if alignment.misalignment_score > 0.3:
            vault_path = self._ex.alignment_analyzer.log_alignment_to_vault(
                parsed_request, alignment, project
            )
            if vault_path:
                decision_paths.append(vault_path)
                logger.debug("Logged alignment analysis: %s", vault_path)
        metrics["alignment"] = {
            "misalignment_score": alignment.misalignment_score,
            "intent_match": alignment.intent_match_score,
            "constraint_satisfaction": alignment.constraint_satisfaction,
            "criteria_satisfaction": alignment.criteria_satisfaction,
            "violations_count": len(alignment.violations),
            "failures_count": len(alignment.failures),
            "issues_count": len(alignment.issues),
            "should_retry": alignment.should_retry,
        }
        logger.debug("Alignment analysis: %s", metrics["alignment"])

    def _compute_coherence(self, metrics: dict[str, Any]) -> None:
        cohesion_components: list[float] = []
        cohesion_components.append(0.7 if metrics.get("success", False) else 0.2)
        cohesion_components.append(1.0 - metrics.get("anomaly_score", 0.0))
        alignment_data = metrics.get("alignment", {})
        if alignment_data:
            cohesion_components.append(alignment_data.get("intent_match", 0.5))
        metrics["coherence"] = sum(cohesion_components) / len(cohesion_components)

    def _run_drr_gate(
        self, metrics: dict[str, Any], skill_name: str, task_description: str
    ) -> None:
        if self._ex._drr_generator:
            try:
                from cohezion.compound.design_review_report import GateLevel

                drr = self._ex._drr_generator.generate(
                    gate=GateLevel.IMPLEMENTATION,
                    session_id=self._ex._drr_session_id or "unknown",
                    left_artifact=skill_name or "unknown",
                    right_artifact=task_description[:100] if task_description else "unknown",
                )
                metrics["drr_gate"] = drr.gate.value
                metrics["drr_passed"] = drr.passed
                metrics["drr_findings"] = len(drr.findings)
                if not drr.passed:
                    logger.warning("DRR-%s FAILED: %s", drr.gate.value, drr.summary)
            except Exception:
                logger.debug("DRR gate check failed", exc_info=True)

    def _run_natural_capital(self, metrics: dict[str, Any]) -> None:
        try:
            import numpy as np

            from cohezion.physics.natural_capital import NaturalCapitalValuation

            ncv = NaturalCapitalValuation()
            coherence_val = metrics.get("coherence", 0.5)
            state_12d = np.full(12, coherence_val)
            nc = ncv.evaluate(
                state_12d=state_12d,
                coherence=coherence_val,
                connectivity=0.5,
                gauge_curvature=0.0,
                spore_density=0.5,
            )
            metrics["natural_capital"] = nc.total_natural_capital
            metrics["habitat_quality"] = nc.habitat_quality
            metrics["coherence"] = metrics["coherence"] * 0.9 + nc.habitat_quality * 0.1
        except Exception:
            pass

    def _run_autoresearch(self, task_description: str, metrics: dict[str, Any]) -> None:
        keywords = {"train", "optimize", "research", "experiment", "tune", "improve loss"}
        if not any(kw in task_description.lower() for kw in keywords):
            return
        try:
            from cohezion.research.autoresearch_driver import AutoresearchDriver

            target = (
                "jepa"
                if "jepa" in task_description.lower()
                else "flume_vae"
                if "flume" in task_description.lower()
                else "rl_ppo"
                if any(w in task_description.lower() for w in ("rl", "ppo", "reward"))
                else "jepa"
            )
            driver = AutoresearchDriver(target=target, budget_seconds=60)
            asyncio.ensure_future(driver.run_loop(n_iterations=1))
            metrics["autoresearch_target"] = target
        except Exception:
            pass

    def _run_retrospection(
        self,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
        skill_name: str,
    ) -> bool:
        should_refine = True
        if self._ex._retrospection_engine:
            try:
                temp_result = self._make_temp_result(
                    success=success,
                    output=output,
                    metrics=metrics,
                    duration_seconds=duration_seconds,
                    token_metrics=token_metrics,
                )
                ctx = self._ex._retrospection_engine.analyze_execution_result(
                    temp_result, skill_name
                )
                should_refine = ctx.get("should_refine", True) if ctx is not None else True
                if ctx and ctx.get("insights"):
                    metrics["retrospection_insights"] = ctx["insights"]
            except Exception as e:
                logger.debug("Retrospection failed: %s", e, exc_info=True)
        return should_refine

    def _run_skill_health(
        self,
        skill_name: str,
        success: bool,
        token_metrics: dict[str, Any] | None,
        metrics: dict[str, Any],
    ) -> None:
        if not self._ex._skill_health_tracker:
            return
        try:
            tokens = token_metrics.get("tokens_used", 0) if token_metrics else 0
            self._ex._skill_health_tracker.record_usage(
                skill_name=skill_name,
                success=success,
                tokens_used=tokens,
                quality_score=metrics.get("coherence", 0.0),
            )
        except Exception as e:
            logger.warning("Skill health tracking failed: %s", e)

    def _run_degradation(
        self,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
        task_description: str,
        skill_name: str,
        project: str,
        decision_paths: list[str],
    ) -> None:
        coherence_val = metrics.get("coherence", 0.5)
        if 0.4 <= coherence_val <= 0.6 and self._ex._degradation_mode:
            logger.info(
                "Coherence returned to HIHO band (%.2f), exiting degradation mode", coherence_val
            )
            self._ex._degradation_mode = False

        if not self._ex._degradation_detector:
            return
        try:
            degr = {
                "combined_hit_rate": 0.0,
                "tokens_per_second": 0.0,
                "mean_coherence": coherence_val,
                "elapsed_seconds": duration_seconds,
                "success_rate": 1.0 if metrics.get("success", False) else 0.0,
            }
            if token_metrics:
                degr["combined_hit_rate"] = token_metrics.get(
                    "cache_hit_rate", token_metrics.get("combined_hit_rate", 0.0)
                )
                degr["tokens_per_second"] = token_metrics.get("tokens_per_second", 0.0)
            alerts = self._ex._degradation_detector.check_degradation(degr)
            if alerts:
                metrics["degradation_alerts"] = len(alerts)
                critical_alerts = [a for a in alerts if a.severity.value == "CRITICAL"]
                if critical_alerts:
                    self._ex._degradation_mode = True
                    metrics["execution_degraded"] = True
                    logger.warning(
                        "Entering degradation mode: %d CRITICAL alerts", len(critical_alerts)
                    )
                for alert in critical_alerts:
                    try:
                        dp = self._ex.log_inflection_point(
                            title=f"Degradation: {alert.metric}",
                            context=f"Task: {task_description}\n{alert.message}",
                            decision="Investigate degradation",
                            rationale=(
                                f"Current: {alert.current_value:.3f},"
                                f" Baseline: {alert.baseline_value:.3f},"
                                f" Threshold: {alert.threshold:.3f}"
                            ),
                            project=project,
                        )
                        if dp:
                            decision_paths.append(dp)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Degradation detection failed: %s", e)

    def _run_geometric_mapping(
        self,
        metrics: dict[str, Any],
        task_description: str,
        project: str,
        decision_paths: list[str],
    ) -> None:
        if not self._ex.geometric_bridge:
            return
        try:
            import torch

            latent_vec = metrics.get("latent_vector")
            if latent_vec is None:
                latent_vec = torch.randn(256)
            if not isinstance(latent_vec, torch.Tensor):
                latent_vec = torch.tensor(latent_vec).float()
            regime = self._ex.geometric_bridge.map_to_regime(latent_vec)
            coords = self._ex.geometric_bridge.project_to_coordinates(latent_vec)
            metrics["topological_regime"] = regime
            metrics["mereon_coords"] = coords.tolist()
            logger.debug("Latent state mapped to %s regime", regime)
            if regime in {"A", "C", "Inner"}:
                dp = self._ex.log_inflection_point(
                    title=f"Regime Transition: {regime}",
                    context=f"Task: {task_description}\nSymmetry: {regime}",
                    decision="Distillation trigger",
                    rationale=f"Latent state aligned with {regime} sector of Mereon manifold",
                    project=project,
                )
                if dp:
                    decision_paths.append(dp)
        except Exception as e:
            logger.debug("Geometric latent mapping failed: %s", e)

    def _run_bioelectric(self, metrics: dict[str, Any]) -> None:
        try:
            import numpy as np

            from cohezion.physics.bioelectric_model import BioelectricNetwork

            bio_net = BioelectricNetwork(n_cells=8)
            bio_net.set_uniform_conductance(0.3)
            bio_net.v_mem = np.full(8, metrics.get("coherence", 0.5) * 2 - 1)
            bio_net.simulate(n_steps=10, dt=0.01)
            metrics["bioelectric_coherence"] = float(bio_net.coherence())
            metrics["bioelectric_percolated"] = bio_net.percolation_analysis().is_percolated
        except Exception:
            pass

    def _run_model_quality(
        self,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
    ) -> None:
        if not self._ex._model_quality_classifier:
            return
        try:
            model_name = "unknown"
            tokens_used = 0
            if token_metrics:
                model_name = token_metrics.get("model", "unknown")
                tokens_used = token_metrics.get("tokens_used", 0)
            self._ex._model_quality_classifier.add_execution(
                model=model_name,
                coherence=metrics.get("coherence", 0.5),
                success=metrics.get("success", False),
                tokens_used=tokens_used,
                duration=duration_seconds,
            )
        except Exception as e:
            logger.debug("Model quality recording failed: %s", e)

    def _run_metrics_collection(
        self,
        skill_name: str,
        success: bool,
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
    ) -> None:
        if not self._ex._metrics_collector:
            return
        try:
            tokens = token_metrics.get("tokens_used", 0) if token_metrics else 0
            model = token_metrics.get("model", "") if token_metrics else ""
            self._ex._metrics_collector.record_execution(
                skill_name=skill_name,
                success=success,
                tokens_used=tokens,
                duration_ms=duration_seconds * 1000,
                model_used=model,
            )
        except Exception as e:
            logger.debug("Metrics recording failed: %s", e)

    def _run_journey_tracking(
        self,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        duration_seconds: float,
        token_metrics: dict[str, Any] | None,
        task_description: str,
        operation_type: str,
        skill_name: str,
    ) -> bool:
        if not self._ex._journey_tracker:
            return False
        try:
            temp_result = self._make_temp_result(
                success=success,
                output=output,
                metrics=metrics,
                duration_seconds=duration_seconds,
                token_metrics=token_metrics,
            )
            point = self._ex._journey_tracker.track_execution(
                temp_result, task_description, operation_type
            )
            if point and point.metadata:
                metrics["phi_score"] = point.metadata.get("phi_score", 0.0)
            if self._ex._journey_persistence and point:
                try:
                    point_data = {
                        "coherence": point.coherence,
                        "efficiency": point.efficiency,
                        "operation_type": point.operation_type,
                        "task_description": point.task_description[:200],
                        "timestamp": point.timestamp,
                    }
                    if point.metadata:
                        point_data["metadata"] = point.metadata
                    _id = f"exec_{int(time.time())}"
                    try:
                        asyncio.get_running_loop()
                        asyncio.ensure_future(
                            self._ex._journey_persistence.save_trajectory_point(_id, point_data)
                        )
                    except RuntimeError:
                        asyncio.run(
                            self._ex._journey_persistence.save_trajectory_point(_id, point_data)
                        )
                except Exception as e:
                    logger.debug("Journey persistence failed: %s", e)
            return True
        except Exception as e:
            logger.debug("Journey tracking failed: %s", e)
            return False

    def _run_universe_snapshot(self, metrics: dict[str, Any]) -> None:
        try:
            from cohezion.persistence.genesis_persistence import persist_universe_snapshot

            snap = persist_universe_snapshot(
                tick=int(time.time()),
                global_coherence=metrics.get("coherence", 0.5),
                symmetry_group="SU2",
                temperature=float(metrics.get("temperature", 0.5)),
                n_agents=1,
            )
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(snap)
            except RuntimeError:
                asyncio.run(snap)
        except Exception:
            pass

    def _run_universe_bridge_point(
        self,
        universe_journey_id: str | None,
        journey_point_tracked: bool,
        skill_name: str,
    ) -> None:
        if not self._ex._universe_bridge or not universe_journey_id or not journey_point_tracked:
            return
        try:
            if self._ex._journey_tracker:
                last_point = self._ex._journey_tracker.get_last_point()
                if last_point:
                    self._ex._universe_bridge.add_point(
                        universe_journey_id,
                        last_point,
                        step_number=self._ex._journey_tracker.get_recent_point_count(),
                        action=skill_name,
                    )
        except Exception as e:
            logger.debug("Universe bridge point failed: %s", e)

    def _run_complete_universe_journey(
        self,
        universe_journey_id: str | None,
        success: bool,
        metrics: dict[str, Any],
        output: str,
    ) -> None:
        if not self._ex._universe_bridge or not universe_journey_id:
            return
        try:
            phi = metrics.get("phi_score", 0.0)
            self._ex._universe_bridge.complete_journey(
                universe_journey_id,
                success=success,
                phi_score=phi,
                output=output[:500],
            )
        except Exception as e:
            logger.debug("Universe bridge completion failed: %s", e)

    def _run_ouroboros_bridge(
        self, metrics: dict[str, Any], task_description: str, skill_name: str
    ) -> None:
        try:
            from cohezion.physics.ouroboros_bridge import OuroborosBridge

            if not hasattr(self._ex, "_ouroboros_bridge_instance"):
                self._ex._ouroboros_bridge_instance = OuroborosBridge()
            drop = abs(metrics.get("coherence", 0.5) - 0.5)
            if drop > 0.3:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        logger.debug("Ouroboros: coherence drop %.3f (async deferred)", drop)
                    else:
                        loop.run_until_complete(
                            self._ex._ouroboros_bridge_instance.check_coherence(
                                drop, task_id=skill_name
                            )
                        )
                except RuntimeError:
                    pass
        except Exception:
            pass

    def _run_mycelium(self, success: bool, skill_name: str, task_description: str) -> None:
        if not success:
            return
        try:
            from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry

            if not hasattr(self._ex, "_mycelium_registry"):
                # Shared singleton so synthesized skills are visible to the
                # mycelium API reader (closes the recursion loop). Matches the
                # executor Step 10.6 writer path.
                self._ex._mycelium_registry = MyceliumRegistry.get_instance()
            entry = JournalEntry(
                entry_id=f"exec_{int(time.time())}_{skill_name}",
                content=f"Executed {skill_name}: {task_description[:200]}",
                domain="pattern",
            )
            self._ex._mycelium_registry.ingest_entry(entry)
            if (
                hasattr(self._ex._mycelium_registry, "_entries")
                and len(self._ex._mycelium_registry._entries) % 10 == 0
            ):
                try:
                    report = self._ex._mycelium_registry.run_audit()
                    logger.info(
                        "Mycelium audit: %d skills synthesized",
                        getattr(report, "skills_synthesized", 0) if report else 0,
                    )
                except Exception:
                    logger.debug("Mycelium audit failed")
        except Exception:
            pass

    def _run_prompt_artifact_persistence(
        self,
        task_description: str,
        output: str,
        token_metrics: dict[str, Any] | None,
        metrics: dict[str, Any],
    ) -> None:
        try:
            from cohezion.persistence.genesis_persistence import persist_prompt_artifact

            _artifact_coro = persist_prompt_artifact(
                prompt_text=task_description,
                response_text=output[:2000],
                model_id=token_metrics.get("model", "unknown") if token_metrics else "unknown",
                confidence=metrics.get("coherence", 0.5),
                latency_ms=metrics.get("duration_seconds", 0.0) * 1000,
            )
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(_artifact_coro)
            except RuntimeError:
                asyncio.run(_artifact_coro)
        except Exception:
            pass

    def _run_context_policy_outcome(
        self,
        _task_profile,
        _context_budget,
        success: bool,
        metrics: dict[str, Any],
    ) -> None:
        if _task_profile is None or _context_budget is None or not self._ex._context_policy:
            return
        try:
            self._ex._context_policy.record_outcome(
                profile=_task_profile,
                budget=_context_budget,
                execution_success=success,
                coherence_final=metrics.get("coherence", 0.5),
            )
        except Exception as e:
            logger.debug("Context policy outcome recording failed: %s", e)
