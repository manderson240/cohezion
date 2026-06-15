"""Unit tests for RecursiveTraceRouter and dynamic trace routing workflows."""

from unittest.mock import MagicMock

from cohezion.compound.recursive_trace_router import (
    RecursiveTraceRouter,
    WorkflowStep,
)
from cohezion.compound.trajectory_search import TrajectorySearchResult


def test_basic_leaf_step_execution():
    """Verify that a single leaf step executes successfully and returns trace details."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    def mock_execute(ctx):
        ctx["data"] = "success_val"
        return "step_ok"

    step = WorkflowStep(
        name="test_step",
        description="Verify local model availability",
        operation_type="analyze",
        execute_fn=mock_execute,
    )

    ctx = {}
    result = router.execute_workflow(step, ctx)

    assert result.success is True
    assert result.output == "step_ok"
    assert ctx["data"] == "success_val"
    assert result.trace_tree.step_name == "test_step"
    assert result.trace_tree.assigned_tier == "npu"
    assert result.trace_tree.success is True
    assert result.trace_tree.error is None


def test_composite_workflow_steps():
    """Verify that composite steps run all sub-steps in sequence."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    calls = []

    def step_1_fn(ctx):
        calls.append(1)
        return "one"

    def step_2_fn(ctx):
        calls.append(2)
        return "two"

    step1 = WorkflowStep("step_1", "Desc 1", "analyze", step_1_fn)
    step2 = WorkflowStep("step_2", "Desc 2", "generate", step_2_fn)

    parent_step = WorkflowStep(
        name="parent_composite",
        description="Run multi-step pipeline",
        operation_type="pipeline",
        sub_steps=[step1, step2],
    )

    result = router.execute_workflow(parent_step)

    assert result.success is True
    assert result.output == "two"  # final result gets stored in context
    assert calls == [1, 2]
    assert result.trace_tree.step_name == "parent_composite"
    assert len(result.trace_tree.children) == 2
    assert result.trace_tree.children[0].step_name == "step_1"
    assert result.trace_tree.children[1].step_name == "step_2"


def test_trajectory_guided_routing():
    """Verify that search engine results guide initial model tier selection."""
    mock_search = MagicMock()
    # Mock finding a past successful trajectory suggesting "cpu"
    mock_search.find_similar_trajectories.return_value = [
        TrajectorySearchResult(
            task_description="Analyze dataset",
            operation_type="analyze",
            coherence=0.9,
            phi_score=0.8,
            trajectory_smoothness=0.9,
            trajectory_convergence=0.9,
            similarity_score=0.95,
            success=True,
            guidance="Past execution succeeded on cpu",
        )
    ]

    router = RecursiveTraceRouter(search_engine=mock_search)

    def mock_execute(ctx):
        return "ok"

    step = WorkflowStep(
        name="test_step",
        description="Analyze dataset",
        operation_type="analyze",
        execute_fn=mock_execute,
    )

    result = router.execute_workflow(step)
    assert result.success is True
    assert result.trace_tree.assigned_tier == "cpu"  # Routed to CPU based on trajectory search!
    mock_search.find_similar_trajectories.assert_called_once_with(
        task_description="Analyze dataset",
        operation_type="analyze",
        top_k=1,
    )


