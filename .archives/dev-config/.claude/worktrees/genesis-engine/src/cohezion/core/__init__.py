"""Cohezion core infrastructure."""

from cohezion.core.config import CohezionConfig
from cohezion.core.context_engineering import ContextEngineeringInfrastructure
from cohezion.core.mcp_client import (
    MCPAuthenticationError,
    MCPClient,
    MCPClientError,
    MCPConfig,
    MCPConnectionError,
    MCPToolError,
    create_mcp_client,
)
from cohezion.core.vault_subscription import VaultEvent as VaultChangeEvent
from cohezion.core.vault_subscription import VaultSubscriptionClient


__all__ = [
    "CohezionConfig",
    "ContextEngineeringInfrastructure",
    "MCPAuthenticationError",
    "MCPClient",
    "MCPClientError",
    "MCPConfig",
    "MCPConnectionError",
    "MCPToolError",
    "VaultChangeEvent",
    "VaultSubscriptionClient",
    "create_mcp_client",
]
