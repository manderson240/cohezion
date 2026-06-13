"""Recursive trace router for dynamically executing and routing workflows.

Recursively navigates workflow step hierarchies, uses past trajectory search
results to route to optimal agent tiers, and recursively escalates to higher
tiers on failures while building a structured execution trace tree.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.trajectory_search import TrajectorySearchEngine


logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a dynamic workflow, potentially containing sub-steps."""

    name: str
    description: str
    operation_type: str
    # Function to execute for this step. Accepts input arguments and return value of previous steps.
    execute_fn: Callable[[dict[str, Any]], Any] | None = None
    sub_steps: list[WorkflowStep] = field(default_factory=list)
    # Optional routing function for composite steps to dynamically select sub-steps.
    route_fn: Callable[[dict[str, Any]], str | list[str] | None] | None = None


@dataclass
class TraceNode:
    """Execution trace node for a workflow step, forming a recursive tree."""

    step_name: str
    description: str
    assigned_tier: str
    success: bool
    latency_ms: float
    cost_usd: float
    error: str | None = None
    children: list[TraceNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Overall outcome of running a recursive trace workflow."""

    success: bool
    output: Any
    trace_tree: TraceNode
    total_cost_usd: float
    total_latency_ms: float


class RecursiveTraceRouter:
    """Routes and executes dynamic workflows using recursive trace logic."""

    TIERS = ["npu", "igpu", "cpu", "haiku", "sonnet"]

    # Cost approximations for model tiers
    TIER_COSTS = {
        "npu": 0.0,
        "igpu": 0.0,
        "cpu": 0.0,
        "haiku": 0.001,
        "sonnet": 0.01,
    }

    def __init__(
        self,
        search_engine: TrajectorySearchEngine | None = None,
        default_tier: str = "npu",
    ) -> None:
        """Initialize the recursive trace router.

        Parameters
        ----------
        search_engine : TrajectorySearchEngine or None
            Engine to find past execution trajectories.
        default_tier : str
            Fallback tier if no past matches are found.
        """
        self.search_engine = search_engine
        self.default_tier = default_tier if default_tier in self.TIERS else "npu"

    def execute_workflow(
        self,
        step: WorkflowStep,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a workflow step recursively, routing and tracing each step.

        Parameters
        ----------
        step : WorkflowStep
            Root workflow step or step hierarchy to run.
        context : dict or None
            Initial context/inputs for the workflow.

        Returns
        -------
        WorkflowResult containing final output, success status, and trace tree.
        """
        if context is None:
            context = {}
        if "trace_history" not in context:
            context["trace_history"] = []
        start_time = time.time()
        trace_node = self._execute_recursive(step, context, start_tier_idx=0)
        end_time = time.time()

        total_latency = (end_time - start_time) * 1000
        total_cost = self._calculate_total_cost(trace_node)

        return WorkflowResult(
            success=trace_node.success,
            output=context.get("result"),
            trace_tree=trace_node,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
        )

    def _execute_recursive(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
        start_tier_idx: int = 0,
    ) -> TraceNode:
        """Recursively route and execute a workflow step."""
        # Case 1: Composite step (has sub-steps)
        if step.sub_steps:
            logger.info("Executing composite step: %s", step.name)
            children = []
            success = True
            error_msg = None
            start_time = time.time()

            steps_to_run = step.sub_steps
            if step.route_fn:
                try:
                    route_target = step.route_fn(context)
                    if route_target:
                        if isinstance(route_target, str):
                            route_targets = [route_target]
                        else:
                            route_targets = list(route_target)
                        steps_to_run = [sub for sub in step.sub_steps if sub.name in route_targets]
                        logger.info(
                            "Dynamic routing selected sub-steps: %s for step: %s",
                            [s.name for s in steps_to_run],
                            step.name,
                        )
                    else:
                        steps_to_run = []
                        logger.info("Dynamic routing skipped all sub-steps for step: %s", step.name)
                except Exception as e:
                    success = False
                    error_msg = f"Routing decision failed for composite step {step.name}: {e}"
                    steps_to_run = []

            if success:
                for sub in steps_to_run:
                    sub_trace = self._execute_recursive(sub, context, start_tier_idx=0)
                    children.append(sub_trace)
                    if not sub_trace.success:
                        success = False
                        error_msg = f"Sub-step {sub.name} failed: {sub_trace.error}"
                        break

            latency = (time.time() - start_time) * 1000
            return TraceNode(
                step_name=step.name,
                description=step.description,
                assigned_tier="composite",
                success=success,
                latency_ms=latency,
                cost_usd=0.0,
                error=error_msg,
                children=children,
            )

        # Case 2: Leaf step (executable)
        if not step.execute_fn:
            return TraceNode(
                step_name=step.name,
                description=step.description,
                assigned_tier="none",
                success=True,
                latency_ms=0.0,
                cost_usd=0.0,
                metadata={"reason": "No execution function provided"},
            )

        # Determine start tier using past trajectory search
        tier_idx = start_tier_idx
        if self.search_engine and tier_idx == 0:
            try:
                matches = self.search_engine.find_similar_trajectories(
                    task_description=step.description,
                    operation_type=step.operation_type,
                    top_k=1,
                )
                if matches and matches[0].success:
                    # In a real environment, the trajectory matches might contain model routing hints.
                    # We default to matching their historically successful tier if valid.
                    hist_guidance = matches[0].guidance.lower()
                    for idx, t in enumerate(self.TIERS):
                        if t in hist_guidance:
                            tier_idx = idx
                            logger.info(
                                "Found past successful trajectory for '%s'. Routing to: %s",
                                step.name,
                                t,
                            )
                            break
            except Exception as e:
                logger.warning("Error searching trajectories for step %s: %s", step.name, e)

        # Perform execution with recursive escalation fallback on failure
        current_tier = self.TIERS[tier_idx]
        start_time = time.time()
        success = False
        error_msg = None
        output = None
        children = []

        try:
            logger.info("Executing leaf step '%s' on tier '%s'", step.name, current_tier)
            # Inject current target tier into execution context
            context["target_tier"] = current_tier
            output = step.execute_fn(context)
            success = True
            context["result"] = output

            # Dynamic workflow step generation: if execute_fn returns WorkflowStep(s),
            # recursively execute them and nest their traces as children.
            if isinstance(output, WorkflowStep):
                child_trace = self._execute_recursive(output, context, start_tier_idx=0)
                children.append(child_trace)
                if not child_trace.success:
                    success = False
                    error_msg = f"Dynamic child step {output.name} failed: {child_trace.error}"
            elif isinstance(output, list) and all(isinstance(x, WorkflowStep) for x in output):
                for child_step in output:
                    child_trace = self._execute_recursive(child_step, context, start_tier_idx=0)
                    children.append(child_trace)
                    if not child_trace.success:
                        success = False
                        error_msg = (
                            f"Dynamic child step {child_step.name} failed: {child_trace.error}"
                        )
                        break
        except Exception as e:
            error_msg = str(e)
            logger.warning(
                "Execution of step '%s' failed on tier '%s': %s",
                step.name,
                current_tier,
                error_msg,
            )

        latency = (time.time() - start_time) * 1000
        cost = self.TIER_COSTS[current_tier]

        # Record to trace history in context
        trace_summary = {
            "step_name": step.name,
            "tier": current_tier,
            "success": success,
            "latency_ms": latency,
            "cost_usd": cost,
            "error": error_msg,
        }
        if "trace_history" not in context:
            context["trace_history"] = []
        context["trace_history"].append(trace_summary)

        # Recursive trace routing escalation
        if not success and tier_idx + 1 < len(self.TIERS):
            next_tier = self.TIERS[tier_idx + 1]
            logger.info(
                "Escalating step '%s' recursively from '%s' to '%s'",
                step.name,
                current_tier,
                next_tier,
            )
            # Recurse with escalated tier
            retry_trace = self._execute_recursive(step, context, start_tier_idx=tier_idx + 1)

            # Return a trace node showing the failure, with the escalated attempt nested
            return TraceNode(
                step_name=step.name,
                description=step.description,
                assigned_tier=current_tier,
                success=retry_trace.success,
                latency_ms=latency,
                cost_usd=cost,
                error=error_msg,
                children=[retry_trace, *children],
            )

        return TraceNode(
            step_name=step.name,
            description=step.description,
            assigned_tier=current_tier,
            success=success,
            latency_ms=latency,
            cost_usd=cost,
            error=error_msg,
            children=children,
        )

    def _calculate_total_cost(self, node: TraceNode) -> float:
        """Recursively calculate the total cost of a trace tree."""
        cost = node.cost_usd
        for child in node.children:
            cost += self._calculate_total_cost(child)
        return cost
