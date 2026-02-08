"""Cohezion core infrastructure."""

from cohezion.core.context_engineering import ContextEngineeringInfrastructure
from cohezion.core.mcp_client import (
    MCPClient,
    MCPClientError,
    MCPConfig,
    MCPConnectionError,
    MCPAuthenticationError,
    MCPToolError,
    create_mcp_client,
)
from cohezion.core.vault_subscription import VaultEvent as VaultChangeEvent
from cohezion.core.vault_subscription import VaultSubscriptionClient

__all__ = [
    "ContextEngineeringInfrastructure",
    "MCPClient",
    "MCPClientError",
    "MCPConfig",
    "MCPConnectionError",
    "MCPAuthenticationError",
    "MCPToolError",
    "VaultChangeEvent",
    "VaultSubscriptionClient",
    "create_mcp_client",
]
