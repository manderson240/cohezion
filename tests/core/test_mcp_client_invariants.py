"""Structural invariant tests for MCPClient async/sync contract.

These tests verify:
1. All vault_* methods are async (correct contract)
2. vault_search provides a sync wrapper for vault_find_relevant_context
3. skill_selector.py calls vault_find_relevant_context (not vault_search) — documents
   the known pattern so future changes are visible
4. The vault_search fallback handles RuntimeError from running event loop
"""
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.core.mcp_client import MCPClient, MCPConfig


def _make_client() -> MCPClient:
    cfg = MCPConfig(server_url="http://localhost:8360", api_key="test-key")
    return MCPClient(cfg)


class TestMCPClientAsyncContract:
    """Structural: all vault operation methods must be coroutines."""

    ASYNC_VAULT_METHODS = [
        "vault_read",
        "vault_write",
        "vault_delete",
        "vault_log_decision",
        "vault_find_relevant_context",
        "vault_edit",
        "vault_log_experiment",
        "vault_extract_pattern",
        "_call_tool",
        "connect",
        "close",
    ]

    @pytest.mark.parametrize("method_name", ASYNC_VAULT_METHODS)
    def test_method_is_coroutine(self, method_name):
        """Each listed method must be an async coroutine function."""
        client = _make_client()
        method = getattr(client, method_name)
        assert inspect.iscoroutinefunction(method), (
            f"MCPClient.{method_name} must be async (coroutine function)"
        )

    SYNC_WRAPPER_METHODS = [
        "vault_search",
        "vault_search_by_operation",
        "vault_write_sync",
        "vault_read_sync",
        "vault_delete_sync",
    ]

    @pytest.mark.parametrize("method_name", SYNC_WRAPPER_METHODS)
    def test_sync_wrapper_is_not_coroutine(self, method_name):
        """Synchronous wrapper methods must NOT be coroutines."""
        client = _make_client()
        method = getattr(client, method_name)
        assert not inspect.iscoroutinefunction(method), (
            f"MCPClient.{method_name} is intended as a sync wrapper — must NOT be async"
        )


class TestVaultSearchSyncWrapper:
    """vault_search wraps vault_find_relevant_context synchronously."""

    @patch("cohezion.core.mcp_client.httpx.AsyncClient")
    def test_vault_search_returns_list_when_no_loop_running(self, mock_client_class):
        """vault_search calls vault_find_relevant_context via asyncio.run and returns list."""
        mock_ac = MagicMock()
        mock_ac.aclose = AsyncMock()
        mock_ac.post = AsyncMock()
        mock_client_class.return_value = mock_ac

        client = _make_client()
        client._client = mock_ac
        client._session_id = "test-session"

        # Patch vault_find_relevant_context to return a list
        async def fake_find(query, **kw):
            return [{"path": "test.md", "category": "decision"}]

        with patch.object(client, "vault_find_relevant_context", side_effect=fake_find):
            result = client.vault_search("test query")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["category"] == "decision"

    def test_vault_search_returns_empty_on_exception(self):
        """vault_search returns [] and never raises when vault errors."""
        client = _make_client()

        async def raises(*a, **kw):
            raise RuntimeError("vault unavailable")

        # Mock asyncio.run to also raise RuntimeError
        with (
            patch.object(client, "vault_find_relevant_context", side_effect=raises),
            patch("asyncio.run", side_effect=RuntimeError("loop exists")),
            patch("asyncio.new_event_loop") as mock_loop_ctor,
        ):
            mock_loop = MagicMock()
            mock_loop.run_until_complete.side_effect = Exception("nested fail")
            mock_loop_ctor.return_value = mock_loop

            result = client.vault_search("test query")

        assert result == []

    def test_vault_search_by_operation_falls_back_to_flat_search(self):
        """vault_search_by_operation tries folder lookup then falls back."""
        client = _make_client()

        call_count = []

        def mock_vault_search(query, limit=10):
            call_count.append(query)
            # First call (folder lookup) returns empty; second (flat) returns results
            return [] if "operations/" in query else [{"path": "test"}]

        with patch.object(client, "vault_search", side_effect=mock_vault_search):
            results = client.vault_search_by_operation("codegen", limit=5)

        assert len(results) == 1
        assert len(call_count) == 2
        assert "operations/codegen" in call_count[0]


class TestSkillSelectorCallsVaultFindRelevantContext:
    """Document that skill_selector.py calls vault_find_relevant_context without await.

    This is a known pattern. These tests serve as a regression guard: if
    skill_selector.py is ever fixed to use vault_search (the sync wrapper),
    these tests would need to be updated — which would be a sign that the
    broader async-in-sync problem was addressed.
    """

    def test_skill_selector_uses_vault_search_sync_wrapper(self):
        """Verify skill_selector.py uses vault_search (sync wrapper), not vault_find_relevant_context.

        vault_find_relevant_context is async; calling it without await in synchronous
        code creates an unawaited coroutine (RuntimeWarning). vault_search is the correct
        synchronous wrapper that handles the async-in-sync case safely.
        """
        import ast
        from pathlib import Path

        selector_file = Path("src/cohezion/compound/skill_selector.py")
        if not selector_file.exists():
            pytest.skip("skill_selector.py not found")

        source = selector_file.read_text()
        tree = ast.parse(source)

        vault_search_calls = []
        vault_find_raw_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr == "vault_search":
                    vault_search_calls.append(node)
                elif node.attr == "vault_find_relevant_context":
                    vault_find_raw_calls.append(node)

        # Correct pattern: use vault_search (sync wrapper)
        assert len(vault_search_calls) > 0, (
            "skill_selector.py should call vault_search (sync wrapper), not vault_find_relevant_context"
        )
        # Should NOT call vault_find_relevant_context directly in sync code
        assert len(vault_find_raw_calls) == 0, (
            "skill_selector.py should NOT call vault_find_relevant_context directly — "
            "use vault_search (the sync wrapper) instead to avoid unawaited coroutine warnings"
        )


