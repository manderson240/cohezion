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
            "INBOX_MODEL", "claude-haiku-4-5-20251001"
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
    sheets_spreadsheet_id: str = field(
        default_factory=lambda: os.environ.get(
            "SHEETS_SPREADSHEET_ID",
            "1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk",
        )
    )
    sheets_quota_project: str = field(
        default_factory=lambda: os.environ.get(
            "SHEETS_QUOTA_PROJECT", "cohezion-477604"
        )
    )
    sheets_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("SHEETS_ENABLED", "true").lower() == "true"
        )
    )
    allowed_hosts: list[str] = field(
        default_factory=lambda: os.environ.get("ALLOWED_HOSTS", "*").split(",")
    )
    tls_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("TLS_ENABLED", "false").lower() == "true"
        )
    )
    tls_cert_path: str = field(
        default_factory=lambda: os.environ.get("TLS_CERT_PATH", "")
    )
    tls_key_path: str = field(
        default_factory=lambda: os.environ.get("TLS_KEY_PATH", "")
    )
    tls_hsts_max_age: int = field(
        default_factory=lambda: int(
            os.environ.get("TLS_HSTS_MAX_AGE", "31536000")
        )
    )
    tls_allowed_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "TLS_ALLOWED_ORIGINS", "https://localhost,https://127.0.0.1"
        ).split(",")
    )
    surrealdb_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("SURREALDB_ENABLED", "true").lower() == "true"
        )
    )
    surrealdb_url: str = field(
        default_factory=lambda: os.environ.get("SURREALDB_URL", "http://localhost:8000")
    )
    surrealdb_namespace: str = field(
        default_factory=lambda: os.environ.get("SURREALDB_NAMESPACE", "cohezion")
    )
    surrealdb_database: str = field(
        default_factory=lambda: os.environ.get("SURREALDB_DATABASE", "vault")
    )
    surrealdb_username: str = field(
        default_factory=lambda: os.environ.get("SURREALDB_USERNAME", "root")
    )
    surrealdb_password: str = field(
        default_factory=lambda: os.environ.get("SURREALDB_PASSWORD", "root")
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls()
