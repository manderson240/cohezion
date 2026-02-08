"""Server configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """Configuration for the Cloud Vault MCP Server."""

    vault_path: str = field(
        default_factory=lambda: os.environ.get("VAULT_PATH", "/vault")
    )
    api_key: str = field(default_factory=lambda: os.environ.get("MCP_API_KEY", ""))
    host: str = field(default_factory=lambda: os.environ.get("MCP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("MCP_PORT", "8360")))
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get("CORS_ORIGINS", "*").split(",")
    )
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "info"))

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls()
