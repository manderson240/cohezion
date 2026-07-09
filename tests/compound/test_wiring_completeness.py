"""V-model wiring-completeness tests — ensure every product has a consumer.

Five previously-unwired products are closed here:
  W1: JepaGate auto-injected by make_executor()
  W2: JourneyTracker.restore_identity() called by ExecutorFactory; save_identity() via atexit
  W3: DegradationDetector.suggest_routing_tier() exposed in execution metrics
  W4: DifficultyEstimator.predict_tier() exposed in execution metrics
  W5: skill_proximity() consumed by _generate_recommendation()

Each test is discriminating: a wrong implementation that only "fires" but doesn't wire
the product into the correct consumer would FAIL the test.
"""

from __future__ import annotations

import atexit
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# W1: JepaGate auto-injected by make_executor()
# ---------------------------------------------------------------------------


class TestW1JepaGateFactoryInjection:
    def test_make_executor_injects_jepa_gate(self):
        """make_executor() must produce an executor with _jepa_gate set.

        Wrong impl: factory passes jepa_gate=None (gate never fires).
        Discriminating: _jepa_gate must not be None after make_executor().
        """
        from cohezion.compound import make_executor

        mock_client = MagicMock()
        # lemonade_available is imported inside make_executor() from local_inference
        with (
            patch("cohezion.compound.local_inference.lemonade_available", return_value=False),
            patch("cohezion.compound.local_inference.get_recommended_concurrency", return_value=1),
        ):
            executor = make_executor(mock_client)

        assert executor._jepa_gate is not None, (
            "make_executor() must inject a JepaGate (at minimum fail-open with world_model=None)"
        )

    def test_injected_gate_is_fail_open_when_no_world_model(self):
        """Gate injected by factory must fail-open (PROCEED) when world model unavailable.

        Wrong impl: gate injects with world_model that raises, causing SKIP on first call.
        """
        from cohezion.compound import make_executor
        from cohezion.compound.jepa_gate import PreExecutionVerdict

        mock_client = MagicMock()
        with (
            patch("cohezion.compound.local_inference.lemonade_available", return_value=False),
            patch("cohezion.compound.local_inference.get_recommended_concurrency", return_value=1),
        ):
            executor = make_executor(mock_client)

        verdict = executor._jepa_gate.check("any task")
        assert verdict == PreExecutionVerdict.PROCEED, (
            f"Fail-open gate must return PROCEED without world model, got {verdict}"
        )

    def test_executor_factory_create_forwards_jepa_gate(self):
        """ExecutorFactory.create() must accept and forward jepa_gate kwarg.

        Wrong impl: create() ignores jepa_gate, stores None on executor.
        """
        from cohezion.compound.executor_factory import ExecutorFactory
        from cohezion.compound.jepa_gate import JepaGate

        gate = JepaGate(world_model=None)
        mock_client = MagicMock()
        executor = ExecutorFactory.create(mock_client, jepa_gate=gate)
        assert executor._jepa_gate is gate, (
            "ExecutorFactory.create() must forward jepa_gate to CompoundExecutor"
        )


# ---------------------------------------------------------------------------
# W2: JourneyTracker identity lifecycle
# ---------------------------------------------------------------------------


