"""Tests for compound/post_execution.py.

Covers PostExecutionOrchestrator pipeline execution and all step runners.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.post_execution import PostExecutionOrchestrator


@pytest.mark.asyncio
async def test_post_execution_orchestrator_run_success():
    """[P0] Should run post-execution orchestrator with no errors."""
    mock_executor = MagicMock()
    mock_executor._enable_alignment_analysis = True
    mock_executor._degradation_mode = False
    mock_executor._drr_generator = None
    mock_executor.alignment_analyzer = MagicMock()
    mock_alignment = MagicMock()
    mock_alignment.misalignment_score = 0.1
    mock_alignment.intent_match_score = 0.8
    mock_alignment.constraint_satisfaction = 0.9
    mock_alignment.criteria_satisfaction = 0.9
    mock_alignment.violations = []
    mock_alignment.failures = []
    mock_alignment.issues = []
    mock_alignment.should_retry = False
    mock_executor.alignment_analyzer.analyze_alignment.return_value = mock_alignment
    mock_executor.skill_refiner = MagicMock()
    mock_executor.skill_refiner.refine.return_value = "/path/to/refined/skill"
    mock_executor.inflection_detector = MagicMock()

    # Mock inflect detection returning low severity anomaly
    mock_anomaly = MagicMock()
    mock_anomaly.severity.value = "info"
    mock_anomaly.score = 0.1
    mock_anomaly.issues = []
    mock_anomaly.recommendations = []
    mock_executor.inflection_detector.detect_anomaly.return_value = mock_anomaly

    mock_executor.logger = MagicMock()
    mock_executor.logger.compute_coherence.return_value = 0.5
    mock_executor.logger.extract_execution_pattern.return_value = "/path/to/extracted/pattern"

    orchestrator = PostExecutionOrchestrator(executor=mock_executor)

    metrics = {}
    decision_paths = []

    # Mocks for imported modules to prevent side effects in tests
    with (
        patch("cohezion.governance.autonomy_engine.get_autonomy_engine"),
        patch("cohezion.physics.natural_capital.NaturalCapitalValuation") as mock_nc_class,
        patch("cohezion.physics.cosmogony.get_cosmogony") as mock_get_cosmo,
        patch("cohezion.universe.engine.AxiomaticState"),
        patch("cohezion.universe.spatial_phonons.SpatialPhononsEngine"),
        patch("cohezion.flume.morphospace.MorphospaceMapper"),
        patch("cohezion.flume.lcsp.LCSPPredictor"),
        patch("cohezion.simulation.emergent_detector.EmergentDetector"),
        patch("cohezion.physics.bec_bridge.BECState"),
        patch("cohezion.physics.bec_bridge.MercuryLattice"),
        patch("cohezion.physics.colibre_bridge.AgentAsEVO"),
        patch("cohezion.physics.colibre_bridge.ColibreState"),
        patch("cohezion.physics.mhd_plasma.MHDEquilibrium"),
        patch("cohezion.physics.mhd_plasma.BismuthDiamagnet"),
        patch("cohezion.physics.toroidal_moment.FractalToroidalMoment"),
        patch("cohezion.physics.tensor_metric_engineering.TensorMetricEngineering"),
        patch("cohezion.physics.sarfatti_bridge.SarfattiBackAction"),
        patch("cohezion.physics.sarfatti_bridge.QuarkGluonPlasma"),
        patch("cohezion.physics.lenr.LENRHamiltonian"),
        patch("cohezion.physics.ionic_cluster.IonicClusterState"),
    ):
        mock_nc_val = MagicMock()
        mock_nc_val.evaluate.return_value = SimpleNamespace(
            habitat_quality=0.8, total_natural_capital=100.0
        )
        mock_nc_class.return_value = mock_nc_val

        mock_get_cosmo.return_value.generate_12d_state.return_value = [0.5] * 12
        mock_get_cosmo.return_value.state.to_dict.return_value = {
            "temperature": 1.0,
            "symmetry": "U(1)",
            "stage": 1,
            "transitions": [],
            "order_parameters": {},
            "fisher_eigenvalue_max": 1.0,
            "landau_free_energy": 0.0,
        }

        result_paths = await orchestrator.run(
            success=True,
            output="mock execution completed successfully",
            metrics=metrics,
            duration_seconds=2.5,
            token_metrics={"prompt_tokens": 100, "completion_tokens": 200},
            experiment_path="/path/to/experiment",
            decision_paths=decision_paths,
            task_description="Evaluate dynamic agent swarm trajectory",
            skill_name="test-skill",
            operation_type="generate",
            project="test-project",
            parsed_request={"key": "request"},
            universe_journey_id="journey-123",
            _task_profile={"profile": "test"},
            _context_budget={"budget": 100},
        )

        assert isinstance(result_paths, list)
        assert "/path/to/refined/skill" in result_paths
        assert "/path/to/extracted/pattern" in result_paths
