"""Tests for the Capability Evaluation Harness."""

import pytest

from cohezion.universe.capability_eval import (
    CriterionResult,
    Difficulty,
    EvalRunner,
    EvalScorer,
    EvalTask,
    RegressionDetector,
    ScoringCriterion,
    ScoringMethod,
    ScoringRubric,
    SuiteResult,
    TaskDomain,
    TaskSuite,
    build_core_capability_suite,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class MockAgent:
    """Mock agent that returns configurable responses."""

    def __init__(self, responses: dict[str, str] | None = None, default: str = ""):
        self._responses = responses or {}
        self._default = default

    async def execute(self, prompt: str) -> tuple[str, int]:
        response = self._responses.get(prompt, self._default)
        return response, len(response)


@pytest.fixture
def simple_rubric():
    return ScoringRubric(
        criteria=[
            ScoringCriterion("exact", ScoringMethod.EXACT_MATCH, weight=1.0, expected="hello"),
            ScoringCriterion("contains", ScoringMethod.CONTAINS, weight=1.0, expected="world"),
        ],
        pass_threshold=0.5,
    )


@pytest.fixture
def scorer():
    return EvalScorer()


@pytest.fixture
def core_suite():
    return build_core_capability_suite()


# ---------------------------------------------------------------------------
# ScoringCriterion tests
# ---------------------------------------------------------------------------


class TestScoringCriterion:
    def test_creation(self):
        c = ScoringCriterion("test", ScoringMethod.EXACT_MATCH, weight=2.0, expected="abc")
        assert c.name == "test"
        assert c.method == ScoringMethod.EXACT_MATCH
        assert c.weight == 2.0
        assert c.expected == "abc"
        assert c.threshold == 0.5  # default

    def test_default_weight(self):
        c = ScoringCriterion("test", ScoringMethod.CONTAINS)
        assert c.weight == 1.0


# ---------------------------------------------------------------------------
# EvalScorer tests
# ---------------------------------------------------------------------------


class TestEvalScorer:
    def test_exact_match_pass(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("exact", ScoringMethod.EXACT_MATCH, expected="hello")]
            ),
        )
        results = scorer.score_task(task, "hello")
        assert results[0].score == 1.0
        assert results[0].passed

    def test_exact_match_fail(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("exact", ScoringMethod.EXACT_MATCH, expected="hello")]
            ),
        )
        results = scorer.score_task(task, "goodbye")
        assert results[0].score == 0.0
        assert not results[0].passed

    def test_contains_match(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("contains", ScoringMethod.CONTAINS, expected="world")]
            ),
        )
        results = scorer.score_task(task, "hello world")
        assert results[0].score == 1.0

    def test_regex_match(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("regex", ScoringMethod.REGEX, expected=r"\d{3}")]
            ),
        )
        results = scorer.score_task(task, "code 404 found")
        assert results[0].score == 1.0

    def test_regex_no_match(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("regex", ScoringMethod.REGEX, expected=r"\d{5}")]
            ),
        )
        results = scorer.score_task(task, "code 404 found")
        assert results[0].score == 0.0

    def test_numeric_closeness_exact(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.MATH,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[
                    ScoringCriterion("numeric", ScoringMethod.NUMERIC_CLOSENESS, expected=42.0)
                ]
            ),
        )
        results = scorer.score_task(task, "The answer is 42.0")
        assert results[0].score == pytest.approx(1.0)

    def test_numeric_closeness_approximate(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.MATH,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[
                    ScoringCriterion("numeric", ScoringMethod.NUMERIC_CLOSENESS, expected=100.0)
                ]
            ),
        )
        results = scorer.score_task(task, "Result: 95")
        assert 0.9 <= results[0].score <= 1.0

    def test_code_execution_valid_python(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.CODE_GENERATION,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(criteria=[ScoringCriterion("code", ScoringMethod.CODE_EXECUTION)]),
        )
        results = scorer.score_task(task, "def hello():\n    return 'world'")
        assert results[0].score == 0.8  # Valid Python

    def test_code_execution_invalid_python(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.CODE_GENERATION,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(criteria=[ScoringCriterion("code", ScoringMethod.CODE_EXECUTION)]),
        )
        results = scorer.score_task(task, "This is not code at all")
        assert results[0].score == 0.0

    def test_composite_score(self, scorer, simple_rubric):
        results = [
            CriterionResult("exact", 1.0, True, ScoringMethod.EXACT_MATCH),
            CriterionResult("contains", 0.0, False, ScoringMethod.CONTAINS),
        ]
        composite, passed = scorer.compute_composite(simple_rubric, results)
        assert composite == pytest.approx(0.5)
        assert passed  # 0.5 >= pass_threshold 0.5

    def test_composite_empty(self, scorer, simple_rubric):
        composite, passed = scorer.compute_composite(simple_rubric, [])
        assert composite == 0.0
        assert not passed

    def test_custom_scorer(self, scorer):
        custom_fn = lambda out, _: 1.0 if "special" in out else 0.0
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[
                    ScoringCriterion(
                        "custom", ScoringMethod.CUSTOM, metadata={"scorer_fn": custom_fn}
                    )
                ]
            ),
        )
        results = scorer.score_task(task, "this is special content")
        assert results[0].score == 1.0

    def test_none_expected(self, scorer):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test",
            rubric=ScoringRubric(
                criteria=[ScoringCriterion("exact", ScoringMethod.EXACT_MATCH, expected=None)]
            ),
        )
        results = scorer.score_task(task, "anything")
        assert results[0].score == 0.0