class TestW2JourneyTrackerIdentityLifecycle:
    def test_factory_calls_restore_identity_on_creation(self):
        """ExecutorFactory.create() must call restore_identity() when journey_tracker provided.

        Wrong impl: factory stores the tracker but never restores cross-session identity.
        Discriminating: method must actually be called (not just stored).
        """
        from cohezion.compound.executor_factory import ExecutorFactory

        mock_tracker = MagicMock()
        mock_tracker.restore_identity.return_value = True
        mock_client = MagicMock()

        ExecutorFactory.create(mock_client, journey_tracker=mock_tracker)

        (
            mock_tracker.restore_identity.assert_called_once(),
            (
                "ExecutorFactory.create() must call restore_identity() when a journey_tracker is provided"
            ),
        )

    def test_factory_registers_save_identity_as_atexit_handler(self):
        """ExecutorFactory.create() must register journey_tracker.save_identity via atexit.

        Wrong impl: factory calls restore but forgets to wire save_identity() on exit.
        Discriminating: atexit handlers must include save_identity after factory creation.
        """
        from cohezion.compound.executor_factory import ExecutorFactory

        mock_tracker = MagicMock()
        mock_client = MagicMock()

        # Capture atexit registrations during factory call
        registered = []
        original_register = atexit.register

        def spy_register(fn, *args, **kwargs):
            registered.append(fn)
            return original_register(fn, *args, **kwargs)

        with patch("atexit.register", side_effect=spy_register):
            ExecutorFactory.create(mock_client, journey_tracker=mock_tracker)

        assert mock_tracker.save_identity in registered, (
            "ExecutorFactory.create() must register journey_tracker.save_identity via atexit"
        )

    def test_no_identity_lifecycle_when_no_journey_tracker(self):
        """When no journey_tracker, factory must not call restore/save identity.

        Wrong impl: factory always calls restore_identity() on some default object.
        """
        from cohezion.compound.executor_factory import ExecutorFactory

        mock_client = MagicMock()

        registered = []
        with patch("atexit.register", side_effect=lambda f, *a, **k: registered.append(f)):
            ExecutorFactory.create(mock_client, journey_tracker=None)

        # There should be no save_identity call in registered fns
        save_names = [getattr(f, "__name__", str(f)) for f in registered]
        assert "save_identity" not in save_names, (
            "No save_identity atexit registration when journey_tracker is None"
        )


# ---------------------------------------------------------------------------
# W3: DegradationDetector.suggest_routing_tier() → execution metrics
# ---------------------------------------------------------------------------


class TestW3SuggestRoutingTierConsumer:
    def _make_executor_with_degradation_detector(self):
        """Build a CompoundExecutor with a mocked DegradationDetector."""
        from cohezion.compound.degradation_detector import DegradationDetector
        from cohezion.compound.executor import CompoundExecutor

        dd = MagicMock(spec=DegradationDetector)
        dd.suggest_routing_tier.return_value = "igpu"
        mock_client = MagicMock()
        return CompoundExecutor(mock_client, degradation_detector=dd), dd

    def test_execute_task_calls_suggest_routing_tier(self):
        """execute_task must call DegradationDetector.suggest_routing_tier() at least once.

        Wrong impl: DD is stored but suggest_routing_tier() is never called.
        Discriminating: suggest_routing_tier() must actually be invoked per execution.
        """
        executor, dd = self._make_executor_with_degradation_detector()

        def fake_execute(guidance):
            return "output", {}

        executor.execute_task(
            task_description="test task",
            skill_name="TEST",
            operation_type="generate",
            execute_fn=fake_execute,
        )

        (
            dd.suggest_routing_tier.assert_called(),
            ("execute_task must call DegradationDetector.suggest_routing_tier()"),
        )

    def test_execute_task_exposes_suggested_tier_in_metrics(self):
        """ExecutionResult.metrics must contain 'suggested_tier' after execution.

        Wrong impl: tier is computed but not stored in metrics dict.
        Discriminating: key must actually appear in the returned metrics.
        """
        executor, dd = self._make_executor_with_degradation_detector()
        dd.suggest_routing_tier.return_value = "igpu"

        def fake_execute(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="test task",
            skill_name="TEST",
            operation_type="generate",
            execute_fn=fake_execute,
        )

        assert "suggested_tier" in result.metrics, (
            f"'suggested_tier' must appear in execution metrics; got keys: {list(result.metrics.keys())}"
        )
        assert result.metrics["suggested_tier"] == "igpu"


# ---------------------------------------------------------------------------
# W4: DifficultyEstimator.predict_tier() → execution metrics
# ---------------------------------------------------------------------------


