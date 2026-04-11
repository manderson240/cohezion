"""MCP Server Manager - default server registrations."""

from __future__ import annotations

import logging
import os

from .server_manager import get_manager


logger = logging.getLogger(__name__)


def init_default_servers() -> None:
    """Register default MCP servers."""
    manager = get_manager()

    # Register Vault MCP Server (Port 8360) - Cloud Vault for compound engineering
    manager.register_server(
        name="vault",
        entry_point="cohezion.mcp.servers.vault:run_server",
        preferred_port=8360,
        auto_restart=True,
        env_vars={
            "VAULT_PATH": os.environ.get("VAULT_PATH", "/vault"),
            "MCP_API_KEY": os.environ.get("MCP_API_KEY", ""),
            "LOG_LEVEL": "INFO",
            "WATCHER_ENABLED": "true",
            "HEALTH_CHECK_ENABLED": "true",
        },
    )

    # Register BMAD server (Port 8361)
    manager.register_server(
        name="bmad",
        entry_point="cohezion.mcp.servers.bmad.server:app",
        preferred_port=8361,
        auto_restart=True,
        env_vars={
            "BMAD_DATA_PATH": "_bmad",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Skills.sh server (Port 8362)
    manager.register_server(
        name="skills",
        entry_point="cohezion.mcp.servers.skills.server:app",
        preferred_port=8362,
        auto_restart=True,
        env_vars={
            "SKILLS_CACHE_SIZE": "1000",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Doc Retriever server (Port 8364)
    manager.register_server(
        name="doc-retriever",
        entry_point="cohezion.mcp.servers.doc.server:app",
        preferred_port=8364,
        auto_restart=True,
        env_vars={
            "SURREAL_URL": "ws://localhost:8001/rpc",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Hugging Face MCP Server (Port 8365) - Official HF managed service
    manager.register_server(
        name="huggingface",
        entry_point="cohezion.mcp.servers.huggingface.server:app",
        preferred_port=8365,
        auto_restart=True,
        env_vars={
            "HF_MCP_URL": "https://huggingface.co/mcp",
            "HF_TOKEN": os.getenv("HF_TOKEN", ""),
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Memory MCP Server (Port 8366) - Knowledge graph
    manager.register_server(
        name="memory",
        entry_point="cohezion.mcp.servers.memory.server:app",
        preferred_port=8366,
        auto_restart=True,
        env_vars={
            "SURREAL_URL": "ws://localhost:8001/rpc",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Sequential Thinking MCP Server (Port 8367)
    manager.register_server(
        name="sequential-thinking",
        entry_point="cohezion.mcp.servers.sequential.server:app",
        preferred_port=8367,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Git Context MCP Server (Port 8368)
    manager.register_server(
        name="git-context",
        entry_point="cohezion.mcp.servers.git.server:app",
        preferred_port=8368,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Security MCP Server (Port 8369)
    manager.register_server(
        name="security",
        entry_point="cohezion.mcp.servers.security.server:app",
        preferred_port=8369,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Knowledge MCP Server (Port 8371)
    manager.register_server(
        name="knowledge",
        entry_point="cohezion.mcp.knowledge_server:app",
        preferred_port=8371,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Swarm MCP Server (Port 8372)
    manager.register_server(
        name="swarm",
        entry_point="cohezion.mcp.swarm_server:app",
        preferred_port=8372,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Research MCP Server (Port 8373)
    manager.register_server(
        name="research",
        entry_point="cohezion.mcp.research_server:app",
        preferred_port=8373,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    logger.info("Registered %d default MCP servers", len(manager.servers))