# ---------------------------------------------------------------------------
# EvalTask tests
# ---------------------------------------------------------------------------


class TestEvalTask:
    def test_content_hash_deterministic(self):
        task = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="test prompt",
            rubric=ScoringRubric(criteria=[]),
        )
        hash1 = task.content_hash
        hash2 = task.content_hash
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_content_hash_varies(self):
        task1 = EvalTask(
            task_id="t1",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="prompt A",
            rubric=ScoringRubric(criteria=[]),
        )
        task2 = EvalTask(
            task_id="t2",
            domain=TaskDomain.REASONING,
            difficulty=Difficulty.EASY,
            prompt="prompt B",
            rubric=ScoringRubric(criteria=[]),
        )
        assert task1.content_hash != task2.content_hash


# ---------------------------------------------------------------------------
# TaskSuite tests
# ---------------------------------------------------------------------------


class TestTaskSuite:
    def test_domain_distribution(self, core_suite):
        dist = core_suite.domain_distribution
        assert "code_generation" in dist
        assert "reasoning" in dist
        assert sum(dist.values()) == len(core_suite.tasks)

    def test_difficulty_distribution(self, core_suite):
        dist = core_suite.difficulty_distribution
        assert "easy" in dist
        assert sum(dist.values()) == len(core_suite.tasks)

    def test_core_suite_has_tasks(self, core_suite):
        assert len(core_suite.tasks) >= 5
        assert core_suite.suite_id == "core_capability_v1"


# ---------------------------------------------------------------------------
# EvalRunner tests
# ---------------------------------------------------------------------------


class TestEvalRunner:
    @pytest.mark.asyncio
    async def test_run_suite(self, core_suite, tmp_path):
        agent = MockAgent(default="def is_palindrome(s):\n    return s == s[::-1]")
        runner = EvalRunner(output_dir=str(tmp_path / "evals"))
        result = await runner.run_suite(core_suite, agent, model_id="test-model")

        assert isinstance(result, SuiteResult)
        assert result.total_tasks == len(core_suite.tasks)
        assert result.model_id == "test-model"
        assert 0.0 <= result.overall_score <= 1.0
        assert result.domain_scores  # Not empty

    @pytest.mark.asyncio
    async def test_run_saves_result(self, tmp_path):
        suite = TaskSuite(
            suite_id="test_suite",
            name="Test",
            description="test",
            tasks=[
                EvalTask(
                    task_id="t1",
                    domain=TaskDomain.REASONING,
                    difficulty=Difficulty.EASY,
                    prompt="What is 2+2?",
                    rubric=ScoringRubric(
                        criteria=[ScoringCriterion("ans", ScoringMethod.CONTAINS, expected="4")]
                    ),
                )
            ],
        )
        agent = MockAgent(default="The answer is 4")
        runner = EvalRunner(output_dir=str(tmp_path / "evals"))
        result = await runner.run_suite(suite, agent)

        # Check file was saved
        files = list((tmp_path / "evals").glob("*.json"))
        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, tmp_path):
        class FailingAgent:
            async def execute(self, prompt):
                raise RuntimeError("Agent crashed")

        suite = TaskSuite(
            suite_id="test",
            name="Test",
            description="test",
            tasks=[
                EvalTask(
                    task_id="t1",
                    domain=TaskDomain.REASONING,
                    difficulty=Difficulty.EASY,
                    prompt="test",
                    rubric=ScoringRubric(criteria=[]),
                )
            ],
        )
        runner = EvalRunner(output_dir=str(tmp_path / "evals"))
        result = await runner.run_suite(suite, FailingAgent())

        assert result.task_results[0].error is not None
        assert not result.task_results[0].passed

    @pytest.mark.asyncio
    async def test_pass_rate(self, tmp_path):
        suite = TaskSuite(
            suite_id="test",
            name="Test",
            description="test",
            tasks=[
                EvalTask(
                    task_id="t1",
                    domain=TaskDomain.REASONING,
                    difficulty=Difficulty.EASY,
                    prompt="test1",
                    rubric=ScoringRubric(
                        criteria=[ScoringCriterion("c", ScoringMethod.CONTAINS, expected="yes")]
                    ),
                ),
                EvalTask(
                    task_id="t2",
                    domain=TaskDomain.REASONING,
                    difficulty=Difficulty.EASY,
                    prompt="test2",
                    rubric=ScoringRubric(
                        criteria=[ScoringCriterion("c", ScoringMethod.CONTAINS, expected="yes")]
                    ),
                ),
            ],
        )
        agent = MockAgent(responses={"test1": "yes", "test2": "no"})
        runner = EvalRunner(output_dir=str(tmp_path / "evals"))
        result = await runner.run_suite(suite, agent)

        assert result.passed_tasks == 1
        assert result.pass_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# RegressionDetector tests