class TestW4PredictTierConsumer:
    def _make_executor_with_difficulty_estimator(self):
        """Build a CompoundExecutor where SkillRefiner has a mocked DifficultyEstimator."""
        from cohezion.compound.difficulty_estimator import DifficultyEstimator
        from cohezion.compound.executor import CompoundExecutor
        from cohezion.compound.skill_refiner import SkillRefiner

        sr = MagicMock(spec=SkillRefiner)
        estimator = MagicMock(spec=DifficultyEstimator)
        estimator.predict_tier.return_value = "npu"
        sr._difficulty_estimator = estimator

        mock_client = MagicMock()
        return CompoundExecutor(mock_client, skill_refiner=sr), estimator

    def test_execute_task_calls_predict_tier_with_skill_and_op(self):
        """execute_task must call DifficultyEstimator.predict_tier(skill_name, operation_type).

        Wrong impl: predict_tier is never called (prediction made but unused).
        Discriminating: call must pass through skill_name and operation_type.
        """
        executor, estimator = self._make_executor_with_difficulty_estimator()

        def fake_execute(guidance):
            return "output", {}

        executor.execute_task(
            task_description="test task",
            skill_name="MY_SKILL",
            operation_type="analyze",
            execute_fn=fake_execute,
        )

        (
            estimator.predict_tier.assert_called_with("MY_SKILL", "analyze"),
            ("execute_task must call predict_tier(skill_name, operation_type)"),
        )

    def test_execute_task_exposes_predicted_tier_in_metrics(self):
        """ExecutionResult.metrics must contain 'predicted_tier' after execution.

        Wrong impl: tier is predicted but not forwarded to result metrics.
        """
        executor, estimator = self._make_executor_with_difficulty_estimator()
        estimator.predict_tier.return_value = "npu"

        def fake_execute(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="test task",
            skill_name="MY_SKILL",
            operation_type="generate",
            execute_fn=fake_execute,
        )

        assert "predicted_tier" in result.metrics, (
            f"'predicted_tier' must appear in execution metrics; got: {list(result.metrics.keys())}"
        )
        assert result.metrics["predicted_tier"] == "npu"


# ---------------------------------------------------------------------------
# W5: skill_proximity() consumed by _generate_recommendation()
# ---------------------------------------------------------------------------


class TestW5SkillProximityConsumer:
    def _make_refiner_with_history(self, skill_a: str, skill_b: str, proximity: float):
        """Build a SkillRefiner stub that returns a controlled proximity score."""
        from cohezion.compound.skill_refiner import SkillRefiner

        sr = SkillRefiner.__new__(SkillRefiner)
        # Minimal init to bypass heavy I/O
        sr._session_goal = None
        sr._moe_router = None  # required by _generate_recommendation MoE check (#83)
        sr._autodata_wins = {}  # required by RiVER frequency weighting (#141)
        sr._difficulty_estimator = MagicMock()
        sr._env_predictor = MagicMock()
        sr._env_predictor._history = {skill_b: {}}

        # Stub the proximity method to return controlled value
        sr.skill_proximity = MagicMock(return_value=proximity)

        # Stub _autodata_candidates and _autodata_select for isolation
        sr._autodata_candidates = MagicMock(return_value=["base recommendation"])
        sr._autodata_select = MagicMock(return_value="base recommendation")
        return sr

    def test_generate_recommendation_calls_skill_proximity(self):
        """_generate_recommendation() must call skill_proximity() to find nearest skill.

        Wrong impl: skill_proximity() exists but is never called by recommendation path.
        Discriminating: the method must be invoked at least once per recommendation.
        """
        from cohezion.compound.skill_refiner import ExecutionMetrics

        sr = self._make_refiner_with_history("SKILL_A", "SKILL_B", 0.8)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )
        sr._generate_recommendation(metrics, "generate", "SKILL_A")

        (
            sr.skill_proximity.assert_called(),
            ("_generate_recommendation() must call skill_proximity() when history is available"),
        )

    def test_generate_recommendation_includes_transfer_hint_when_high_proximity(self):
        """When skill_proximity > 0.5, recommendation must include a transfer-from hint.

        Wrong impl: proximity is computed but recommendation text is unchanged.
        Discriminating: the output string must reference the proximate skill name.
        """
        from cohezion.compound.skill_refiner import ExecutionMetrics

        sr = self._make_refiner_with_history("SKILL_A", "SKILL_B", 0.75)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )
        result = sr._generate_recommendation(metrics, "generate", "SKILL_A")

        assert "SKILL_B" in result, (
            f"High-proximity skill SKILL_B must appear in recommendation; got: {result!r}"
        )

    def test_generate_recommendation_no_transfer_when_low_proximity(self):
        """When skill_proximity ≤ 0.5, recommendation must NOT include transfer hint.

        Wrong impl: always adds transfer hint regardless of proximity score.
        Discriminating: low-proximity skills must not pollute recommendation.
        """
        from cohezion.compound.skill_refiner import ExecutionMetrics

        sr = self._make_refiner_with_history("SKILL_A", "SKILL_C", 0.2)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )
        result = sr._generate_recommendation(metrics, "generate", "SKILL_A")

        assert "SKILL_C" not in result, (
            f"Low-proximity skill SKILL_C must NOT appear in recommendation; got: {result!r}"
        )

    def test_generate_recommendation_accepts_skill_name_kwarg(self):
        """_generate_recommendation() must accept skill_name as third positional param.

        Wrong impl: signature has no skill_name, causing TypeError on call.
        """
        import inspect

        from cohezion.compound.skill_refiner import SkillRefiner

        sig = inspect.signature(SkillRefiner._generate_recommendation)
        params = list(sig.parameters.keys())
        assert "skill_name" in params, (
            f"_generate_recommendation must accept 'skill_name'; got params: {params}"
        )


