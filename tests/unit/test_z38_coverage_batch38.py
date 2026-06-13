"""Coverage batch Z38: rewards_server, env_data_mcp, research_server_mcp, manager_models, manager_defaults, fleet."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: mcp/servers/rewards/server.py
# ---------------------------------------------------------------------------


class TestRewardsServer:
    def test_get_reward_status_default_agent(self):
        from cohezion.mcp.servers.rewards.server import get_reward_status

        result = asyncio.run(get_reward_status())
        assert result["agent_id"] == "me"
        assert "tier" in result
        assert "total_xp" in result

    def test_get_reward_status_custom_agent(self):
        from cohezion.mcp.servers.rewards.server import get_reward_status

        result = asyncio.run(get_reward_status(agent_id="agent-007"))
        assert result["agent_id"] == "agent-007"

    def test_get_reward_status_has_achievements(self):
        from cohezion.mcp.servers.rewards.server import get_reward_status

        result = asyncio.run(get_reward_status())
        assert isinstance(result["achievements"], list)
        assert len(result["achievements"]) > 0

    def test_get_reward_status_has_streak(self):
        from cohezion.mcp.servers.rewards.server import get_reward_status

        result = asyncio.run(get_reward_status())
        assert "streak" in result
        assert "current" in result["streak"]

    def test_get_reward_status_has_next_unlock(self):
        from cohezion.mcp.servers.rewards.server import get_reward_status

        result = asyncio.run(get_reward_status())
        assert "next_unlock" in result
        assert "name" in result["next_unlock"]

    def test_get_leaderboard_default_top(self):
        from cohezion.mcp.servers.rewards.server import get_leaderboard

        result = asyncio.run(get_leaderboard())
        assert isinstance(result, list)
        assert len(result) <= 10

    def test_get_leaderboard_top_1(self):
        from cohezion.mcp.servers.rewards.server import get_leaderboard

        result = asyncio.run(get_leaderboard(top=1))
        assert len(result) == 1
        assert result[0]["rank"] == 1

    def test_get_leaderboard_entries_have_xp(self):
        from cohezion.mcp.servers.rewards.server import get_leaderboard

        result = asyncio.run(get_leaderboard(top=3))
        for entry in result:
            assert "xp" in entry
            assert "agent" in entry


# ---------------------------------------------------------------------------
# Module 2: mcp/env_data_mcp.py
# ---------------------------------------------------------------------------


class TestEnvDataMcp:
    def test_fetch_noaa_data_returns_json_string(self):
        from cohezion.mcp.env_data_mcp import fetch_noaa_data

        result = asyncio.run(fetch_noaa_data())
        import json

        data = json.loads(result)
        assert "station" in data
        assert "measurements" in data

    def test_fetch_noaa_data_custom_station(self):
        from cohezion.mcp.env_data_mcp import fetch_noaa_data

        import json

        result = asyncio.run(fetch_noaa_data(station_id="GHCND:TEST123"))
        data = json.loads(result)
        assert data["station"] == "GHCND:TEST123"

    def test_fetch_noaa_data_has_temperature(self):
        from cohezion.mcp.env_data_mcp import fetch_noaa_data

        import json

        result = asyncio.run(fetch_noaa_data())
        data = json.loads(result)
        assert "TMAX" in data["measurements"]
        assert "TMIN" in data["measurements"]

    def test_fetch_copernicus_data_returns_json_string(self):
        from cohezion.mcp.env_data_mcp import fetch_copernicus_data

        result = asyncio.run(fetch_copernicus_data())
        import json

        data = json.loads(result)
        assert "region" in data
        assert "indices" in data

    def test_fetch_copernicus_data_custom_region(self):
        from cohezion.mcp.env_data_mcp import fetch_copernicus_data

        import json

        result = asyncio.run(fetch_copernicus_data(region="Sahel_Region"))
        data = json.loads(result)
        assert data["region"] == "Sahel_Region"

    def test_fetch_copernicus_data_has_ndvi(self):
        from cohezion.mcp.env_data_mcp import fetch_copernicus_data

        import json

        result = asyncio.run(fetch_copernicus_data())
        data = json.loads(result)
        assert "NDVI" in data["indices"]

    def test_fetch_copernicus_data_has_land_cover(self):
        from cohezion.mcp.env_data_mcp import fetch_copernicus_data

        import json

        result = asyncio.run(fetch_copernicus_data())
        data = json.loads(result)
        assert "land_cover_stats" in data
        assert "forest_cover_pct" in data["land_cover_stats"]


# ---------------------------------------------------------------------------
# Module 3: mcp/research_server_mcp.py
# ---------------------------------------------------------------------------


class TestResearchServerMcp:
    def _make_mock_server(self):
        mock_server = MagicMock()
        mock_server.search_arxiv.return_value = [{"title": "Paper 1", "id": "arxiv:123"}]
        mock_server.get_hf_trending.return_value = [{"title": "Model X"}]
        mock_server.list_research_channels.return_value = ["arxiv", "hf-trending"]
        return mock_server

    def test_search_arxiv_calls_server(self):
        from cohezion.mcp.research_server_mcp import search_arxiv

        mock_server = self._make_mock_server()
        with patch("cohezion.mcp.research_server_mcp.get_server", return_value=mock_server):
            result = asyncio.run(search_arxiv("transformers", limit=3))
        mock_server.search_arxiv.assert_called_once_with("transformers", 3)
        assert len(result) == 1
        assert result[0]["title"] == "Paper 1"

    def test_get_hf_trending_calls_server(self):
        from cohezion.mcp.research_server_mcp import get_hf_trending

        mock_server = self._make_mock_server()
        with patch("cohezion.mcp.research_server_mcp.get_server", return_value=mock_server):
            result = asyncio.run(get_hf_trending(limit=5))
        mock_server.get_hf_trending.assert_called_once_with(5)
        assert result[0]["title"] == "Model X"

    def test_list_research_channels_returns_list(self):
        from cohezion.mcp.research_server_mcp import list_research_channels

        mock_server = self._make_mock_server()
        with patch("cohezion.mcp.research_server_mcp.get_server", return_value=mock_server):
            result = asyncio.run(list_research_channels())
        assert "arxiv" in result


# ---------------------------------------------------------------------------
# Module 4: mcp/manager/models.py
# ---------------------------------------------------------------------------


class TestManagerModels:
    def test_mcp_server_config_basic(self):
        from cohezion.mcp.manager.models import MCPServerConfig

        cfg = MCPServerConfig(name="test", port=8360, entry_point="mod:app")
        assert cfg.name == "test"
        assert cfg.port == 8360
        assert cfg.status == "stopped"

    def test_mcp_server_config_to_dict_redacts_secrets(self):
        from cohezion.mcp.manager.models import MCPServerConfig

        cfg = MCPServerConfig(
            name="vault",
            port=8361,
            entry_point="mod:app",
            env_vars={"API_KEY": "secret123", "LOG_LEVEL": "INFO"},
        )
        d = cfg.to_dict()
        assert d["env_vars"]["API_KEY"] == "***REDACTED***"
        assert d["env_vars"]["LOG_LEVEL"] == "INFO"

    def test_mcp_server_config_to_dict_no_datetime_without_health_check(self):
        from cohezion.mcp.manager.models import MCPServerConfig

        cfg = MCPServerConfig(name="s", port=8362, entry_point="mod:app")
        d = cfg.to_dict()
        assert d["last_health_check"] is None

    def test_port_allocator_preferred_port(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        port = alloc.allocate("vault", preferred_port=8360)
        assert port == 8360

    def test_port_allocator_fallback_when_preferred_taken(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        alloc.allocate("server1", preferred_port=8360)
        port2 = alloc.allocate("server2", preferred_port=8360)
        assert port2 != 8360  # preferred was taken, got next available

    def test_port_allocator_same_server_returns_same_port(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        p1 = alloc.allocate("vault", preferred_port=8360)
        p2 = alloc.allocate("vault", preferred_port=8360)
        assert p1 == p2

    def test_port_allocator_release(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        alloc.allocate("vault", preferred_port=8360)
        assert alloc.release("vault") is True
        assert "vault" not in alloc.allocated.values()

    def test_port_allocator_release_unknown_returns_false(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        assert alloc.release("nonexistent") is False

    def test_port_allocator_get_server_port(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        alloc.allocate("vault", preferred_port=8360)
        assert alloc.get_server_port("vault") == 8360

    def test_port_allocator_get_server_port_missing(self):
        from cohezion.mcp.manager.models import PortAllocator

        alloc = PortAllocator()
        assert alloc.get_server_port("nobody") is None


# ---------------------------------------------------------------------------
# Module 5: mcp/manager/defaults.py
# ---------------------------------------------------------------------------


class TestManagerDefaults:
    def test_init_default_servers_registers_servers(self):
        from cohezion.mcp.manager.defaults import init_default_servers

        mock_manager = MagicMock()
        mock_manager.servers = {f"server_{i}": {} for i in range(12)}
        with patch("cohezion.mcp.manager.defaults.get_manager", return_value=mock_manager):
            init_default_servers()
        assert mock_manager.register_server.call_count >= 10

    def test_init_default_servers_registers_vault(self):
        from cohezion.mcp.manager.defaults import init_default_servers

        mock_manager = MagicMock()
        mock_manager.servers = {}
        with patch("cohezion.mcp.manager.defaults.get_manager", return_value=mock_manager):
            init_default_servers()

        call_names = [
            call.kwargs.get("name") or call.args[0]
            for call in mock_manager.register_server.call_args_list
        ]
        assert "vault" in call_names

    def test_init_default_servers_registers_research(self):
        from cohezion.mcp.manager.defaults import init_default_servers

        mock_manager = MagicMock()
        mock_manager.servers = {}
        with patch("cohezion.mcp.manager.defaults.get_manager", return_value=mock_manager):
            init_default_servers()

        call_names = [
            call.kwargs.get("name") or call.args[0]
            for call in mock_manager.register_server.call_args_list
        ]
        assert "research" in call_names


# ---------------------------------------------------------------------------
# Module 6: mcp/fleet.py
# ---------------------------------------------------------------------------


class TestMcpFleet:
    def test_run_server_sync_unknown_server_logs_error(self):
        from cohezion.mcp.fleet import run_server_sync

        with patch("cohezion.mcp.fleet.logger") as mock_logger:
            run_server_sync("no-such-server")
        mock_logger.error.assert_called()

    def test_run_server_sync_calls_module_main(self):
        from cohezion.mcp.fleet import run_server_sync

        mock_module = MagicMock()
        mock_module.main = MagicMock()
        with patch("importlib.import_module", return_value=mock_module):
            run_server_sync("bmad")
        mock_module.main.assert_called_once()

    def test_run_server_sync_calls_async_main(self):
        from cohezion.mcp.fleet import run_server_sync

        mock_module = MagicMock()

        async def async_main():
            pass

        mock_module.main = async_main
        with patch("importlib.import_module", return_value=mock_module):
            run_server_sync("bmad")  # Should not raise

    def test_run_server_sync_calls_app_run_on_no_main(self):
        from cohezion.mcp.fleet import run_server_sync

        mock_module = MagicMock(spec=["app"])
        mock_module.app = MagicMock()
        with patch("importlib.import_module", return_value=mock_module):
            run_server_sync("skills")
        mock_module.app.run.assert_called_once()

    def test_run_server_sync_http_transport_with_port(self):
        from cohezion.mcp.fleet import run_server_sync

        mock_module = MagicMock(spec=["app"])
        mock_module.app = MagicMock()
        with patch("importlib.import_module", return_value=mock_module):
            run_server_sync("skills", transport="http", port=9000)
        mock_module.app.run.assert_called_once_with(transport="http", host="0.0.0.0", port=9000)

    def test_run_server_sync_handles_import_exception(self):
        from cohezion.mcp.fleet import run_server_sync

        # The except block in run_server_sync swallows exceptions — verify no raise
        with patch("importlib.import_module", side_effect=RuntimeError("import-failed")):
            run_server_sync("bmad")  # must not raise

    def test_main_exits_on_all_server(self):
        from cohezion.mcp.fleet import main

        with patch("sys.argv", ["fleet", "all"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_dispatches_named_server(self):
        from cohezion.mcp.fleet import main

        with patch("sys.argv", ["fleet", "bmad"]):
            with patch("cohezion.mcp.fleet.run_server_sync") as mock_run:
                main()
        mock_run.assert_called_once_with("bmad", "stdio", None)