def test_recursive_escalation_on_failure():
    """Verify that failures trigger recursive escalation to higher capability tiers."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    # Force failure on npu and igpu, but succeed on cpu
    execution_attempts = []

    def mock_execute(ctx):
        tier = ctx.get("target_tier")
        execution_attempts.append(tier)
        if tier in ("npu", "igpu"):
            raise ValueError(f"OOM or quality gate fail on {tier}")
        return "recovered_on_cpu"

    step = WorkflowStep(
        name="failing_step",
        description="Perform deep reasoning",
        operation_type="reason",
        execute_fn=mock_execute,
    )

    result = router.execute_workflow(step)

    # Escalation should walk NPU -> iGPU -> CPU where it succeeds
    assert result.success is True
    assert result.output == "recovered_on_cpu"
    assert execution_attempts == ["npu", "igpu", "cpu"]

    # Trace tree check: should show NPU failed, nesting iGPU which failed, nesting CPU which succeeded
    npu_node = result.trace_tree
    assert npu_node.assigned_tier == "npu"
    assert npu_node.success is True  # Success overall (since escalation succeeded)
    assert npu_node.error == "OOM or quality gate fail on npu"
    assert len(npu_node.children) == 1

    igpu_node = npu_node.children[0]
    assert igpu_node.assigned_tier == "igpu"
    assert igpu_node.success is True
    assert igpu_node.error == "OOM or quality gate fail on igpu"
    assert len(igpu_node.children) == 1

    cpu_node = igpu_node.children[0]
    assert cpu_node.assigned_tier == "cpu"
    assert cpu_node.success is True
    assert cpu_node.error is None
    assert len(cpu_node.children) == 0


def test_dynamic_workflow_step_routing():
    """Verify that route_fn dynamically filters sub-steps of a composite step."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    executed = []

    step_a = WorkflowStep("step_a", "Desc A", "op", lambda ctx: executed.append("A"))
    step_b = WorkflowStep("step_b", "Desc B", "op", lambda ctx: executed.append("B"))

    def route_decision(ctx):
        # Dynamically route to step_b if route_to_b flag is set, otherwise step_a
        if ctx.get("route_to_b"):
            return "step_b"
        return "step_a"

    parent = WorkflowStep(
        name="composite_parent",
        description="Parent step",
        operation_type="op",
        sub_steps=[step_a, step_b],
        route_fn=route_decision,
    )

    # Scenario 1: route to A
    ctx = {"route_to_b": False}
    result = router.execute_workflow(parent, ctx)
    assert result.success is True
    assert executed == ["A"]
    assert len(result.trace_tree.children) == 1
    assert result.trace_tree.children[0].step_name == "step_a"

    # Scenario 2: route to B
    executed.clear()
    ctx = {"route_to_b": True}
    result = router.execute_workflow(parent, ctx)
    assert result.success is True
    assert executed == ["B"]
    assert len(result.trace_tree.children) == 1
    assert result.trace_tree.children[0].step_name == "step_b"


def test_dynamic_workflow_child_generation():
    """Verify that a step returning WorkflowStep(s) gets executed recursively."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    executed = []

    def make_dynamic_step(ctx):
        # Returns a dynamic step to be executed recursively
        child = WorkflowStep(
            name="dynamic_child",
            description="Generated dynamically",
            operation_type="op",
            execute_fn=lambda c: executed.append("child_run"),
        )
        return child

    parent = WorkflowStep(
        name="parent_step",
        description="Parent generating child",
        operation_type="op",
        execute_fn=make_dynamic_step,
    )

    result = router.execute_workflow(parent)
    assert result.success is True
    assert executed == ["child_run"]
    assert result.trace_tree.step_name == "parent_step"
    assert len(result.trace_tree.children) == 1
    assert result.trace_tree.children[0].step_name == "dynamic_child"


def test_trace_history_in_context():
    """Verify that execution trace history is recorded in context and accessible."""
    router = RecursiveTraceRouter(search_engine=None, default_tier="npu")

    def first_step_fn(ctx):
        ctx["val"] = 123
        return "first_ok"

    def second_step_fn(ctx):
        history = ctx.get("trace_history", [])
        if len(history) > 0 and history[0]["step_name"] == "first_step":
            ctx["verified"] = True
        return "second_ok"

    step1 = WorkflowStep("first_step", "Step 1", "op", first_step_fn)
    step2 = WorkflowStep("second_step", "Step 2", "op", second_step_fn)

    parent = WorkflowStep(
        name="pipeline",
        description="Pipeline",
        operation_type="op",
        sub_steps=[step1, step2],
    )

    ctx = {}
    result = router.execute_workflow(parent, ctx)

    assert result.success is True
    assert ctx.get("verified") is True
    assert len(ctx.get("trace_history", [])) == 2
    assert ctx["trace_history"][0]["step_name"] == "first_step"
    assert ctx["trace_history"][0]["success"] is True
    assert ctx["trace_history"][1]["step_name"] == "second_step"
