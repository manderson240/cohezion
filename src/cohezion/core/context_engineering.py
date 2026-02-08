"""Context Engineering Infrastructure for compound operations.

Provides a unified interface for context engineering tools with optional
Cloud Vault MCP Server integration for persistent knowledge storage.
"""

import logging
from collections.abc import Callable
from typing import Any

from cohezion.core.mcp_client import MCPClient, create_mcp_client


logger = logging.getLogger(__name__)


class ContextEngineeringInfrastructure:
    """Infrastructure for context engineering with optional MCP integration.

    Supports two modes:
    1. Local-only: Register and execute tools locally (backward compatible)
    2. MCP-enabled: Integrate with Cloud Vault for persistent knowledge

    When MCP is configured, the following compound operations are available:
    - log_decision: Create Architecture Decision Records
    - log_experiment: Track experiments with hypothesis/method/results
    - extract_pattern: Extract reusable patterns from project work
    - find_relevant_context: Search prior decisions/patterns/experiments
    """

    def __init__(
        self,
        mcp_server_url: str | None = None,
        mcp_api_key: str | None = None,
        mcp_enabled: bool = True,
    ):
        """Initialize context engineering infrastructure.

        Args:
            mcp_server_url: Optional Cloud Vault MCP Server URL
            mcp_api_key: Optional API key for MCP authentication
            mcp_enabled: Enable MCP integration if credentials provided (default: True)
        """
        self._tools: dict[str, Callable] = {}
        self._mcp_client: MCPClient | None = None
        self._mcp_enabled = mcp_enabled

        # Initialize MCP client if credentials provided
        if mcp_enabled and mcp_server_url and mcp_api_key:
            try:
                self._mcp_client = create_mcp_client(mcp_server_url, mcp_api_key)
                self._mcp_client.connect()
                self._register_mcp_tools()
                logger.info("MCP integration enabled with Cloud Vault")
            except Exception as e:
                logger.warning("Failed to initialize MCP client: %s", e)
                self._mcp_client = None

    def _register_mcp_tools(self) -> None:
        """Register compound operations from MCP client as tools."""
        if self._mcp_client is None:
            return

        # Capture in local var for closure type narrowing
        client = self._mcp_client

        # Register log_decision tool
        def log_decision(
            project: str,
            title: str,
            context: str,
            decision: str,
            rationale: str,
            alternatives_considered: str = "",
        ) -> str:
            """Create an Architecture Decision Record.

            Args:
                project: Project name
                title: Short decision title
                context: What situation led to this decision
                decision: What was decided
                rationale: Why this option was chosen
                alternatives_considered: Other options evaluated

            Returns:
                Path to created decision record
            """
            return client.vault_log_decision(  # type: ignore[no-any-return]
                project=project,
                title=title,
                context=context,
                decision=decision,
                rationale=rationale,
                alternatives_considered=alternatives_considered,
            )

        # Register log_experiment tool
        def log_experiment(
            project: str,
            hypothesis: str,
            method: str,
            result: str = "",
            learnings: str = "",
            title: str = "",
        ) -> str:
            """Log an experiment with hypothesis, method, and results.

            Args:
                project: Project name
                hypothesis: What you expected to happen
                method: What you did / how you tested
                result: What actually happened
                learnings: Key takeaways
                title: Optional title

            Returns:
                Path to created experiment log
            """
            return client.vault_log_experiment(  # type: ignore[no-any-return]
                project=project,
                hypothesis=hypothesis,
                method=method,
                result=result,
                learnings=learnings,
                title=title,
            )

        # Register extract_pattern tool
        def extract_pattern(
            source_path: str,
            pattern_name: str,
            description: str,
            code_example: str = "",
            domain: str = "general",
        ) -> str:
            """Extract a reusable pattern from project work.

            Args:
                source_path: Path to source note/project
                pattern_name: Name of the pattern
                description: Description of the solution
                code_example: Optional code example
                domain: Domain tag (e.g. 'rl', 'ml', 'general')

            Returns:
                Path to created pattern document
            """
            return client.vault_extract_pattern(  # type: ignore[no-any-return]
                source_path=source_path,
                pattern_name=pattern_name,
                description=description,
                code_example=code_example,
                domain=domain,
            )

        # Register find_relevant_context tool
        def find_relevant_context(query: str, project: str = "") -> list[dict]:
            """Search for prior decisions, patterns, and experiments.

            This is the primary compound engineering tool for experience-guided
            execution. It searches across decisions, patterns, experiments,
            concepts, and projects to find relevant prior context.

            Args:
                query: What you're looking for
                project: Optional project name to scope the search

            Returns:
                List of relevant context with path, category, match_count
            """
            return client.vault_find_relevant_context(  # type: ignore[no-any-return]
                query=query, project=project
            )

        # Register all compound operations
        self._tools["log_decision"] = log_decision
        self._tools["log_experiment"] = log_experiment
        self._tools["extract_pattern"] = extract_pattern
        self._tools["find_relevant_context"] = find_relevant_context

    def register_tool(self, name: str, tool: Callable) -> None:
        """Register a custom tool.

        Args:
            name: Tool name
            tool: Callable that implements the tool
        """
        self._tools[name] = tool

    def execute_tool(self, name: str, **kwargs: Any) -> Any:
        """Execute a registered tool.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name](**kwargs)

    def list_tools(self) -> list[str]:
        """List all registered tools.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def is_mcp_enabled(self) -> bool:
        """Check if MCP integration is active.

        Returns:
            True if MCP client is connected
        """
        return self._mcp_client is not None

    def close(self) -> None:
        """Clean up resources, close MCP connection if open."""
        if self._mcp_client is not None:
            self._mcp_client.close()
            self._mcp_client = None
