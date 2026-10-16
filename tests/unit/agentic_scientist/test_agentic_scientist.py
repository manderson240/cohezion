"""
Unit tests for The Agentic Scientist orchestration module (arXiv:2610.18933).
"""

import pytest

from cohezion.agentic_scientist.contracts import (
    AblationPlan,
    EvaluationStatus,
    IdeationContract,
    RubricCriterion,
    TaskSpecification,
)
from cohezion.agentic_scientist.orchestrator import (
    AblationStudyEngine,
    ClaimAuditor,
    ExecutionAgent,
    IdeationAgent,
    SharedKnowledgeMemory,
)


@pytest.fixture
def sample_task():
    return TaskSpecification(
        task_id="test_opt_01",
        description="Optimize learned recombination weights",
        initial_program_code="def optimize(): return 0.5",
        search_evaluator_code="def run_evaluation(code): return 0.85, {'acc': 0.85}",
        baseline_score=0.5,
    )


def test_task_specification_integrity(sample_task):
    assert len(sample_task.search_evaluator_hash) == 64
    # Untampered code passes
    assert sample_task.verify_evaluator_integrity(sample_task.search_evaluator_code) is True
    # Tampered evaluator fails integrity check
    tampered_code = sample_task.search_evaluator_code + "\n# backdoor"
    assert sample_task.verify_evaluator_integrity(tampered_code) is False


def test_ideation_agent_contract_generation(sample_task):
    agent = IdeationAgent(worker_id="worker_alpha")
    rubrics = [
        RubricCriterion(
            id="R1_DALE",
            name="Dale Compliance",
            description="All synaptic weights must maintain invariant signs.",
            verification_type="ast_inspection",
            is_mandatory=True,
        )
    ]
    contract = agent.propose_contract(
        task=sample_task,
        best_program_code=sample_task.initial_program_code,
        recent_conclusions=["Worker 1 found that learning rate > 0.1 diverges."],
        idea_title="Asymmetric Sigmoidal Modulation",
        hypothesis="Widening the sigmoid saturation band stabilizes credit assignment.",
        implementation_plan=["Define sigmoid width parameter", "Apply to forward pass"],
        rubrics=rubrics,
    )

    assert contract.worker_id == "worker_alpha"
    assert contract.title == "Asymmetric Sigmoidal Modulation"
    assert len(contract.target_rubrics) == 1
    assert contract.target_rubrics[0].id == "R1_DALE"


@pytest.mark.asyncio
async def test_execution_agent_decoupled_gates(sample_task):
    agent = ExecutionAgent(
        worker_id="worker_alpha",
        evaluator_fn=lambda code: (0.92, {"score": 0.92}),
    )

    contract = IdeationContract(
        title="Test Idea",
        falsifiable_hypothesis="Hypothesis test",
        implementation_plan=["Step 1"],
        target_rubrics=[
            RubricCriterion(
                id="R0_INTEGRITY",
                name="Integrity",
                description="No redefinition of evaluation harness",
            )
        ],
        target_metrics=["score"],
    )

    # Valid candidate improving score
    valid_code = "def optimize(): return 0.92"
    outcome = await agent.execute_attempt(
        contract=contract,
        candidate_code=valid_code,
        current_best_score=0.85,
        task=sample_task,
    )

    assert outcome.status == EvaluationStatus.SUCCESS
    assert outcome.scalar_score == 0.92
    assert outcome.all_rubrics_passed is True
    assert outcome.is_new_best is True

    # Valid candidate with lower score (decoupled: rubrics pass, but not new best)
    agent_low = ExecutionAgent(
        worker_id="worker_alpha",
        evaluator_fn=lambda code: (0.70, {"score": 0.70}),
    )
    outcome_low = await agent_low.execute_attempt(
        contract=contract,
        candidate_code=valid_code,
        current_best_score=0.85,
        task=sample_task,
    )
    assert outcome_low.all_rubrics_passed is True
    assert outcome_low.is_new_best is False

    # Syntax error candidate
    invalid_code = "def broken( return 123"
    outcome_err = await agent.execute_attempt(
        contract=contract,
        candidate_code=invalid_code,
        current_best_score=0.85,
        task=sample_task,
    )
    assert outcome_err.status == EvaluationStatus.SYNTAX_ERROR
    assert outcome_err.all_rubrics_passed is False
    assert outcome_err.is_new_best is False


@pytest.mark.asyncio
async def test_shared_knowledge_memory():
    memory = SharedKnowledgeMemory()
    agent = ExecutionAgent(worker_id="worker_1", evaluator_fn=lambda c: (0.88, {"acc": 0.88}))
    contract = IdeationContract(
        title="Worker 1 Innovation",
        falsifiable_hypothesis="Hypothesis 1",
        implementation_plan=[],
        target_rubrics=[],
        target_metrics=[],
    )
    task = TaskSpecification(
        task_id="t1",
        description="",
        initial_program_code="",
        search_evaluator_code="",
        baseline_score=0.5,
    )
    outcome = await agent.execute_attempt(contract, "def f(): pass", 0.5, task)

    await memory.publish_cycle_conclusion(
        worker_id="worker_1",
        contract_title="Worker 1 Innovation",
        hypothesis="Hypothesis 1",
        outcome=outcome,
        distilled_takeaway="Sigmoid width 2.5 achieved 88% accuracy without gradient attenuation.",
    )

    context = await memory.get_distilled_context(current_worker_id="worker_2")
    assert len(context) == 1
    assert "Worker 1 Innovation" in context[0]
    assert "88% accuracy" in context[0]


@pytest.mark.asyncio
async def test_ablation_study_engine():
    engine = AblationStudyEngine(
        evaluator_seed_fn=lambda code, seed: 0.95 if "full" in code else 0.85
    )

    plan = AblationPlan(
        ablation_id="abl_sigmoid",
        target_program_id="best_01",
        isolated_innovation="Wide Sigmoid Saturation",
        component_type="architecture",
        rationale="Test credit assignment without wide sigmoid",
        code_patch_to_revert="",
    )

    result = await engine.evaluate_ablation(
        plan=plan,
        full_program_code="full model code",
        ablated_program_code="ablated model code",
        seeds=[1, 2, 3],
    )

    assert result.ablation_id == "abl_sigmoid"
    assert pytest.approx(result.full_program_mean, 0.0001) == 0.95
    assert pytest.approx(result.ablated_program_mean, 0.0001) == 0.85
    assert pytest.approx(result.causal_lift, 0.0001) == 0.10
    assert result.is_statistically_significant is True


def test_claim_auditor():
    auditor = ClaimAuditor()

    # Exact claim verification
    claim_link = auditor.audit_claim(
        statement="ED-PPO achieved 96.7% accuracy on MNIST.",
        reported_value=0.967,
        canonical_value=0.9670,
        run_id="run_mnist_2026",
        metric_key="mnist_acc",
        artifact_uri="experiments/mnist/run_2026.json",
    )
    assert claim_link.is_verified is True
    assert "Verified" in claim_link.audit_notes

    # Hallucinated or overclaimed value
    claim_link_bad = auditor.audit_claim(
        statement="ED-PPO achieved 99.9% accuracy on MNIST.",
        reported_value=0.999,
        canonical_value=0.9670,
        run_id="run_mnist_2026",
        metric_key="mnist_acc",
        artifact_uri="experiments/mnist/run_2026.json",
    )
    assert claim_link_bad.is_verified is False
    assert "Discrepancy detected" in claim_link_bad.audit_notes