class TestVaultWriteSyncWrapper:
    """vault_write_sync closes coroutines properly to suppress RuntimeWarning."""

    def test_vault_write_sync_returns_none(self):
        """vault_write_sync is a sync void operation."""
        client = _make_client()
        client._client = MagicMock()
        client._session_id = "test"

        async def fake_write(path, content):
            pass

        with patch.object(client, "vault_write", side_effect=fake_write):
            result = client.vault_write_sync("test.md", "content")

        assert result is None

    def test_vault_write_sync_silences_exceptions(self):
        """vault_write_sync never raises regardless of vault errors."""
        client = _make_client()

        async def always_fails(path, content):
            raise RuntimeError("vault is offline")

        with patch.object(client, "vault_write", side_effect=always_fails):
            # Should NOT raise
            client.vault_write_sync("test.md", "content")

    def test_vault_write_sync_is_not_coroutine(self):
        """vault_write_sync must be a sync method."""
        client = _make_client()
        import inspect
        assert not inspect.iscoroutinefunction(client.vault_write_sync)


class TestVaultReadSyncWrapper:
    """vault_read_sync mirrors vault_write_sync semantics for reads."""

    def test_vault_read_sync_returns_value_when_no_loop_running(self):
        """vault_read_sync calls vault_read via asyncio.run and returns content."""
        client = _make_client()

        async def fake_read(path):
            return "file contents"

        with patch.object(client, "vault_read", side_effect=fake_read):
            result = client.vault_read_sync("test.md")

        assert result == "file contents"

    def test_vault_read_sync_returns_empty_on_exception(self):
        """vault_read_sync returns empty string and never raises when vault errors."""
        client = _make_client()

        async def always_fails(path):
            raise RuntimeError("vault is offline")

        with patch.object(client, "vault_read", side_effect=always_fails):
            # Should NOT raise
            result = client.vault_read_sync("test.md")

        assert result == ""

    def test_vault_read_sync_is_not_coroutine(self):
        """vault_read_sync must be a sync method."""
        client = _make_client()
        import inspect
        assert not inspect.iscoroutinefunction(client.vault_read_sync)


class TestVaultDeleteSyncWrapper:
    """vault_delete_sync is a fire-and-forget sync delete."""

    def test_vault_delete_sync_returns_none(self):
        """vault_delete_sync is a sync void operation."""
        client = _make_client()

        async def fake_delete(path):
            pass

        with patch.object(client, "vault_delete", side_effect=fake_delete):
            result = client.vault_delete_sync("test.md")

        assert result is None

    def test_vault_delete_sync_silences_exceptions(self):
        """vault_delete_sync never raises regardless of vault errors."""
        client = _make_client()

        async def always_fails(path):
            raise RuntimeError("vault is offline")

        with patch.object(client, "vault_delete", side_effect=always_fails):
            # Should NOT raise
            client.vault_delete_sync("test.md")

    def test_vault_delete_sync_is_not_coroutine(self):
        """vault_delete_sync must be a sync method."""
        client = _make_client()
        import inspect
        assert not inspect.iscoroutinefunction(client.vault_delete_sync)


class TestAdditionalSyncWrappers:
    """vault_read_sync and vault_delete_sync follow same pattern as vault_write_sync."""

    SYNC_VAULT_WRAPPERS = ["vault_read_sync", "vault_write_sync", "vault_delete_sync"]

    @pytest.mark.parametrize("method_name", SYNC_VAULT_WRAPPERS)
    def test_sync_wrapper_is_not_coroutine(self, method_name):
        """All _sync wrappers must be synchronous (not coroutines)."""
        client = _make_client()
        import inspect
        assert not inspect.iscoroutinefunction(getattr(client, method_name)), (
            f"{method_name} must NOT be async"
        )

    def test_vault_read_sync_returns_string_or_empty(self):
        """vault_read_sync returns str, never raises."""
        client = _make_client()
        async def fake_read(path):
            raise RuntimeError("vault offline")
        with patch.object(client, "vault_read", side_effect=fake_read):
            result = client.vault_read_sync("test.md")
        assert isinstance(result, str)
        assert result == ""

    def test_vault_delete_sync_silences_exceptions(self):
        """vault_delete_sync never raises."""
        client = _make_client()
        async def always_fails(path):
            raise RuntimeError("vault offline")
        with patch.object(client, "vault_delete", side_effect=always_fails):
            client.vault_delete_sync("test.md")  # Should NOT raise