# ---------------------------------------------------------------------------
# WN1-WN4: AReaL2.0 JourneyTracker → SkillRefiner trajectory wiring
# ---------------------------------------------------------------------------


class TestWNTrajectoryWiring:
    """Verify that JourneyTracker.export_trajectories() is wired into
    SkillRefiner._autodata_candidates() (AReaL2.0 Gap 1+2 closure).

    Every producer must have a consumer — these tests confirm both ends.
    """

    def _make_fake_tracker(self, op: str, coherence: float, n: int = 5) -> object:
        """Return a minimal duck-typed JourneyTracker with export_trajectories."""
        points = [
            {
                "operation_type": op,
                "coherence": coherence,
                "efficiency": 0.5,
                "tier": "npu",
                "success": True,
            }
            for _ in range(n)
        ]

        class FakeTracker:
            def export_trajectories(self, last_n=20):
                return points

        return FakeTracker()

    def test_wn1_journey_tracker_kwarg_accepted(self):
        """WN1 structural: SkillRefiner.__init__ accepts journey_tracker kwarg."""
        import inspect

        from cohezion.compound.skill_refiner import SkillRefiner

        params = inspect.signature(SkillRefiner.__init__).parameters
        assert "journey_tracker" in params, (
            f"SkillRefiner.__init__ must accept 'journey_tracker'; got: {list(params)}"
        )

    def test_wn2_export_trajectories_shape(self):
        """WN2: export_trajectories returns list of dicts with required keys."""
        from unittest.mock import MagicMock

        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        # Seed a fake recent point directly
        fake_point = MagicMock()
        fake_point.operation_type = "synthesis"
        fake_point.coherence = 0.8
        fake_point.efficiency = 0.6
        fake_point.metadata = {"tier_used": "igpu", "success": True}
        tracker._recent_points.append(fake_point)

        result = tracker.export_trajectories(last_n=10)
        assert len(result) == 1
        assert set(result[0].keys()) >= {
            "operation_type",
            "coherence",
            "efficiency",
            "tier",
            "success",
        }
        assert result[0]["operation_type"] == "synthesis"
        assert result[0]["coherence"] == 0.8

    def test_wn3_high_coherence_trajectory_generates_reinforce_candidate(self):
        """WN3 discriminating: wired high-coherence tracker adds trajectory candidate.

        Wrong impl that ignores _journey_tracker would not include any candidate
        containing "Trajectory" — the discriminating check is substring presence.
        """
        from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner

        tracker = self._make_fake_tracker("synthesis", coherence=0.80, n=5)
        sr = SkillRefiner(journey_tracker=tracker)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )

        candidates = sr._autodata_candidates(metrics, "synthesis")

        traj_candidates = [c for c in candidates if "Trajectory" in c]
        assert traj_candidates, (
            f"Expected a trajectory-informed candidate for high-coherence history; "
            f"got: {candidates}"
        )
        assert "reinforce" in traj_candidates[0].lower(), (
            f"High-coherence trajectory must produce 'reinforce' candidate; "
            f"got: {traj_candidates[0]!r}"
        )

    def test_wn3b_low_coherence_trajectory_generates_revise_candidate(self):
        """WN3b discriminating: low-coherence trajectory → 'revise' candidate, not 'reinforce'."""
        from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner

        tracker = self._make_fake_tracker("synthesis", coherence=0.30, n=5)
        sr = SkillRefiner(journey_tracker=tracker)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )

        candidates = sr._autodata_candidates(metrics, "synthesis")

        traj_candidates = [c for c in candidates if "Trajectory" in c]
        assert traj_candidates, "Expected trajectory candidate for low-coherence history"
        assert "revise" in traj_candidates[0].lower(), (
            f"Low-coherence trajectory must produce 'revise' candidate; got: {traj_candidates[0]!r}"
        )

    def test_wn3c_no_tracker_produces_no_trajectory_candidate(self):
        """WN3c: without tracker, no trajectory candidate appears — operation_type mismatch also excluded."""
        from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner

        sr = SkillRefiner(journey_tracker=None)
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.7,
            anomaly_score=0.1,
            cached_hits=0,
        )
        candidates = sr._autodata_candidates(metrics, "synthesis")
        assert not any("Trajectory" in c for c in candidates)

    def test_wn4_factory_wires_journey_tracker(self):
        """WN4: SkillRefinerFactory.create() forwards journey_tracker to the instance."""
        import inspect

        from cohezion.compound.skill_refiner import SkillRefinerFactory

        params = inspect.signature(SkillRefinerFactory.create).parameters
        assert "journey_tracker" in params, (
            f"SkillRefinerFactory.create must accept 'journey_tracker'; got: {list(params)}"
        )

        tracker = self._make_fake_tracker("synthesis", coherence=0.75, n=4)
        refiner = SkillRefinerFactory.create(journey_tracker=tracker)
        assert refiner._journey_tracker is tracker, (
            "factory must set _journey_tracker on the returned SkillRefiner"
        )


