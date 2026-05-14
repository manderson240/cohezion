"""Coverage batch Z37: apikey_middleware, local_registry, plasma_simulation, vliw_kernel, memory_manager."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: security/apikey_auth_middleware.py
# ---------------------------------------------------------------------------


class TestAPIKeyAuthMiddleware:
    def _make_request(self, path: str, token: str | None = None, has_client: bool = True):
        """Build a minimal mock Request."""
        req = MagicMock()
        req.url.path = path
        req.headers.get = MagicMock(side_effect=lambda k, d=None: token if k == "X-Agent-Token" else d)
        req.client = MagicMock(host="127.0.0.1") if has_client else None
        req.state = MagicMock()  # Ensure state is accessible
        return req

    def _make_middleware(self, auth_manager=None):
        from cohezion.security.apikey_auth_middleware import APIKeyAuthMiddleware

        mock_app = MagicMock()
        mock_mgr = auth_manager or MagicMock()
        return APIKeyAuthMiddleware(mock_app, auth_manager=mock_mgr)

    def test_dispatch_skips_health_path(self):
        mid = self._make_middleware()
        req = self._make_request("/health")
        mock_next = AsyncMock(return_value=MagicMock())
        asyncio.run(mid.dispatch(req, mock_next))
        mock_next.assert_awaited_once()

    def test_dispatch_skips_docs_path(self):
        mid = self._make_middleware()
        req = self._make_request("/docs")
        mock_next = AsyncMock(return_value=MagicMock())
        asyncio.run(mid.dispatch(req, mock_next))
        mock_next.assert_awaited_once()

    def test_dispatch_passes_non_api_path(self):
        mid = self._make_middleware()
        req = self._make_request("/other/path")
        mock_next = AsyncMock(return_value=MagicMock())
        asyncio.run(mid.dispatch(req, mock_next))
        mock_next.assert_awaited_once()

    def test_dispatch_returns_401_when_no_token(self):
        from fastapi.responses import JSONResponse

        mid = self._make_middleware()
        req = self._make_request("/api/tool", token=None)
        mock_next = AsyncMock()
        response = asyncio.run(mid.dispatch(req, mock_next))
        assert response.status_code == 401

    def test_dispatch_returns_401_when_invalid_token(self):
        mock_mgr = MagicMock()
        mock_mgr.validate_token.return_value = None  # invalid token

        mid = self._make_middleware(auth_manager=mock_mgr)
        req = self._make_request("/api/tool", token="bad-token-xyz")
        mock_next = AsyncMock()
        response = asyncio.run(mid.dispatch(req, mock_next))
        assert response.status_code == 401

    def test_dispatch_passes_with_valid_token(self):
        mock_cred = MagicMock()
        mock_cred.agent_id = "agent-1"
        mock_cred.permissions = ["read", "write"]
        mock_mgr = MagicMock()
        mock_mgr.validate_token.return_value = mock_cred

        mid = self._make_middleware(auth_manager=mock_mgr)
        req = self._make_request("/api/tool", token="valid-token")
        mock_next = AsyncMock(return_value=MagicMock())
        asyncio.run(mid.dispatch(req, mock_next))
        mock_next.assert_awaited_once()
        assert req.state.agent_id == "agent-1"

    def test_dispatch_attaches_credential_to_state(self):
        mock_cred = MagicMock()
        mock_cred.agent_id = "agent-2"
        mock_cred.permissions = ["read"]
        mock_mgr = MagicMock()
        mock_mgr.validate_token.return_value = mock_cred

        mid = self._make_middleware(auth_manager=mock_mgr)
        req = self._make_request("/api/data", token="token123")
        mock_next = AsyncMock(return_value=MagicMock())
        asyncio.run(mid.dispatch(req, mock_next))
        assert req.state.agent_permissions == ["read"]

    def test_require_permission_returns_403_when_missing(self):
        mid = self._make_middleware()
        req = MagicMock()
        req.state.agent_permissions = ["read"]
        req.state.agent_id = "a1"
        req.url.path = "/api/vault"

        protected_fn = AsyncMock(return_value={"ok": True})
        decorated = mid.require_permission("write")(protected_fn)
        response = asyncio.run(decorated(req))
        assert response.status_code == 403

    def test_require_permission_allows_when_present(self):
        mid = self._make_middleware()
        req = MagicMock()
        req.state.agent_permissions = ["read", "write"]
        req.state.agent_id = "a1"

        protected_fn = AsyncMock(return_value={"ok": True})
        decorated = mid.require_permission("write")(protected_fn)
        result = asyncio.run(decorated(req))
        assert result == {"ok": True}

    def test_require_permission_401_when_no_auth(self):
        mid = self._make_middleware()
        req = MagicMock()
        req.url.path = "/api/write"
        # state object without agent_permissions (using spec to prevent auto-creation)
        req.state = MagicMock(spec=[])  # spec=[] means no attributes → hasattr returns False

        protected_fn = AsyncMock()
        decorated = mid.require_permission("write")(protected_fn)
        response = asyncio.run(decorated(req))
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Module 2: core/local_registry.py
# ---------------------------------------------------------------------------


class TestLocalRegistry:
    def setup_method(self):
        import cohezion.core.local_registry as mod

        mod.LocalRegistry._instance = None

    def test_refresh_parses_ollama_output(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="NAME       SIZE\nollama:latest     5GB\nphi3:mini    4GB\n",
            )
            reg = LocalRegistry()
        assert "ollama:latest" in reg.available_models

    def test_refresh_handles_failed_ollama(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            reg = LocalRegistry()
        assert reg.available_models == set()

    def test_refresh_handles_exception(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("subprocess failed")
            reg = LocalRegistry()
        assert reg.available_models == set()

    def test_is_available_exact_match(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\nphi3:mini   4GB\n")
            reg = LocalRegistry()
        assert reg.is_available("phi3:mini") is True

    def test_is_available_prefix_match(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\nphi3:mini   4GB\n")
            reg = LocalRegistry()
        assert reg.is_available("phi3") is True

    def test_is_available_returns_false_when_missing(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\nphi3:mini\n")
            reg = LocalRegistry()
        assert reg.is_available("gpt4") is False

    def test_get_best_available_returns_first_match(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\nphi3:mini\nllama3\n")
            reg = LocalRegistry()
        result = reg.get_best_available_local(["llama3", "phi3:mini"])
        assert result == "llama3"

    def test_get_best_available_returns_fallback(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\nphi3:mini\n")
            reg = LocalRegistry()
        result = reg.get_best_available_local(["gpt4", "claude"])
        assert result == "phi3:mini"

    def test_get_best_available_hope_and_pray(self):
        """Test the fallback-of-last-resort path when no models available."""
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\n")  # empty roster
            reg = LocalRegistry()
        # No preferred and no fallbacks → returns "phi3:mini" unconditionally
        result = reg.get_best_available_local(["gpt4"])
        assert result == "phi3:mini"

    def test_get_local_registry_function(self):
        from cohezion.core.local_registry import get_local_registry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\n")
            reg = get_local_registry()
        assert reg is not None

    def test_check_capacity_returns_bool(self):
        from cohezion.core.local_registry import LocalRegistry

        with patch("cohezion.core.local_registry.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME\n")
            with patch("cohezion.core.local_registry.shutil.disk_usage") as mock_du:
                mock_du.return_value = (1000 * 1024**3, 800 * 1024**3, 200 * 1024**3)
                reg = LocalRegistry()
                result = reg.check_capacity(min_gb=20.0)
        assert result is True


# ---------------------------------------------------------------------------
# Module 3: mcp/servers/plasma/simulation.py
# ---------------------------------------------------------------------------


class TestPlasmaSimulation:
    def test_create_particle(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        p = sim.create_particle("electron", [1.0, 2.0, 3.0], [0.1, 0.2, 0.3], charge=-1.0, mass=9.11e-31)
        assert p.species == "electron"
        assert len(sim.particles) == 1

    def test_step_advances_time(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        result = sim.step()
        assert result["time"] == pytest.approx(0.01)

    def test_step_moves_particle(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        sim.create_particle("proton", [1.0, 1.0, 1.0], [1.0, 0.0, 0.0], charge=1.0, mass=1.67e-27)
        sim.step()
        # Position should have moved by velocity * time_step
        assert sim.particles[0].position[0] != pytest.approx(1.0)

    def test_generate_exotic_vacuum_object_probability(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        with patch("cohezion.mcp.servers.plasma.simulation.np.random.random", return_value=0.05):
            obj = sim.generate_exotic_vacuum_object()
        assert obj is not None

    def test_generate_exotic_vacuum_object_no_spawn(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        with patch("cohezion.mcp.servers.plasma.simulation.np.random.random", return_value=0.5):
            obj = sim.generate_exotic_vacuum_object()
        assert obj is None

    def test_get_hiho_agents_returns_list(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation()
        agents = sim.get_hiho_agents()
        assert len(agents) == 3
        assert all("name" in a for a in agents)

    def test_get_field_at(self):
        from cohezion.mcp.servers.plasma.simulation import PlasmaSimulation

        sim = PlasmaSimulation(grid_size=16)
        result = sim.get_field_at([1.0, 2.0, 3.0])
        assert "electric_field" in result
        assert "magnetic_field" in result

    def test_get_simulation_singleton_pattern(self):
        from cohezion.mcp.servers.plasma.simulation import get_simulation

        s1 = get_simulation("test-sim-id")
        s2 = get_simulation("test-sim-id")
        assert s1 is s2


# ---------------------------------------------------------------------------
# Module 4: flume/vliw_kernel_sim.py
# ---------------------------------------------------------------------------


class TestVLIWSimulator:
    def test_hash_round_deterministic(self):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator()
        result1 = sim.hash_round(12345)
        result2 = sim.hash_round(12345)
        assert result1 == result2

    def test_hash_round_different_inputs(self):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator()
        assert sim.hash_round(0) != sim.hash_round(1)

    def test_hash_round_stays_within_32bit(self):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator()
        result = sim.hash_round(0xFFFFFFFF)
        assert 0 <= result <= 0xFFFFFFFF

    def test_run_vectorized_produces_output(self, capsys):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator(items=32, rounds=4)
        sim.run_vectorized()
        captured = capsys.readouterr()
        assert "VLIW KERNEL SIMULATION REPORT" in captured.out

    def test_run_vectorized_bit_exact(self, capsys):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator(items=32, rounds=4)
        sim.run_vectorized()
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out

    def test_run_vectorized_failure_path(self, capsys):
        from cohezion.flume.vliw_kernel_sim import VLIWSimulator

        sim = VLIWSimulator(items=32, rounds=4)
        # Make vectorized produce different output by breaking hash_round just during run
        # Patch np.all to return False to trigger failure path
        with patch("cohezion.flume.vliw_kernel_sim.np.all", return_value=False):
            with patch("cohezion.flume.vliw_kernel_sim.np.where", return_value=([0, 1, 2],)):
                sim.run_vectorized()
        captured = capsys.readouterr()
        assert "FAILURE" in captured.out
