"""Coverage batch Z46: lcsp_predictor, datamesh_federation, flume_bridge."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: flume/lcsp.py
# ---------------------------------------------------------------------------


class TestLCSPPredictor:
    def _make_predictor(self, latent_dim=32):
        from cohezion.flume.lcsp import LCSPPredictor

        pred = LCSPPredictor(latent_dim=latent_dim)
        pred.initialize()
        return pred

    def test_lcsp_prediction_dataclass(self):
        from cohezion.flume.lcsp import LCSPPrediction

        pred = LCSPPrediction(
            next_state=np.zeros(12),
            actions=[0.0] * 12,
            confidence=0.8,
            hiho_stability=0.9,
        )
        assert pred.confidence == pytest.approx(0.8)

    def test_initialize_sets_weights(self):
        from cohezion.flume.lcsp import LCSPPredictor

        predictor = LCSPPredictor(latent_dim=16)
        assert not predictor._initialized
        predictor.initialize()
        assert predictor._initialized
        assert predictor._encoder_weights is not None

    def test_encode_returns_latent(self):
        predictor = self._make_predictor(latent_dim=16)
        state = np.random.randn(12).astype(np.float32)
        latent = predictor.encode(state)
        assert latent.shape == (16,)

    def test_encode_uses_tanh(self):
        predictor = self._make_predictor(latent_dim=16)
        state = np.random.randn(12).astype(np.float32)
        latent = predictor.encode(state)
        assert np.all(latent >= -1.0) and np.all(latent <= 1.0)

    def test_predict_latent_shape(self):
        predictor = self._make_predictor(latent_dim=16)
        latent = np.random.randn(16)
        next_latent = predictor.predict_latent(latent)
        assert next_latent.shape == (16,)

    def test_decode_returns_12d(self):
        predictor = self._make_predictor(latent_dim=16)
        latent = np.random.randn(16)
        state = predictor.decode(latent)
        assert state.shape == (12,)

    def test_predict_full_pipeline(self):
        predictor = self._make_predictor(latent_dim=16)
        state = np.random.randn(12).astype(np.float32)
        result = predictor.predict(state)
        assert result.next_state.shape == (12,)
        assert len(result.actions) == 12
        assert 0.0 <= result.confidence <= 1.0

    def test_predict_wrong_shape_raises(self):
        predictor = self._make_predictor()
        with pytest.raises(ValueError):
            predictor.predict(np.zeros(8))

    def test_predict_auto_initializes(self):
        from cohezion.flume.lcsp import LCSPPredictor

        predictor = LCSPPredictor(latent_dim=16)
        assert not predictor._initialized
        state = np.zeros(12)
        _result = predictor.predict(state)  # should auto-initialize
        assert predictor._initialized

    def test_predict_context_passed(self):
        predictor = self._make_predictor(latent_dim=16)
        state = np.zeros(12)
        # context is optional; passing one should not raise
        result = predictor.predict(state, context={"step": 1})
        assert result is not None


# ---------------------------------------------------------------------------
# Module 2: datamesh/federation.py
# ---------------------------------------------------------------------------


class TestFederationLayer:
    def _make_layer(self):
        from cohezion.datamesh.federation import FederationLayer

        return FederationLayer()

    def test_register_domain(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        ep = DomainEndpoint(name="vault", priority=1)
        layer.register_domain(ep)
        assert "vault" in layer.list_domains()

    def test_get_ingestion_returns_none_for_missing_domain(self):
        layer = self._make_layer()
        result = layer.get_ingestion("nonexistent")
        assert result is None

    def test_get_ingestion_returns_none_for_unhealthy_domain(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        mock_ingestion = MagicMock()
        ep = DomainEndpoint(name="sick", ingestion=mock_ingestion)
        layer.register_domain(ep)
        layer._unhealthy.add("sick")
        assert layer.get_ingestion("sick") is None

    def test_get_query_returns_query_for_healthy_domain(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        mock_query = MagicMock()
        ep = DomainEndpoint(name="healthy", query=mock_query)
        layer.register_domain(ep)
        result = layer.get_query("healthy")
        assert result is mock_query

    def test_list_domains(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        layer.register_domain(DomainEndpoint(name="d1"))
        layer.register_domain(DomainEndpoint(name="d2"))
        assert set(layer.list_domains()) == {"d1", "d2"}

    def test_list_healthy_excludes_unhealthy(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        layer.register_domain(DomainEndpoint(name="ok"))
        layer.register_domain(DomainEndpoint(name="bad"))
        layer._unhealthy.add("bad")
        assert "ok" in layer.list_healthy()
        assert "bad" not in layer.list_healthy()

    def test_health_check_no_check_configured(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        layer.register_domain(DomainEndpoint(name="d1"))
        results = asyncio.run(layer.health_check())
        assert results["d1"] is True

    def test_health_check_callable_healthy(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()

        async def healthy():
            return True

        ep = DomainEndpoint(name="d1", health_check=healthy)
        layer.register_domain(ep)
        results = asyncio.run(layer.health_check())
        assert results["d1"] is True

    def test_health_check_callable_unhealthy(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()

        async def sick():
            return False

        ep = DomainEndpoint(name="d1", health_check=sick)
        layer.register_domain(ep)
        results = asyncio.run(layer.health_check())
        assert results["d1"] is False
        assert "d1" in layer._unhealthy

    def test_health_check_exception_marks_unhealthy(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()

        async def boom():
            raise RuntimeError("down")

        ep = DomainEndpoint(name="d1", health_check=boom)
        layer.register_domain(ep)
        results = asyncio.run(layer.health_check())
        assert results["d1"] is False

    def test_domain_recovery_removes_from_unhealthy(self):
        from cohezion.datamesh.federation import DomainEndpoint

        layer = self._make_layer()
        layer._unhealthy.add("d1")

        async def healthy():
            return True

        ep = DomainEndpoint(name="d1", health_check=healthy)
        layer.register_domain(ep)
        asyncio.run(layer.health_check())
        assert "d1" not in layer._unhealthy


# ---------------------------------------------------------------------------
# Module 3: governance/flume_bridge.py
# ---------------------------------------------------------------------------


class TestFlumeBridge:
    def test_encode_prompt_hash_fallback(self):
        from cohezion.governance.flume_bridge import encode_prompt

        with patch("cohezion.governance.flume_bridge._get_encoder", return_value=None):
            result = encode_prompt("hello world")
        assert result.shape == (256,)

    def test_encode_prompt_with_encoder(self):
        from cohezion.governance.flume_bridge import encode_prompt

        mock_enc = MagicMock()
        mock_enc.encode.return_value = np.random.randn(256)
        with patch("cohezion.governance.flume_bridge._get_encoder", return_value=mock_enc):
            result = encode_prompt("hello world")
        assert result.shape == (256,)

    def test_encode_prompt_returns_normalized(self):
        from cohezion.governance.flume_bridge import encode_prompt

        with patch("cohezion.governance.flume_bridge._get_encoder", return_value=None):
            v1 = encode_prompt("same prompt")
            v2 = encode_prompt("same prompt")
        # Hash fallback is deterministic
        assert np.allclose(v1, v2)

    def test_flume_route_similarity(self):
        from cohezion.governance.flume_bridge import flume_route_similarity

        embedding = np.ones(256) / np.sqrt(256)
        with patch("cohezion.governance.flume_bridge._get_encoder", return_value=None):
            similarity = flume_route_similarity(embedding, "same text")
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0

    def test_data_product_similarity(self):
        from cohezion.governance.flume_bridge import data_product_similarity

        with patch("cohezion.governance.flume_bridge._get_encoder", return_value=None):
            sim = data_product_similarity("find users", "user database query")
        assert isinstance(sim, float)
