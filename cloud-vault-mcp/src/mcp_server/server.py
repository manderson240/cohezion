"""MCP Server definition with all tools registered."""

import json
import logging

from mcp.server.fastmcp import FastMCP

from .compound_ops import CompoundOps
from .config import ServerConfig
from .googlesql_client import GoogleSqlConfig
from .googlesql_ops import GoogleSqlOps
from .obsidian_ops import ObsidianOps
from .vault_ops import VaultOps

logger = logging.getLogger(__name__)


def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""
    vault = VaultOps(config.vault_path)
    obsidian = ObsidianOps(vault)
    compound = CompoundOps(vault, obsidian)
    googlesql = GoogleSqlOps(GoogleSqlConfig(base_url=config.googlesql_url))

    mcp = FastMCP(
        "Cloud Vault",
        instructions=(
            "A knowledge vault MCP server for compound engineering. "
            "Read, write, search, and link Obsidian notes. "
            "Log decisions, experiments, and patterns to build reusable context. "
            "Analyze, validate, and format SQL using the GoogleSQL analyzer."
        ),
    )

    # ── Core Vault Operations ──────────────────────────────────────────

    @mcp.tool()
    def vault_read(path: str) -> str:
        """Read a note's content from the vault.

        Args:
            path: Vault-relative path (e.g. 'decisions/2025-01-15-use-fastmcp.md')
        """
        try:
            return vault.read(path)
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_write(path: str, content: str) -> str:
        """Create or overwrite a note in the vault.

        Args:
            path: Vault-relative path for the note
            content: Full markdown content to write
        """
        try:
            return vault.write(path, content)
        except ValueError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_edit(path: str, edits: list[dict]) -> str:
        """Apply surgical edits to an existing note.

        Each edit is an object with:
        - operation: 'find_replace' | 'append' | 'prepend' | 'insert_at_heading'
        - find/replace: for find_replace operations
        - text: for append, prepend, insert_at_heading
        - heading: for insert_at_heading

        Args:
            path: Vault-relative path to the note
            edits: List of edit operations to apply
        """
        try:
            return vault.edit(path, edits)
        except (FileNotFoundError, ValueError) as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_delete(path: str) -> str:
        """Delete a note from the vault.

        Args:
            path: Vault-relative path to delete
        """
        try:
            return vault.delete(path)
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_list(directory: str = "", recursive: bool = False) -> str:
        """List vault contents.

        Args:
            directory: Directory to list (empty for vault root)
            recursive: If true, list all files recursively
        """
        try:
            items = vault.list_dir(directory, recursive)
            return "\n".join(items) if items else "(empty)"
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_search(query: str, scope: str = "all", folder: str = "") -> str:
        """Full-text search across the vault.

        Args:
            query: Search text (case-insensitive)
            scope: 'all', 'folder', or 'tags'
            folder: Required when scope is 'folder'
        """
        results = vault.search(query, scope, folder)
        if not results:
            return "No results found."
        return json.dumps(results[:20], indent=2)

    # ── Obsidian-Aware Operations ──────────────────────────────────────

    @mcp.tool()
    def vault_backlinks(path: str) -> str:
        """Find all notes that link TO the given note.

        Args:
            path: Vault-relative path of the target note
        """
        results = obsidian.backlinks(path)
        if not results:
            return "No backlinks found."
        return json.dumps(results, indent=2)

    @mcp.tool()
    def vault_forward_links(path: str) -> str:
        """Find all notes that the given note links TO.

        Args:
            path: Vault-relative path of the source note
        """
        try:
            results = obsidian.forward_links(path)
            if not results:
                return "No outgoing links found."
            return json.dumps(results, indent=2)
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_tags(path: str = "") -> str:
        """List tags in the vault, or for a specific note.

        Args:
            path: Optional path to a specific note. If empty, lists all vault tags.
        """
        try:
            result = obsidian.tags(path if path else None)
            if not result:
                return "No tags found."
            return "\n".join(f"#{t}" for t in result)
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def vault_create_from_template(
        template_name: str, target_path: str, variables: dict[str, str]
    ) -> str:
        """Create a new note from a template with variable substitution.

        Available templates: decisions, experiments, patterns, papers, daily, projects

        Args:
            template_name: Name of template directory (e.g. 'decisions', 'experiments')
            target_path: Where to create the new note
            variables: Template variable substitutions
        """
        try:
            return obsidian.create_from_template(template_name, target_path, variables)
        except FileNotFoundError as e:
            return f"Error: {e}"

    # ── Compound Engineering Operations ────────────────────────────────

    @mcp.tool()
    def vault_log_decision(
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
        """
        return compound.log_decision(
            project, title, context, decision, rationale, alternatives_considered
        )

    @mcp.tool()
    def vault_log_experiment(
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
        """
        return compound.log_experiment(
            project, hypothesis, method, result, learnings, title
        )

    @mcp.tool()
    def vault_extract_pattern(
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
        """
        return compound.extract_pattern(
            source_path, pattern_name, description, code_example, domain
        )

    @mcp.tool()
    def vault_find_relevant_context(query: str, project: str = "") -> str:
        """Search for prior decisions, patterns, and experiments.

        This is the primary 'compound engineering' tool. It searches
        across decisions, patterns, experiments, concepts, and projects
        to find prior context relevant to current work.

        Args:
            query: What you're looking for
            project: Optional project name to scope the search
        """
        results = compound.find_relevant_context(query, project if project else None)
        if not results:
            return "No relevant prior context found."
        return json.dumps(results, indent=2)

    # ── GoogleSQL Analysis Operations ─────────────────────────────────

    @mcp.tool()
    def sql_validate(sql: str) -> str:
        """Validate SQL syntax using the GoogleSQL analyzer.

        Use this to check whether a SQL statement is syntactically correct
        before executing it. Catches syntax errors early.

        Args:
            sql: SQL statement to validate
        """
        try:
            return googlesql.validate(sql)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_parse(sql: str) -> str:
        """Parse SQL into an Abstract Syntax Tree (AST).

        Use this to understand the structure of a SQL statement, including
        what type of statement it is and its component parts.

        Args:
            sql: SQL statement to parse
        """
        try:
            return googlesql.parse(sql)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_analyze(sql: str, catalog_json: str = "") -> str:
        """Perform full semantic analysis of SQL with optional catalog context.

        Resolves table and column references against a provided schema.
        Use this for deep analysis of query semantics, including type checking
        and reference resolution.

        Args:
            sql: SQL statement to analyze
            catalog_json: Optional JSON array of table definitions.
                Example: [{"name": "t", "columns": [{"name": "id", "type": "INT64"}]}]
        """
        try:
            return googlesql.analyze(sql, catalog_json)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_extract_tables(sql: str) -> str:
        """Extract all table references from a SQL statement.

        Use this to discover which tables a query depends on, useful for
        dependency analysis and impact assessment.

        Args:
            sql: SQL statement to extract table references from
        """
        try:
            return googlesql.extract_tables(sql)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_extract_columns(sql: str) -> str:
        """Extract all column references from a SQL statement.

        Use this to discover which columns a query uses, useful for
        understanding data access patterns.

        Args:
            sql: SQL statement to extract column references from
        """
        try:
            return googlesql.extract_columns(sql)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_format(sql: str) -> str:
        """Format a SQL statement for readability.

        Applies consistent formatting to SQL using GoogleSQL's formatter.

        Args:
            sql: SQL statement to format
        """
        try:
            return googlesql.format_sql(sql)
        except ConnectionError:
            return "Error: GoogleSQL Analyzer service is not available."

    @mcp.tool()
    def sql_health() -> str:
        """Check if the GoogleSQL Analyzer service is available."""
        if googlesql.is_available():
            return json.dumps({"status": "ok", "service": "googlesql-analyzer"})
        return json.dumps({"status": "unavailable", "service": "googlesql-analyzer"})

    return mcp