# ---------------------------------------------------------------------------
# OR1-OR3: CompoundHealthOracle wiring (CH5 production path)
# ---------------------------------------------------------------------------


class TestORHealthOracleWiring:
    """OR1-OR3: CompoundHealthOracle wired into SkillRefiner and ExecutorFactory.

    Each test is discriminating: an oracle that is merely ACCEPTED (not read)
    would fail OR2. A factory that accepts health_oracle but doesn't inject it
    into SkillRefiner would fail OR3.
    """

    def test_or1_skill_refiner_accepts_health_oracle_kwarg(self) -> None:
        """OR1: SkillRefiner.__init__ accepts health_oracle; stores as _health_oracle."""
        import inspect

        from cohezion.compound.skill_refiner import SkillRefiner

        params = inspect.signature(SkillRefiner.__init__).parameters
        assert "health_oracle" in params, (
            f"SkillRefiner.__init__ must accept 'health_oracle'; got: {list(params)}"
        )
        from cohezion.compound.compound_health_oracle import CompoundHealthOracle

        oracle = CompoundHealthOracle(window_size=10)
        sr = SkillRefiner(health_oracle=oracle)
        assert sr._health_oracle is oracle

    def test_or2_generate_learning_signal_calls_oracle_assess(self) -> None:
        """OR2: After _generate_learning_signal(), oracle has more scores than before.

        Discriminating: wrong impl that only accepts oracle but never calls assess()
        would leave len(oracle.tracker) == 0 after the signal — and fail this test.
        """
        from cohezion.compound.compound_health_oracle import CompoundHealthOracle
        from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner

        oracle = CompoundHealthOracle(window_size=10)
        sr = SkillRefiner(health_oracle=oracle)

        before = len(oracle.tracker)  # 0 initially

        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=0.5,
            tokens_used=100,
            token_efficiency=200.0,
            quality_score=0.72,
            anomaly_score=0.1,
            cached_hits=0,
        )
        sr._generate_learning_signal("test_skill", "generation", metrics)

        after = len(oracle.tracker)
        assert after > before, (
            f"oracle.tracker must grow after _generate_learning_signal(); "
            f"before={before}, after={after}. Oracle is not being called."
        )

    def test_or3_factory_accepts_and_passes_health_oracle(self) -> None:
        """OR3: SkillRefinerFactory.create() forwards health_oracle to the instance."""
        import inspect

        from cohezion.compound.compound_health_oracle import CompoundHealthOracle
        from cohezion.compound.skill_refiner import SkillRefinerFactory

        params = inspect.signature(SkillRefinerFactory.create).parameters
        assert "health_oracle" in params, (
            f"SkillRefinerFactory.create must accept 'health_oracle'; got: {list(params)}"
        )
        oracle = CompoundHealthOracle(window_size=10)
        refiner = SkillRefinerFactory.create(health_oracle=oracle)
        assert refiner._health_oracle is oracle, (
            "factory must set _health_oracle on the returned SkillRefiner"
        )


