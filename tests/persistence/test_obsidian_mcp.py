from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import torch

from cohezion.persistence.obsidian_mcp import ObsidianMemoryMCP
from cohezion.universe.triune_manifold import TriuneState


@pytest.fixture
def triune_state():
    return TriuneState(doer=torch.randn(12), thinker=torch.randn(512), knower=torch.randn(2048))


@pytest.mark.asyncio
async def test_obsidian_mcp_initialization():
    """Test that the MCP client initializes correctly."""
    client = ObsidianMemoryMCP(server_url="stdio://cloud-vault-mcp")
    assert client.server_url == "stdio://cloud-vault-mcp"


@pytest.mark.asyncio
async def test_store_state_summary_success(triune_state):
    """Test that store_state_summary correctly formats and calls vault_write."""
    mock_session = AsyncMock()
    # Mock initialize and call_tool
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value="Successfully wrote to path")

    # Properly mock stdio_client context manager
    mock_stdio = MagicMock()
    mock_stdio.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
    mock_stdio.__aexit__ = AsyncMock(return_value=None)

    with patch("cohezion.persistence.obsidian_mcp.stdio_client", return_value=mock_stdio):
        with patch("cohezion.persistence.obsidian_mcp.ClientSession") as mock_session_class:
            mock_session_class.return_value.__aenter__.return_value = mock_session

            client = ObsidianMemoryMCP()
            await client.store_state_summary(
                trajectory_id="test_traj_456", state=triune_state, coherence=0.5
            )

            # Verify call_tool was invoked with vault_write
            mock_session.call_tool.assert_called_once()
            args, _ = mock_session.call_tool.call_args
            assert args[0] == "vault_write"

            tool_args = args[1]
            assert "trajectories/test_traj_456.md" in tool_args["path"]
            assert "# Trajectory Summary: test_traj_456" in tool_args["content"]
            # Check for formatted coherence
            assert "**Coherence**: 0.5000" in tool_args["content"]


@pytest.mark.asyncio
async def test_store_state_summary_failure(triune_state):
    """Test handling of tool call failure."""
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.call_tool = AsyncMock(side_effect=Exception("Tool Execution Error"))

    mock_stdio = MagicMock()
    mock_stdio.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
    mock_stdio.__aexit__ = AsyncMock(return_value=None)

    with patch("cohezion.persistence.obsidian_mcp.stdio_client", return_value=mock_stdio):
        with patch("cohezion.persistence.obsidian_mcp.ClientSession") as mock_session_class:
            mock_session_class.return_value.__aenter__.return_value = mock_session

            client = ObsidianMemoryMCP()

            # In Python 3.11+, ExceptionGroup might be raised by anyio TaskGroups
            # but here we're mocking the call_tool directly.
            with pytest.raises(Exception, match="Tool Execution Error"):
                await client.store_state_summary(
                    trajectory_id="test_traj_err", state=triune_state, coherence=0.5
                )
