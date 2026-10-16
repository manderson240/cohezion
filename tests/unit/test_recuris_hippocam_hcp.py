"""Unit tests for Recuris, Hippocam, and Harness Context Protocol (HCP) implementations.
===================================================================================
Tests:
- Recuris MemoryQuad, State-Grounded Invocation, and Trace Failure Localization
- Hippocam Nested Intent Stack, Janus operations, Precip consolidation, and Palim recall
- Macaron HCP contract generation, AST verification substrate, and ActionReceipts
"""

from cohezion.agi.recuris_memory import (
    CheckerPipeline,
    ExecutionTraceStep,
    ExperientialSkill,
    InvocationPolicy,
    MemoryComponent,
    MemoryQuad,
    TraceFailureLocalizer,
    ValidationGatedAdmission,
    WorkingGoal,
    WorkingMemoryState,
)
from cohezion.compound.harness_protocol import (
    ActionSubstrateType,
    HarnessContextProtocol,
    ToolContract,
)
from cohezion.knowledge_graph.hippocam_memory import (
    Intent,
    IntentOperation,
    IntentStack,
    JanusGovernor,
    PalimPrefixTree,
    PrecipConsolidator,
)


def test_recuris_memory_quad_lifecycle() -> None:
    # 1. Initialize MemoryQuad
    skill = ExperientialSkill(
        skill_id="prompt_center",
        name="Adaptive Prompt Centering",
        description="Centers style embeddings by subtracting prompt mean",
        code_body="def center(x, mu):\n    return x - mu\n",
        domain="name_that_llm",
    )
    w_state = WorkingMemoryState(task_id="test_task_1")
    w_state.active_goals.append(WorkingGoal(goal_id="g1", description="Apply prompt centering"))
    rho = InvocationPolicy(routing_rules={"prompt centering": "prompt_center"})
    checker = CheckerPipeline()

    quad = MemoryQuad(E={"prompt_center": skill}, W=w_state, rho=rho, C=checker)

    # 2. Test Invocation Policy triggering on active goal
    invoked = quad.rho.select_skill(quad.W, quad.E)
    assert invoked is not None
    assert invoked.skill_id == "prompt_center"

    # 3. Test Checker verification
    checker.register_verifier("math_check", lambda val: (val > 0, "Must be positive"))
    ok, _ = checker.verify_receipt("math_check", 42)
    assert ok is True

    # 4. Working memory state update upon verified receipt
    assert quad.W.has_unresolved_goals is True
    quad.W.mark_verified("g1", receipt="Receipt #1234")
    assert quad.W.has_unresolved_goals is False


def test_recuris_trace_failure_localization() -> None:
    trace = [
        ExecutionTraceStep(
            turn=1,
            working_state_snapshot={"active_goals": [{"goal_id": "g1", "status": "PENDING"}]},
            invoked_skill_id=None,
            action_taken="pass",
            environment_feedback="waiting",
            verifier_passed=True,
        )
    ]
    # Invoc Policy failed because pending goal existed but no skill was invoked
    loc = TraceFailureLocalizer.localize_failure(trace, task_succeeded=False)
    assert loc is not None
    assert loc.failed_component == MemoryComponent.INVOCATION_POLICY
    assert loc.confidence > 0.80


def test_validation_gated_admission() -> None:
    # Safe code
    valid_code = "def safe_fn(x: int) -> int:\n    return x + 1\n"
    ok, msg = ValidationGatedAdmission.validate_code_patch(valid_code)
    assert ok is True

    # Malicious code with eval
    bad_code = "def exploit(cmd: str):\n    eval(cmd)\n"
    ok, msg = ValidationGatedAdmission.validate_code_patch(bad_code)
    assert ok is False
    assert "Forbidden" in msg


def test_hippocam_intent_stack_and_janus() -> None:
    stack = IntentStack()
    i1 = Intent(
        intent_id="i1",
        purpose="Classify generator LLM style",
        exit_conditions="balanced_accuracy > 0.50",
        start_message_idx=0,
    )
    stack.push(i1)
    assert stack.depth == 1

    # Janus detects exit condition met
    op, reason = JanusGovernor.evaluate_intent(
        stack, "Verified: balanced_accuracy score achieved", 5
    )
    assert op == IntentOperation.CLOSE
    assert "Exit condition met" in reason

    closed = stack.close_current("SUCCESS")
    assert closed is not None
    assert closed.is_closed is True
    assert closed.closed_outcome == "SUCCESS"


def test_hippocam_precip_and_palim_consolidation() -> None:
    closed_intent = Intent(
        intent_id="intent_stylometry",
        purpose="Extract function word features",
        exit_conditions="features extracted",
        start_message_idx=0,
        is_closed=True,
        closed_outcome="SUCCESS",
    )
    raw_msgs = [
        {
            "role": "agent",
            "content": "Applied invariant: Function word frequencies isolate authorial style.",
        },
        {
            "role": "tool",
            "content": "Extracted 150 feature columns cleanly.",
            "source": "stylometry.py",
        },
    ]

    # 1. Precip Consolidates Intent
    node = PrecipConsolidator.consolidate_intent(closed_intent, raw_msgs)
    assert node.level == 1
    assert "Intent 'Extract function word features' concluded" in node.narrative
    assert len(node.knowledge) > 0

    # 2. Palim Prefix Tree
    tree = PalimPrefixTree()
    tree.insert(node)
    recalled = tree.recall(node.node_id)
    assert recalled is not None
    assert recalled.intent_id == "intent_stylometry"

    # Search knowledge
    results = tree.search_knowledge("invariant")
    assert len(results) > 0


def test_macaron_harness_context_protocol() -> None:
    hcp = HarnessContextProtocol(agent_id="test_agent")
    tool = ToolContract(
        name="sinkhorn_balance",
        description="Applies Sinkhorn-Knopp marginal balancing",
        parameters_schema={"type": "object", "properties": {"prob_matrix": {"type": "array"}}},
    )
    hcp.register_tool(tool)

    manifest = hcp.generate_hcp_manifest()
    assert manifest["hcp_version"] == "1.0.0"
    assert len(manifest["available_tools"]) == 1
    assert manifest["available_tools"][0]["name"] == "sinkhorn_balance"

    # Test AST action substrate
    receipt = hcp.execute_ast_action("x = 10 + 20")
    assert receipt.success is True
    assert receipt.substrate == ActionSubstrateType.DETERMINISTIC_AST