# ---------------------------------------------------------------------------
# OC (Oracle Consumption) — end-to-end executor wiring (rung 4 discriminating)
# OC1-OC5 in test_tier_resolution.py verify _resolve_tier() in isolation.
# This class verifies the PRODUCTION call chain:
#   execute_task() → reads _refiner._health_oracle._last_assessment → _tier_hints["oracle_tier"]
#   → _resolve_tier(oracle_tier=...) → result.metrics["oracle_tier"]
# ---------------------------------------------------------------------------


class TestOCExecutorWiring:
    """OC end-to-end: execute_task() exposes oracle_tier in result.metrics.

    The discriminating condition: removing the 8-line oracle wiring block
    (lines ~794-801 in executor.py) would leave oracle_tier absent from
    result.metrics — and FAIL the tests here. OC1-OC5 in test_tier_resolution.py
    only verify _resolve_tier() in isolation (rungs 1-3). These tests close the
    rung-4 gap: the production path must actually read the oracle and put the
    tier into the metrics dict.
    """

    def _make_executor_with_oracle(self, oracle_tier: str):
        """Build a CompoundExecutor whose SkillRefiner has an oracle with a known last_assessment."""
        from cohezion.compound.compound_health_oracle import CompoundHealthOracle, HealthAssessment
        from cohezion.compound.executor import CompoundExecutor
        from cohezion.compound.skill_refiner import SkillRefiner

        # Real oracle with a pre-set _last_assessment (simulates accumulated regime history)
        oracle = CompoundHealthOracle(window_size=10)
        oracle._last_assessment = HealthAssessment(
            regime="stuck",
            tier_recommendation=oracle_tier,
            confidence=0.55,
            alert_level="warn",
            alerts=["STUCK regime — escalating tier to break over-exploitation"],
        )

        # SkillRefiner wired with the oracle; use MagicMock for the spec to avoid heavy init
        sr = MagicMock(spec=SkillRefiner)
        sr._health_oracle = oracle
        sr._difficulty_estimator = MagicMock()
        sr._difficulty_estimator.predict_tier.return_value = "npu"  # baseline cheap prediction

        mock_client = MagicMock()
        return CompoundExecutor(mock_client, skill_refiner=sr), oracle

    def test_oracle_tier_appears_in_execution_metrics(self):
        """execute_task() must put the oracle's tier_recommendation in result.metrics.

        Discriminating: removing the oracle wiring block from executor.py leaves
        oracle_tier absent from result.metrics → this assertion FAILS.
        """
        executor, oracle = self._make_executor_with_oracle("igpu")

        def fake_execute(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="test task",
            skill_name="TEST_SKILL",
            operation_type="generate",
            execute_fn=fake_execute,
        )

        assert "oracle_tier" in result.metrics, (
            f"'oracle_tier' must appear in execution metrics when oracle has a last_assessment; "
            f"got keys: {sorted(result.metrics.keys())}. "
            f"Check the oracle wiring block (~line 796) in execute_task()."
        )
        assert result.metrics["oracle_tier"] == "igpu", (
            f"oracle_tier must equal the oracle's tier_recommendation ('igpu'); "
            f"got {result.metrics['oracle_tier']!r}"
        )

    def test_oracle_chaotic_tier_reaches_metrics(self):
        """CHAOTIC oracle tier ('cpu') is correctly propagated to result.metrics.

        Discriminating: oracle_tier='cpu' must appear in metrics, not 'npu' from
        the DifficultyEstimator baseline. MAX-CAPABILITY selects 'cpu' over 'npu'.
        """
        executor, oracle = self._make_executor_with_oracle("cpu")

        def fake_execute(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="chaotic quality test",
            skill_name="CHAOTIC_SKILL",
            operation_type="analyze",
            execute_fn=fake_execute,
        )

        assert result.metrics.get("oracle_tier") == "cpu", (
            f"CHAOTIC oracle_tier='cpu' must appear in metrics; "
            f"got oracle_tier={result.metrics.get('oracle_tier')!r}, "
            f"recommended_tier={result.metrics.get('recommended_tier')!r}"
        )
        # MAX-CAPABILITY: 'cpu' > 'npu' (from difficulty estimator baseline) → recommended='cpu'
        assert result.metrics.get("recommended_tier") in ("cpu", "cloud"), (
            f"recommended_tier must be 'cpu' or 'cloud' when oracle forces 'cpu'; "
            f"got {result.metrics.get('recommended_tier')!r}"
        )

    def test_oracle_none_last_assessment_does_not_crash(self):
        """execute_task() must not crash when oracle has no last_assessment yet.

        The oracle's _last_assessment is None before any assess() call (first
        execution). The wiring block uses getattr(..., None) guards — this test
        proves the guards work and oracle_tier is simply absent (not None) in metrics.
        """
        from cohezion.compound.compound_health_oracle import CompoundHealthOracle
        from cohezion.compound.executor import CompoundExecutor
        from cohezion.compound.skill_refiner import SkillRefiner

        oracle = CompoundHealthOracle(window_size=10)
        # _last_assessment is None (default) — no assess() called yet

        sr = MagicMock(spec=SkillRefiner)
        sr._health_oracle = oracle
        sr._difficulty_estimator = MagicMock()
        sr._difficulty_estimator.predict_tier.return_value = "npu"

        executor = CompoundExecutor(MagicMock(), skill_refiner=sr)

        def fake_execute(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="cold start test",
            skill_name="NEW_SKILL",
            operation_type="generate",
            execute_fn=fake_execute,
        )

        # oracle_tier must not be in metrics when _last_assessment is None
        assert result.metrics.get("oracle_tier") is None or "oracle_tier" not in result.metrics, (
            "oracle_tier must be absent from metrics when oracle has no last_assessment"
        )


