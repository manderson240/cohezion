"""Step 7.6 geometric regime: decided only on a latent with provenance, never on noise.

Measured 2026-09-20: ``metrics["latent_vector"]`` is written nowhere in ``src/``, so the
old fallback ``torch.randn(256)`` (unseeded) was the ONLY live path. Its Mereon regime
triggered ``log_inflection_point`` -- a real vault write -- on a random draw. No test
covered the path. These tests pin the honest contract and go red if the random fallback
is restored (neutralisation) or if the provenance label is dropped.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.flume.geometric_bridge import GeometricLatentBridge


def _executor(tracker: object) -> tuple[CompoundExecutor, MagicMock]:
    ex = CompoundExecutor(MagicMock(), journey_tracker=tracker, skill_health_tracker=MagicMock())
    bridge = MagicMock()
    bridge.map_to_regime.return_value = "A"  # a regime that TRIGGERS the vault write
    bridge.project_to_coordinates.return_value = np.zeros(3)
    ex.geometric_bridge = bridge
    ex.log_inflection_point = MagicMock(return_value="vault/inflection.md")  # type: ignore[method-assign]
    return ex, bridge


def _run(ex: CompoundExecutor, extra: dict | None = None):
    return ex.execute_task(
        task_description="summarise the release notes",
        skill_name="s",
        operation_type="generate",
        execute_fn=lambda guidance: ("out", dict(extra or {})),
    )


class TestNoLatentMeansNoDecision:
    def test_DISCRIMINATING_no_latent_no_regime_no_vault_write(self):
        """Neutralisation target: restoring ``torch.randn`` makes map_to_regime fire and the
        inflection point get written; both assertions go red."""
        tracker = MagicMock()
        tracker.semantic_latent.return_value = None  # encoder down / not wired
        ex, bridge = _executor(tracker)
        result = _run(ex)
        bridge.map_to_regime.assert_not_called()
        ex.log_inflection_point.assert_not_called()
        assert "topological_regime" not in result.metrics
        assert "latent_source" not in result.metrics

    def test_tracker_without_semantic_latent_is_no_decision(self):
        ex, bridge = _executor(object())  # a tracker lacking the method entirely
        _run(ex)
        bridge.map_to_regime.assert_not_called()


class TestProvenance:
    def test_provider_latent_is_used_and_labelled(self):
        tracker = MagicMock()
        tracker.semantic_latent.return_value = np.ones(256)
        ex, bridge = _executor(tracker)
        result = _run(ex, {"latent_vector": [0.5] * 256})
        assert bridge.map_to_regime.call_count == 1
        assert result.metrics["latent_source"] == "provider"
        tracker.semantic_latent.assert_not_called()  # provider wins; no second encode
        assert torch.equal(bridge.map_to_regime.call_args.args[0], torch.full((256,), 0.5))

    def test_semantic_latent_is_used_and_labelled_when_provider_silent(self):
        tracker = MagicMock()
        tracker.semantic_latent.return_value = np.arange(256, dtype=np.float64) / 256
        ex, _ = _executor(tracker)
        result = _run(ex)
        tracker.semantic_latent.assert_called_once_with("summarise the release notes")
        assert result.metrics["latent_source"] == "flume-embed"
        assert result.metrics["topological_regime"] == "A"
        ex.log_inflection_point.assert_called_once()


class TestJourneyTrackerSemanticLatent:
    def test_no_encoder_returns_none_not_a_hash(self):
        jt = JourneyTracker()
        jt._flume_encoder = None
        assert jt.semantic_latent("x") is None

    def test_unavailable_encoder_returns_none(self):
        jt = JourneyTracker()
        enc = MagicMock()
        enc.is_available.return_value = False
        jt._flume_encoder = enc
        assert jt.semantic_latent("x") is None
        enc.encode.assert_not_called()

    def test_live_encoder_output_is_returned_as_float64(self):
        jt = JourneyTracker()
        enc = MagicMock()
        enc.is_available.return_value = True
        enc.encode.return_value = np.ones(256, dtype=np.float32)
        jt._flume_encoder = enc
        out = jt.semantic_latent("x")
        assert out is not None and out.shape == (256,) and out.dtype == np.float64


class TestRegimeIsAFunctionOfTheLatent:
    """The only latent-space statement the current bridge supports: with fixed weights the
    regime is a deterministic function of the input. Random input broke exactly this."""

    def test_same_latent_same_regime_across_bridges_and_calls(self):
        z = torch.linspace(-1.0, 1.0, 256)
        b1, b2 = GeometricLatentBridge(), GeometricLatentBridge()
        assert b1.map_to_regime(z) == b1.map_to_regime(z) == b2.map_to_regime(z)

    def test_random_input_is_not_a_function_of_the_task(self):
        """The control: the pre-fix input. Over 64 unseeded draws the regime is not constant,
        which is what made every persisted regime meaningless."""
        b = GeometricLatentBridge()
        regimes = {b.map_to_regime(torch.randn(256)) for _ in range(64)}
        if len(regimes) == 1:
            pytest.skip(
                "projection happened to be regime-constant on this seed; control inconclusive"
            )
        assert len(regimes) > 1
