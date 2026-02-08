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
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    inbox_debounce_seconds: float = field(
        default_factory=lambda: float(os.environ.get("INBOX_DEBOUNCE", "2.0"))
    )
    inbox_model: str = field(
        default_factory=lambda: os.environ.get(
            "INBOX_MODEL", "claude-sonnet-4-5-20250929"
        )
    )
    watcher_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("WATCHER_ENABLED", "true").lower() == "true"
        )
    )
    sse_heartbeat_seconds: int = field(
        default_factory=lambda: int(os.environ.get("SSE_HEARTBEAT", "15"))
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls()