# ---------------------------------------------------------------------------


class TestRegressionDetector:
    def test_no_regression(self):
        baseline = SuiteResult(
            suite_id="s",
            run_id="r1",
            model_id="m1",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.8,
            domain_scores={"code_generation": 0.9},
            difficulty_scores={},
        )
        current = SuiteResult(
            suite_id="s",
            run_id="r2",
            model_id="m2",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=9,
            overall_score=0.85,
            domain_scores={"code_generation": 0.92},
            difficulty_scores={},
        )
        detector = RegressionDetector()
        report = detector.compare(baseline, current)

        assert not report.overall_regression
        assert len(report.alerts) == 0

    def test_detects_regression(self):
        baseline = SuiteResult(
            suite_id="s",
            run_id="r1",
            model_id="m1",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.8,
            domain_scores={"code_generation": 0.9},
            difficulty_scores={},
        )
        current = SuiteResult(
            suite_id="s",
            run_id="r2",
            model_id="m2",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=5,
            overall_score=0.5,
            domain_scores={"code_generation": 0.4},
            difficulty_scores={},
        )
        detector = RegressionDetector()
        report = detector.compare(baseline, current)

        assert report.overall_regression
        assert len(report.alerts) >= 2  # overall + domain

    def test_small_delta_not_flagged(self):
        baseline = SuiteResult(
            suite_id="s",
            run_id="r1",
            model_id="m1",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.80,
            domain_scores={"reasoning": 0.85},
            difficulty_scores={},
        )
        current = SuiteResult(
            suite_id="s",
            run_id="r2",
            model_id="m2",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.78,
            domain_scores={"reasoning": 0.83},
            difficulty_scores={},
        )
        detector = RegressionDetector(significance_threshold=0.05)
        report = detector.compare(baseline, current)

        # Delta of 0.02 is below 0.05 threshold
        assert not report.overall_regression

    def test_report_summary_generated(self):
        baseline = SuiteResult(
            suite_id="s",
            run_id="r1",
            model_id="baseline-v1",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.8,
            domain_scores={},
            difficulty_scores={},
        )
        current = SuiteResult(
            suite_id="s",
            run_id="r2",
            model_id="current-v2",
            task_results=[],
            started_at="",
            completed_at="",
            total_tasks=10,
            passed_tasks=8,
            overall_score=0.85,
            domain_scores={},
            difficulty_scores={},
        )
        detector = RegressionDetector()
        report = detector.compare(baseline, current)
        assert "baseline-v1" in report.summary
        assert "current-v2" in report.summary

    def test_suite_result_serialization(self):
        result = SuiteResult(
            suite_id="s",
            run_id="r1",
            model_id="m1",
            task_results=[],
            started_at="now",
            completed_at="later",
            total_tasks=5,
            passed_tasks=3,
            overall_score=0.6,
            domain_scores={"code_generation": 0.7},
            difficulty_scores={"easy": 0.9},
        )
        d = result.to_dict()
        assert d["suite_id"] == "s"
        assert d["pass_rate"] == pytest.approx(0.6)
        assert isinstance(d["task_results"], list)