class TestSRSSkillRefinerPersistence:
    """SRS3 wiring in ExecutorFactory: restore_state on startup, save_state via atexit.

    Mirrors W2 (JourneyTracker identity lifecycle) and HO3 (CompoundHealthOracle).
    The discriminating test verifies that restore_state is CALLED (consumption), not
    merely that the SkillRefiner object exists (declaration).
    """

    def test_sr_wiring_restore_called_when_state_file_exists(self, tmp_path):
        """SRS3 discriminating: ExecutorFactory.create() calls restore_state when the
        state file exists, advancing _goal_epoch from 0 to the saved value.

        Wrong impl (restore not called) leaves _goal_epoch == 0 -> FAILS.
        """
        import json
        from unittest.mock import MagicMock, patch

        from cohezion.compound.executor_factory import ExecutorFactory
        from cohezion.compound.skill_refiner import SkillRefiner

        # Build a state file with non-default goal_epoch
        state_file = tmp_path / "skill_refiner_state.json"
        state_file.write_text(
            json.dumps(
                {
                    "goal_epoch": 5,
                    "goal_consecutive_hits": 2,
                    "session_goal": None,
                    "goal_call_tally": {},
                    "autodata_wins": {},
                    "process_rewards": {},
                    "erp_history": {},
                }
            )
        )

        mcp = MagicMock()

        with patch.object(SkillRefiner, "_DEFAULT_STATE_PATH", str(state_file)):
            executor = ExecutorFactory.create(mcp)

        # The SkillRefiner instance should have had restore_state called.
        # Access it via the executor's internal _skill_refiner attribute.
        sr = getattr(executor, "_skill_refiner", None)
        if sr is None:
            # Some executor variants store it differently
            sr = getattr(executor, "skill_refiner", None)

        assert sr is not None, "SkillRefiner must be wired into executor"
        assert sr._goal_epoch == 5, (
            f"restore_state must have been called; _goal_epoch expected 5, got {sr._goal_epoch}"
        )

    def test_sr_wiring_no_crash_when_state_file_absent(self, tmp_path):
        """SRS3 fail-open: ExecutorFactory.create() does not crash when state file absent."""
        from unittest.mock import MagicMock, patch

        from cohezion.compound.executor_factory import ExecutorFactory
        from cohezion.compound.skill_refiner import SkillRefiner

        absent_path = str(tmp_path / "nonexistent_state.json")
        mcp = MagicMock()

        # Should not raise
        with patch.object(SkillRefiner, "_DEFAULT_STATE_PATH", absent_path):
            executor = ExecutorFactory.create(mcp)

        assert executor is not None
