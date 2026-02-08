"""MCP client for Cloud Vault operations.

Connects to the Cloud Vault MCP Server using streamable-http protocol
to enable compound engineering workflows with persistent knowledge storage.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


def _parse_sse_response(text: str) -> dict:
    """Parse Server-Sent Events response to extract JSON-RPC data.

    Args:
        text: Raw SSE response text

    Returns:
        Parsed JSON data from SSE event

    Raises:
        ValueError: If response cannot be parsed
    """
    # SSE format: "event: message\ndata: {...json...}\n\n"
    lines = text.strip().split("\n")
    for line in lines:
        if line.startswith("data: "):
            json_str = line[6:]  # Remove "data: " prefix
            return json.loads(json_str)
    raise ValueError("No data found in SSE response")


@dataclass
class MCPConfig:
    """Configuration for MCP client connection."""

    server_url: str
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class MCPConnectionError(MCPClientError):
    """Connection to MCP server failed."""


class MCPAuthenticationError(MCPClientError):
    """Authentication with MCP server failed."""


class MCPToolError(MCPClientError):
    """MCP tool execution failed."""


class MCPClient:
    """Client for Cloud Vault MCP Server operations.

    Provides methods to interact with the Cloud Vault MCP Server for:
    - Vault operations (read, write, edit, delete, search)
    - Obsidian operations (backlinks, forward links, tags, templates)
    - Compound operations (decisions, experiments, patterns, context)

    Uses streamable-http protocol with Bearer token authentication.
    """

    def __init__(self, config: MCPConfig):
        """Initialize MCP client.

        Args:
            config: MCP client configuration with server URL and API key
        """
        self.config = config
        self._client: httpx.Client | None = None
        self._session_id: str | None = None

    def __enter__(self) -> "MCPClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """Establish connection to MCP server and initialize session."""
        if self._client is not None and self._session_id is not None:
            return

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        self._client = httpx.Client(
            base_url=self.config.server_url,
            headers=headers,
            timeout=self.config.timeout,
        )

        # Initialize MCP session
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "cohezion-mcp-client", "version": "1.0"},
                },
            }
            response = self._client.post("/mcp", json=payload)
            response.raise_for_status()

            # Extract session ID from response headers
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                raise MCPConnectionError("No session ID in server response")

            self._session_id = session_id
            logger.info(f"MCP session initialized: {session_id}")

            # Parse SSE response
            if response.text:
                try:
                    result = _parse_sse_response(response.text)
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        raise MCPConnectionError(
                            f"Session initialization failed: {error_msg}"
                        )
                except ValueError as e:
                    logger.warning(f"Could not parse SSE response: {e}")
                    # Session ID in header is sufficient for success
                    pass

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise MCPAuthenticationError(
                    "Invalid API key for MCP server"
                ) from e
            raise MCPConnectionError(f"Connection check failed: {e}") from e
        except httpx.RequestError as e:
            raise MCPConnectionError(
                f"Failed to connect to MCP server at {self.config.server_url}: {e}"
            ) from e

    def close(self) -> None:
        """Close connection to MCP server."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._session_id = None

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool with retry logic.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPConnectionError: If connection fails after retries
            MCPToolError: If tool execution fails
        """
        if self._client is None or self._session_id is None:
            raise MCPConnectionError("Client not connected. Call connect() first.")

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        # Add session ID to headers
        headers = {"mcp-session-id": self._session_id}

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._client.post("/mcp", json=payload, headers=headers)
                response.raise_for_status()

                # Parse SSE response
                result = _parse_sse_response(response.text)

                # Check for JSON-RPC error
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    raise MCPToolError(
                        f"Tool '{tool_name}' failed: {error_msg}"
                    )

                return result.get("result", {}).get("content", [{}])[0].get("text", "")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    raise MCPAuthenticationError(
                        "Authentication failed during tool call"
                    ) from e
                last_error = e
                logger.warning(
                    "Tool call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )

            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    "Connection error (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )

        raise MCPConnectionError(
            f"Failed to call tool '{tool_name}' after "
            f"{self.config.max_retries} attempts: {last_error}"
        ) from last_error

    # ── Vault Operations ────────────────────────────────────────────────

    def vault_read(self, path: str) -> str:
        """Read a note's content from the vault.

        Args:
            path: Vault-relative path (e.g. 'decisions/2025-01-15-use-fastmcp.md')

        Returns:
            Note content as markdown

        Raises:
            MCPToolError: If note not found or read fails
        """
        return self._call_tool("vault_read", {"path": path})

    def vault_write(self, path: str, content: str) -> str:
        """Create or overwrite a note in the vault.

        Args:
            path: Vault-relative path for the note
            content: Full markdown content to write

        Returns:
            Confirmation message

        Raises:
            MCPToolError: If write fails
        """
        return self._call_tool("vault_write", {"path": path, "content": content})

    def vault_edit(self, path: str, edits: list[dict]) -> str:
        """Apply surgical edits to an existing note.

        Each edit is a dict with:
        - operation: 'find_replace' | 'append' | 'prepend' | 'insert_at_heading'
        - For find_replace: find, replace
        - For append/prepend: text
        - For insert_at_heading: heading, text

        Args:
            path: Vault-relative path to the note
            edits: List of edit operations to apply

        Returns:
            Summary of applied edits

        Raises:
            MCPToolError: If edit fails
        """
        return self._call_tool("vault_edit", {"path": path, "edits": edits})

    def vault_delete(self, path: str) -> str:
        """Delete a note from the vault.

        Args:
            path: Vault-relative path to delete

        Returns:
            Confirmation message

        Raises:
            MCPToolError: If delete fails
        """
        return self._call_tool("vault_delete", {"path": path})

    def vault_list(self, directory: str = "", recursive: bool = False) -> list[str]:
        """List vault contents.

        Args:
            directory: Directory to list (empty for vault root)
            recursive: If true, list all files recursively

        Returns:
            List of file/directory paths

        Raises:
            MCPToolError: If listing fails
        """
        result = self._call_tool(
            "vault_list", {"directory": directory, "recursive": recursive}
        )
        if result == "(empty)":
            return []
        return result.strip().split("\n")

    def vault_search(
        self, query: str, scope: str = "all", folder: str = ""
    ) -> list[dict]:
        """Full-text search across the vault.

        Args:
            query: Search text (case-insensitive)
            scope: 'all', 'folder', or 'tags'
            folder: Required when scope is 'folder'

        Returns:
            List of search results with path, line_number, line, context

        Raises:
            MCPToolError: If search fails
        """
        import json

        result = self._call_tool(
            "vault_search", {"query": query, "scope": scope, "folder": folder}
        )
        if result == "No results found.":
            return []
        return json.loads(result)

    # ── Obsidian Operations ─────────────────────────────────────────────

    def vault_backlinks(self, path: str) -> list[dict]:
        """Find all notes that link TO the given note.

        Args:
            path: Vault-relative path of the target note

        Returns:
            List of backlinks with source and link_text

        Raises:
            MCPToolError: If operation fails
        """
        import json

        result = self._call_tool("vault_backlinks", {"path": path})
        if result == "No backlinks found.":
            return []
        return json.loads(result)

    def vault_forward_links(self, path: str) -> list[dict]:
        """Find all notes that the given note links TO.

        Args:
            path: Vault-relative path of the source note

        Returns:
            List of forward links with link, resolved_path, exists

        Raises:
            MCPToolError: If operation fails
        """
        import json

        result = self._call_tool("vault_forward_links", {"path": path})
        if result == "No outgoing links found.":
            return []
        return json.loads(result)

    def vault_tags(self, path: str = "") -> list[str]:
        """List tags in the vault, or for a specific note.

        Args:
            path: Optional path to a specific note. If empty, lists all vault tags.

        Returns:
            List of tags (with # prefix)

        Raises:
            MCPToolError: If operation fails
        """
        result = self._call_tool("vault_tags", {"path": path})
        if result == "No tags found.":
            return []
        return result.strip().split("\n")

    def vault_create_from_template(
        self, template_name: str, target_path: str, variables: dict[str, str]
    ) -> str:
        """Create a new note from a template with variable substitution.

        Available templates: decisions, experiments, patterns, papers, daily, projects

        Args:
            template_name: Name of template directory (e.g. 'decisions', 'experiments')
            target_path: Where to create the new note
            variables: Template variable substitutions

        Returns:
            Confirmation message

        Raises:
            MCPToolError: If template not found or creation fails
        """
        return self._call_tool(
            "vault_create_from_template",
            {
                "template_name": template_name,
                "target_path": target_path,
                "variables": variables,
            },
        )

    # ── Compound Operations ─────────────────────────────────────────────

    def vault_log_decision(
        self,
        project: str,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        alternatives_considered: str = "",
    ) -> str:
        """Create an Architecture Decision Record (ADR).

        Use this after making a significant technical decision to capture the context,
        rationale, and alternatives for future reference.

        Args:
            project: Project name (e.g. 'rl-environment', 'cohezion')
            title: Short decision title (e.g. 'Use FastMCP for server framework')
            context: What situation led to this decision
            decision: What was decided
            rationale: Why this option was chosen
            alternatives_considered: Other options that were evaluated

        Returns:
            Path to created decision record

        Raises:
            MCPToolError: If creation fails
        """
        return self._call_tool(
            "vault_log_decision",
            {
                "project": project,
                "title": title,
                "context": context,
                "decision": decision,
                "rationale": rationale,
                "alternatives_considered": alternatives_considered,
            },
        )

    def vault_log_experiment(
        self,
        project: str,
        hypothesis: str,
        method: str,
        result: str = "",
        learnings: str = "",
        title: str = "",
    ) -> str:
        """Log an experiment with hypothesis, method, and results.

        Use this when trying something new — a library, approach, configuration,
        or technique — to capture what was tried and what was learned.

        Args:
            project: Project name
            hypothesis: What you expected to happen
            method: What you did / how you tested
            result: What actually happened (can be filled in later)
            learnings: Key takeaways (can be filled in later)
            title: Optional title (defaults to truncated hypothesis)

        Returns:
            Path to created experiment log

        Raises:
            MCPToolError: If creation fails
        """
        return self._call_tool(
            "vault_log_experiment",
            {
                "project": project,
                "hypothesis": hypothesis,
                "method": method,
                "result": result,
                "learnings": learnings,
                "title": title,
            },
        )

    def vault_extract_pattern(
        self,
        source_path: str,
        pattern_name: str,
        description: str,
        code_example: str = "",
        domain: str = "general",
    ) -> str:
        """Extract a reusable pattern from project work.

        Use this when you notice a solution that could be reused across projects.

        Args:
            source_path: Path to the source note/project this pattern comes from
            pattern_name: Name of the pattern (e.g. 'Reward Shaping with Curriculum')
            description: Description of the solution
            code_example: Optional code example
            domain: Domain tag (e.g. 'rl', 'ml', 'devops', 'general')

        Returns:
            Path to created pattern document

        Raises:
            MCPToolError: If creation fails
        """
        return self._call_tool(
            "vault_extract_pattern",
            {
                "source_path": source_path,
                "pattern_name": pattern_name,
                "description": description,
                "code_example": code_example,
                "domain": domain,
            },
        )

    def vault_find_relevant_context(
        self, query: str, project: str = ""
    ) -> list[dict]:
        """Search for prior decisions, patterns, and experiments.

        This is the primary 'compound engineering' tool. It searches
        across decisions, patterns, experiments, concepts, and projects
        to find prior context relevant to current work.

        Args:
            query: What you're looking for
            project: Optional project name to scope the search

        Returns:
            List of relevant context with path, category, match_count

        Raises:
            MCPToolError: If search fails
        """
        import json

        result = self._call_tool(
            "vault_find_relevant_context", {"query": query, "project": project}
        )
        if result == "No relevant prior context found.":
            return []
        return json.loads(result)


def create_mcp_client(server_url: str, api_key: str, **kwargs) -> MCPClient:
    """Factory function to create an MCP client.

    Args:
        server_url: MCP server URL (e.g. 'http://localhost:8360')
        api_key: API key for authentication
        **kwargs: Additional config options (timeout, max_retries)

    Returns:
        Configured MCPClient instance
    """
    config = MCPConfig(server_url=server_url, api_key=api_key, **kwargs)
    return MCPClient(config)
