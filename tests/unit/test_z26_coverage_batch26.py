"""Coverage batch Z26: history_flux, credentials, spectral_encoder, compound_client, mcp/shared/auth."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: flux/providers/history_flux.py
# ---------------------------------------------------------------------------


class TestHistoryFlux:
    def test_empty_history_returns_empty(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        blocks = asyncio.run(hf.get_context("summarize"))
        assert blocks == []

    def test_record_adds_entry(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("ran pytest tests/unit")
        assert len(hf._entries) == 1

    def test_record_stores_content(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("test content")
        assert hf._entries[0]["content"] == "test content"

    def test_record_stores_metadata(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("content", metadata={"step": 3})
        assert hf._entries[0]["metadata"] == {"step": 3}

    def test_record_default_empty_metadata(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("content")
        assert hf._entries[0]["metadata"] == {}

    def test_get_context_returns_matching_blocks(self):
        from cohezion.flux.providers.history_flux import HistoryFlux
        from cohezion.flux.types import FluxBlock

        hf = HistoryFlux()
        hf.record("ran pytest tests")
        hf.record("ran linter checks")
        blocks = asyncio.run(hf.get_context("pytest tests"))
        assert len(blocks) >= 1
        assert isinstance(blocks[0], FluxBlock)

    def test_get_context_keyword_overlap_scoring(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("pytest unit tests passed")
        hf.record("unrelated entry about cooking")
        blocks = asyncio.run(hf.get_context("pytest tests"))
        assert len(blocks) == 1  # "cooking" entry has zero overlap → excluded

    def test_get_context_sorted_by_score(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("pytest tests unit")  # 3 word overlap with "pytest unit tests"
        hf.record("pytest coverage")    # 1 word overlap
        blocks = asyncio.run(hf.get_context("pytest unit tests"))
        assert "pytest tests unit" in blocks[0].content

    def test_get_context_respects_top_k(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        for i in range(10):
            hf.record(f"test entry {i}")
        blocks = asyncio.run(hf.get_context("test", top_k=3))
        assert len(blocks) <= 3

    def test_get_context_uses_history_source(self):
        from cohezion.flux.providers.history_flux import HistoryFlux
        from cohezion.flux.types import FluxSource

        hf = HistoryFlux()
        hf.record("some content")
        blocks = asyncio.run(hf.get_context("some"))
        assert blocks[0].source == FluxSource.HISTORY

    def test_get_context_relevance_score_capped_at_one(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux()
        hf.record("a b c d e")
        blocks = asyncio.run(hf.get_context("a b c d e f"))  # more query words than content
        assert blocks[0].relevance_score <= 1.0

    def test_max_entries_ring_buffer(self):
        from cohezion.flux.providers.history_flux import HistoryFlux

        hf = HistoryFlux(max_entries=3)
        for i in range(5):
            hf.record(f"entry_{i}")
        assert len(hf._entries) == 3
        assert hf._entries[-1]["content"] == "entry_4"


# ---------------------------------------------------------------------------
# Module 2: security/credentials.py
# ---------------------------------------------------------------------------


class TestCredentialManager:
    def test_get_secret_from_vault(self):
        with patch("cohezion.security.credentials.get_vault") as mock_vault_fn:
            mock_vault = MagicMock()
            mock_vault.get_secret.return_value = "vault_secret"
            mock_vault_fn.return_value = mock_vault
            from cohezion.security.credentials import CredentialManager

            cm = CredentialManager()
            result = cm.get_secret("MY_KEY")
        assert result == "vault_secret"

    def test_get_secret_env_fallback_when_vault_empty(self):
        with patch("cohezion.security.credentials.get_vault") as mock_vault_fn:
            mock_vault = MagicMock()
            mock_vault.get_secret.return_value = None
            mock_vault_fn.return_value = mock_vault
            from cohezion.security.credentials import CredentialManager

            cm = CredentialManager()
            os.environ["Z26_TEST_SECRET"] = "env_value"
            try:
                result = cm.get_secret("MISSING", env_var="Z26_TEST_SECRET")
            finally:
                del os.environ["Z26_TEST_SECRET"]
        assert result == "env_value"

    def test_get_secret_uses_name_as_env_key_when_env_var_omitted(self):
        with patch("cohezion.security.credentials.get_vault") as mock_vault_fn:
            mock_vault = MagicMock()
            mock_vault.get_secret.return_value = None
            mock_vault_fn.return_value = mock_vault
            from cohezion.security.credentials import CredentialManager

            cm = CredentialManager()
            os.environ["Z26_FALLBACK_NAME"] = "by_name"
            try:
                result = cm.get_secret("Z26_FALLBACK_NAME")
            finally:
                del os.environ["Z26_FALLBACK_NAME"]
        assert result == "by_name"

    def test_get_secret_returns_none_when_both_missing(self):
        with patch("cohezion.security.credentials.get_vault") as mock_vault_fn:
            mock_vault = MagicMock()
            mock_vault.get_secret.return_value = None
            mock_vault_fn.return_value = mock_vault
            from cohezion.security.credentials import CredentialManager

            cm = CredentialManager()
            result = cm.get_secret("DEFINITELY_NOT_SET_xyz987")
        assert result is None

    def test_get_credentials_singleton(self):
        with patch("cohezion.security.credentials.get_vault") as mock_vault_fn:
            mock_vault = MagicMock()
            mock_vault_fn.return_value = mock_vault
            from cohezion.security import credentials

            credentials._manager = None  # reset
            c1 = credentials.get_credentials()
            c2 = credentials.get_credentials()
        assert c1 is c2


# ---------------------------------------------------------------------------
# Module 3: flume/spectral_encoder.py
# ---------------------------------------------------------------------------


class TestSpectralEncoder:
    def _make_state(self, ndvi=0.7, ndwi=0.3, sali=0.1, cloud=12.5, resolution="10m"):
        from cohezion.compound.copernicus_bridge import CopernicusState

        return CopernicusState(
            coordinates=(10.0, 45.0, 12.0, 47.0),
            time_range=("2024-01-01", "2024-01-31"),
            spectral_indices={"NDVI": ndvi, "NDWI": ndwi, "SALI": sali},
            cloud_cover=cloud,
            raw_metadata={"resolution": resolution},
        )

    def test_encode_spectral_state_returns_256d_vector(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        result = se.encode_spectral_state(self._make_state())
        assert result.shape == (256,)

    def test_encode_spectral_state_unit_normalized(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        result = se.encode_spectral_state(self._make_state())
        assert np.linalg.norm(result) == pytest.approx(1.0, abs=1e-5)

    def test_encode_spectral_state_deterministic(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        state = self._make_state()
        r1 = se.encode_spectral_state(state)
        r2 = se.encode_spectral_state(state)
        np.testing.assert_array_equal(r1, r2)

    def test_encode_spectral_state_20m_resolution_branch(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        state_10m = self._make_state(resolution="10m")
        state_20m = self._make_state(resolution="20m")
        result_10m = se.encode_spectral_state(state_10m)
        result_20m = se.encode_spectral_state(state_20m)
        # Different resolution → different input_vector → different latent
        assert not np.allclose(result_10m, result_20m)

    def test_encode_spectral_state_missing_indices_default_to_zero(self):
        from cohezion.compound.copernicus_bridge import CopernicusState
        from cohezion.flume.spectral_encoder import SpectralEncoder

        state = CopernicusState(
            coordinates=(0.0, 0.0, 1.0, 1.0),
            time_range=("2024-01-01", "2024-01-02"),
            spectral_indices={},  # all missing
        )
        se = SpectralEncoder(MagicMock())
        result = se.encode_spectral_state(state)
        assert result.shape == (256,)

    def test_integrate_with_text_unit_normalized(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        v1 = np.random.randn(256)
        v2 = np.random.randn(256)
        fused = se.integrate_with_text(v1, v2)
        assert np.linalg.norm(fused) == pytest.approx(1.0, abs=1e-5)

    def test_integrate_with_text_zero_vectors_returns_zero(self):
        from cohezion.flume.spectral_encoder import SpectralEncoder

        se = SpectralEncoder(MagicMock())
        z = np.zeros(256)
        fused = se.integrate_with_text(z, z)
        assert np.linalg.norm(fused) == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# Module 4: swarm/compound_client.py
# ---------------------------------------------------------------------------


class TestCompoundClient:
    def test_create_compound_client_returns_client(self):
        with (
            patch("cohezion.swarm.compound_client.ContextHarness", create=True),
            patch("cohezion.swarm.compound_client.SmartRouterAdapter", create=True),
            patch("cohezion.swarm.compound_client.SmartRouter", create=True),
            patch("cohezion.swarm.compound_client.TokenEfficientClient", create=True) as mock_tec,
        ):
            # Patch at the lazy-import target
            with (
                patch("cohezion.reliability.context_harness.ContextHarness", MagicMock(), create=True),
                patch("cohezion.swarm.model_adapter.SmartRouterAdapter", MagicMock(), create=True),
                patch("cohezion.swarm.smart_router.SmartRouter", MagicMock(), create=True),
                patch("cohezion.swarm.token_client.TokenEfficientClient", MagicMock(), create=True),
            ):
                from cohezion.swarm.compound_client import create_compound_client

                mock_client = MagicMock()
                with (
                    patch("cohezion.reliability.context_harness.ContextHarness"),
                    patch("cohezion.swarm.model_adapter.SmartRouterAdapter"),
                    patch("cohezion.swarm.smart_router.SmartRouter"),
                    patch("cohezion.swarm.token_client.TokenEfficientClient") as mock_tec_cls,
                ):
                    mock_tec_cls.return_value = mock_client
                    result = create_compound_client()
        assert result is mock_client

    def test_reset_compound_client_callable(self):
        from cohezion.swarm.compound_client import reset_compound_client

        assert callable(reset_compound_client)

    def test_get_compound_client_returns_singleton(self):
        from cohezion.swarm.compound_client import get_compound_client, reset_compound_client

        reset_compound_client()
        with (
            patch("cohezion.reliability.context_harness.ContextHarness"),
            patch("cohezion.swarm.model_adapter.SmartRouterAdapter"),
            patch("cohezion.swarm.smart_router.SmartRouter"),
            patch("cohezion.swarm.token_client.TokenEfficientClient") as mock_tec,
        ):
            mock_client = MagicMock()
            mock_tec.return_value = mock_client
            reset_compound_client()
            c1 = get_compound_client()
            c2 = get_compound_client()
        assert c1 is c2


# ---------------------------------------------------------------------------
# Module 5: mcp/shared/auth.py
# ---------------------------------------------------------------------------


class TestMcpSharedAuth:
    def setup_method(self):
        # Reset module-level cache before each test
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = None

    def test_get_mcp_api_key_returns_secret(self):
        with patch("cohezion.mcp.shared.auth.get_credentials") as mock_creds_fn:
            mock_creds = MagicMock()
            mock_creds.get_secret.return_value = "test-api-key-123"
            mock_creds_fn.return_value = mock_creds
            from cohezion.mcp.shared.auth import get_mcp_api_key

            key = get_mcp_api_key()
        assert key == "test-api-key-123"

    def test_get_mcp_api_key_cached(self):
        with patch("cohezion.mcp.shared.auth.get_credentials") as mock_creds_fn:
            mock_creds = MagicMock()
            mock_creds.get_secret.return_value = "cached-key"
            mock_creds_fn.return_value = mock_creds
            from cohezion.mcp.shared.auth import get_mcp_api_key

            get_mcp_api_key()
            get_mcp_api_key()
        mock_creds.get_secret.assert_called_once()  # only called once (lazy init)

    def test_api_key_middleware_allows_health_path(self):
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/health")
        mock_handler = AsyncMock(return_value=MagicMock())
        asyncio.run(api_key_middleware(request, mock_handler))
        mock_handler.assert_awaited_once()

    def test_api_key_middleware_allows_root_path(self):
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/")
        mock_handler = AsyncMock(return_value=MagicMock())
        asyncio.run(api_key_middleware(request, mock_handler))
        mock_handler.assert_awaited_once()

    def test_api_key_middleware_returns_500_when_no_key_configured(self):
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = None

        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        with patch("cohezion.mcp.shared.auth.get_credentials") as mock_creds_fn:
            mock_creds = MagicMock()
            mock_creds.get_secret.return_value = None  # no key configured
            mock_creds_fn.return_value = mock_creds
            request = make_mocked_request("GET", "/api/tools")
            mock_handler = AsyncMock()
            response = asyncio.run(api_key_middleware(request, mock_handler))
        assert response.status == 500

    def test_api_key_middleware_returns_401_when_no_auth_header(self):
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = "real-key"
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/api/tools")
        mock_handler = AsyncMock()
        response = asyncio.run(api_key_middleware(request, mock_handler))
        assert response.status == 401

    def test_api_key_middleware_returns_401_when_malformed_bearer(self):
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = "real-key"
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/api/tools", headers={"Authorization": "Token wrong"})
        mock_handler = AsyncMock()
        response = asyncio.run(api_key_middleware(request, mock_handler))
        assert response.status == 401

    def test_api_key_middleware_returns_403_when_wrong_key(self):
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = "real-key"
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/api/data", headers={"Authorization": "Bearer wrong-key"})
        mock_handler = AsyncMock()
        response = asyncio.run(api_key_middleware(request, mock_handler))
        assert response.status == 403

    def test_api_key_middleware_passes_with_correct_key(self):
        import cohezion.mcp.shared.auth as auth_mod

        auth_mod._mcp_api_key = "correct-key"
        from aiohttp.test_utils import make_mocked_request
        from cohezion.mcp.shared.auth import api_key_middleware

        request = make_mocked_request("GET", "/api/data", headers={"Authorization": "Bearer correct-key"})
        mock_handler = AsyncMock(return_value=MagicMock())
        asyncio.run(api_key_middleware(request, mock_handler))
        mock_handler.assert_awaited_once()
