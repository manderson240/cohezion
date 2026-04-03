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
        default_factory=lambda: os.environ.get("TLS_ENABLED", "false").lower() == "true"
    )
    tls_cert_path: str = field(
        default_factory=lambda: os.environ.get("TLS_CERT_PATH", "")
    )
    tls_key_path: str = field(
        default_factory=lambda: os.environ.get("TLS_KEY_PATH", "")
    )
    tls_hsts_max_age: int = field(
        default_factory=lambda: int(os.environ.get("TLS_HSTS_MAX_AGE", "31536000"))
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
    health_check_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("HEALTH_CHECK_ENABLED", "true").lower() == "true"
        )
    )
    health_check_timeout: float = field(
        default_factory=lambda: float(os.environ.get("HEALTH_CHECK_TIMEOUT", "5"))
    )
    health_check_interval: int = field(
        default_factory=lambda: int(os.environ.get("HEALTH_CHECK_INTERVAL", "60"))
    )
    ollama_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_URL", "http://localhost:11434")
    )
    ollama_timeout: float = field(
        default_factory=lambda: float(os.environ.get("OLLAMA_TIMEOUT", "30"))
    )
    ollama_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("OLLAMA_ENABLED", "true").lower() == "true"
        )
    )
    sheets_research_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("SHEETS_RESEARCH_ENABLED", "false").lower() == "true"
        )
    )
    sheets_research_poll_interval: int = field(
        default_factory=lambda: int(
            os.environ.get("SHEETS_RESEARCH_POLL_INTERVAL", "300")
        )
    )
    sheets_research_batch_size: int = field(
        default_factory=lambda: int(os.environ.get("SHEETS_RESEARCH_BATCH_SIZE", "10"))
    )
    sheets_research_max_concurrent_agents: int = field(
        default_factory=lambda: int(
            os.environ.get("SHEETS_RESEARCH_MAX_CONCURRENT_AGENTS", "4")
        )
    )
    sheets_research_agent_timeout: int = field(
        default_factory=lambda: int(
            os.environ.get("SHEETS_RESEARCH_AGENT_TIMEOUT", "300")
        )
    )
    sheets_research_work_queue_db: str = field(
        default_factory=lambda: os.environ.get(
            "SHEETS_RESEARCH_DB",
            "/var/lib/sheets-research/work_queue.db",
        )
    )
    vault_search_cache_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("VAULT_SEARCH_CACHE_ENABLED", "true").lower() == "true"
        )
    )
    vault_search_cache_ttl_seconds: float = field(
        default_factory=lambda: float(
            os.environ.get("VAULT_SEARCH_CACHE_TTL_SECONDS", "60")
        )
    )
    googlesql_url: str = field(
        default_factory=lambda: os.environ.get("GOOGLESQL_URL", "http://localhost:8081")
    )
    sheets_enabled: bool = field(
        default_factory=lambda: os.environ.get("SHEETS_ENABLED", "true").lower() == "true"
    )
    surrealdb_enabled: bool = field(
        default_factory=lambda: os.environ.get("SURREALDB_ENABLED", "true").lower() == "true"
    )
    googlesql_enabled: bool = field(
        default_factory=lambda: os.environ.get("GOOGLESQL_ENABLED", "true").lower() == "true"
    )
    teleport_enabled: bool = field(
        default_factory=lambda: os.environ.get("TELEPORT_ENABLED", "true").lower() == "true"
    )
    memory_bridge_enabled: bool = field(
        default_factory=lambda: os.environ.get("MEMORY_BRIDGE_ENABLED", "true").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls()
