"""MCP Server definition with all tools registered."""

import json
import logging

from mcp.server.fastmcp import FastMCP

from .agent_context import AgentContextOps
from .compound_ops import CompoundOps
from .config import ServerConfig
from .health import HealthChecker
from .memory_bridge import VaultMemoryBridge
from .obsidian_ops import ObsidianOps
from .sheets_bridge import SheetsBridge
from .surrealdb_sync import SurrealDBSync
from .teleport import CloudTeleportProtocol
from .vault_ops import VaultOps


logger = logging.getLogger(__name__)


def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""
    vault = VaultOps(config.vault_path)
    obsidian = ObsidianOps(vault)
    compound = CompoundOps(vault, obsidian)
    teleport = CloudTeleportProtocol(vault)
    memory_bridge = VaultMemoryBridge(vault)

    sheets: SheetsBridge | None = None
    if config.sheets_enabled:
        sheets = SheetsBridge(
            spreadsheet_id=config.sheets_spreadsheet_id,
            quota_project=config.sheets_quota_project,
        )

    surrealdb: SurrealDBSync | None = None
    agent_context: AgentContextOps | None = None
    if config.surrealdb_enabled:
        surrealdb = SurrealDBSync(
            vault_path=config.vault_path,
            surrealdb_url=config.surrealdb_url,
            namespace=config.surrealdb_namespace,
            database=config.surrealdb_database,
            username=config.surrealdb_username,
            password=config.surrealdb_password,
        )
        agent_context = AgentContextOps(surrealdb)

    health_checker: HealthChecker | None = None
    if config.health_check_enabled:
        health_checker = HealthChecker(
            vault_path=config.vault_path,
            surrealdb_url=config.surrealdb_url,
            sheets_bridge=sheets,
            ollama_url=config.ollama_url,
        )

    mcp = FastMCP(
        "Cloud Vault",
        stateless_http=True,
        instructions=(
            "A knowledge vault MCP server for compound engineering. "
            "Read, write, search, and link Obsidian notes. "
            "Log decisions, experiments, and patterns to build reusable context."
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

    # ── Teleport Operations ──────────────────────────────────────────

    @mcp.tool()
    def teleport_create_task(
        title: str,
        description: str,
        context: str = "",
        expected_output: str = "",
        priority: str = "medium",
    ) -> str:
        """Create a teleport task for delegation between Claude instances.

        Use this to delegate work (research, refactoring, doc generation)
        to another Claude instance (e.g. cloud Claude with web access).

        Args:
            title: Short task title
            description: What needs to be done
            context: Background information for the task
            expected_output: What the result should look like
            priority: low, medium, high, or critical
        """
        result = teleport.create_task(
            title, description, context, expected_output, priority
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    def teleport_list_tasks(status: str = "") -> str:
        """List teleport tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending, in_progress, completed, failed).
                    Empty string returns all tasks.
        """
        tasks = teleport.list_tasks(status if status else None)
        if not tasks:
            return "No teleport tasks found."
        return json.dumps(tasks, indent=2, default=str)

    @mcp.tool()
    def teleport_claim_task(task_id: str, assigned_to: str) -> str:
        """Claim a pending teleport task for processing.

        Args:
            task_id: The task ID to claim
            assigned_to: Who is claiming it (e.g. 'cloud-claude', 'local-claude')
        """
        try:
            result = teleport.claim_task(task_id, assigned_to)
            return json.dumps(result, indent=2, default=str)
        except (ValueError, FileNotFoundError) as e:
            return f"Error: {e}"

    @mcp.tool()
    def teleport_complete_task(task_id: str, result: str) -> str:
        """Complete a teleport task with a result.

        Args:
            task_id: The task ID to complete
            result: The result/output of the completed task
        """
        try:
            task = teleport.complete_task(task_id, result)
            return json.dumps(task, indent=2, default=str)
        except (ValueError, FileNotFoundError) as e:
            return f"Error: {e}"

    @mcp.tool()
    def teleport_fail_task(task_id: str, error: str) -> str:
        """Mark a teleport task as failed.

        Args:
            task_id: The task ID that failed
            error: Description of what went wrong
        """
        try:
            task = teleport.fail_task(task_id, error)
            return json.dumps(task, indent=2, default=str)
        except FileNotFoundError as e:
            return f"Error: {e}"

    @mcp.tool()
    def teleport_get_result(task_id: str) -> str:
        """Get the result of a completed teleport task.

        Args:
            task_id: The task ID to get the result for
        """
        try:
            result = teleport.get_result(task_id)
            return json.dumps(result, indent=2, default=str)
        except FileNotFoundError as e:
            return f"Error: {e}"

    # ── Memory Bridge Operations ─────────────────────────────────────

    @mcp.tool()
    def vault_push_session_state(
        branch: str,
        test_status: str,
        phase: str,
        active_tasks: list[str] | None = None,
        last_commit: str = "",
    ) -> str:
        """Push current session state to a daily session note in the vault.

        Creates a snapshot of the current Claude Code session that other
        Claude instances can read for context.

        Args:
            branch: Current git branch name
            test_status: Test suite status (e.g. '24/24 passing')
            phase: Current project phase
            active_tasks: List of active task descriptions
            last_commit: Last commit hash or message
        """
        path = memory_bridge.push_session_state(
            branch, test_status, phase, active_tasks, last_commit
        )
        return f"Session state pushed to: {path}"

    @mcp.tool()
    def vault_push_memory(memory_content: str) -> str:
        """Parse MEMORY.md content and distribute to vault sections.

        Parses the memory content by ## headings and distributes:
        - Current State → daily/ session note
        - Lessons → patterns/ (deduplicated)
        - TODO → projects/cohezion-todos.md

        Args:
            memory_content: Full content of MEMORY.md
        """
        result = memory_bridge.push_memory(memory_content)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def vault_pull_session_context() -> str:
        """Pull latest session context from the vault.

        Reads recent session notes to build cross-instance context.
        Returns the latest branch, phase, test status, and recent sessions.
        """
        context = memory_bridge.pull_session_context()
        return json.dumps(context, indent=2, default=str)

    # ── Sheets Bridge Operations ────────────────────────────────────

    if sheets:

        @mcp.tool()
        def sheets_read_range(range_spec: str) -> str:
            """Read a range from the Cohezion_Research Google Sheet.

            Args:
                range_spec: A1 notation range (e.g. 'A1:F100', 'A2:A50')
            """
            try:
                rows = sheets.read_range(range_spec)
                return json.dumps(rows, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @mcp.tool()
        def sheets_get_all_rows() -> str:
            """Read all data rows from Cohezion_Research as structured dicts.

            Returns rows with: row number, link, status, abstractions, domain,
            integration_point, vault_note.
            """
            try:
                rows = sheets.get_all_rows()
                return json.dumps(rows, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @mcp.tool()
        def sheets_update_row(
            row_num: int,
            status: str,
            abstractions: str,
            domain: str,
            integration_point: str,
        ) -> str:
            """Update columns B-E for a row in Cohezion_Research.

            Args:
                row_num: Row number (1-based, row 2 = first data row)
                status: Research status (e.g. 'Researched', 'Inaccessible')
                abstractions: Key abstractions (1-2 sentences)
                domain: Domain category (e.g. 'AI Architecture', 'Astrophysics')
                integration_point: Relevant Cohezion module
            """
            try:
                result = sheets.update_row(
                    row_num, status, abstractions, domain, integration_point
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @mcp.tool()
        def sheets_batch_update(data: list[dict]) -> str:
            """Batch update multiple ranges in Cohezion_Research.

            Args:
                data: List of {range: 'Sheet1!B2:E2', values: [['v1', ...]]}
            """
            try:
                result = sheets.batch_update(data)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @mcp.tool()
        def sheets_update_vault_note(row_num: int, vault_note: str) -> str:
            """Update column F (Vault Note) for a row.

            Args:
                row_num: Row number (1-based)
                vault_note: Vault note filename (e.g. 'agentic-ai-memory-hierarchies.md')
            """
            try:
                result = sheets.update_vault_note_column(row_num, vault_note)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error: {e}"

    # ── SurrealDB Graph Database Sync ────────────────────────────────

    if surrealdb:

        @mcp.tool()
        def surrealdb_import_papers() -> str:
            """Import all cortex notes from vault/cortex/ to SurrealDB.

            Performs bulk import of all cortex (knowledge) markdown files, extracting:
            - Frontmatter metadata (title, date, tags)
            - Wiki-links to concepts
            - Content for indexing

            Returns count of notes imported.
            """
            try:
                count = surrealdb.bulk_import_papers()
                return f"Successfully imported {count} papers to SurrealDB"
            except Exception as e:
                logger.error(f"Failed to import papers: {e}")
                return f"Error importing papers: {e}"

        @mcp.tool()
        def surrealdb_import_concepts() -> str:
            """Import all cerebellum notes from vault/cerebellum/ to SurrealDB.

            Performs bulk import of all cerebellum (operational) markdown files, extracting:
            - Frontmatter metadata (title, tags)
            - Content for indexing

            Returns count of notes imported.
            """
            try:
                count = surrealdb.bulk_import_concepts()
                return f"Successfully imported {count} concepts to SurrealDB"
            except Exception as e:
                logger.error(f"Failed to import concepts: {e}")
                return f"Error importing concepts: {e}"

        @mcp.tool()
        def surrealdb_start_watching() -> str:
            """Start real-time file watching for vault changes.

            Monitors cortex/, cerebellum/, patterns/, and decisions/ directories
            for file modifications and creations. Changes are automatically
            synced to SurrealDB in real-time.

            This enables live updates to the 12D graph visualization.
            """
            try:
                surrealdb.start_watching()
                return "File watcher started - vault changes will sync to SurrealDB"
            except Exception as e:
                logger.error(f"Failed to start file watcher: {e}")
                return f"Error starting file watcher: {e}"

        @mcp.tool()
        def surrealdb_stop_watching() -> str:
            """Stop real-time file watching."""
            try:
                surrealdb.stop_watching()
                return "File watcher stopped"
            except Exception as e:
                logger.error(f"Failed to stop file watcher: {e}")
                return f"Error stopping file watcher: {e}"

        @mcp.tool()
        def surrealdb_query(query: str) -> str:
            """Execute a custom SurrealQL query against the vault graph database.

            Args:
                query: SurrealQL query string (automatically prefixed with USE NS/DB)

            Returns:
                Query results as JSON

            Example queries:
            - "SELECT * FROM paper WHERE tags CONTAINS 'ai' LIMIT 10;"
            - "SELECT count() FROM links GROUP BY out;"
            - "SELECT * FROM paper->links->concept WHERE out.title = 'agentic-ai';"
            """
            try:
                # Prepend USE statements
                full_query = f"USE NS {surrealdb.namespace}; USE DB {surrealdb.database}; {query}"
                results = surrealdb._execute_query(full_query)
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                logger.error(f"Query failed: {e}")
                return f"Error executing query: {e}"

    # ── Ollama Integration ────────────────────────────────────────────

    if config.ollama_enabled:
        # Import Ollama client for direct integration
        try:
            from .ollama_client import OllamaClient

            ollama_client = OllamaClient(
                base_url=config.ollama_url,
                timeout=config.ollama_timeout,
            )

            @mcp.tool()
            async def ollama_query(
                prompt: str,
                model: str = "auto",
                temperature: float = 0.7,
            ) -> str:
                """Execute a query against Ollama model.

                Args:
                    prompt: The prompt/question to send to the model
                    model: Model to use (use "auto" for automatic selection)
                    temperature: Temperature for generation (0.0-1.0)

                Returns:
                    Generated text response from the model
                """
                try:
                    response = await ollama_client.query(prompt, model, temperature)
                    return response or "Empty response from Ollama"
                except Exception as e:
                    logger.error(f"Ollama query failed: {e}")
                    return f"Error: {e}"

            @mcp.tool()
            async def ollama_embed(
                texts: list[str],
                model: str = "nomic-embed-text:latest",
            ) -> str:
                """Generate embeddings for texts.

                Args:
                    texts: List of text strings to embed
                    model: Embedding model to use

                Returns:
                    List of embedding vectors as JSON
                """
                try:
                    embeddings = await ollama_client.embed(texts, model)
                    return json.dumps(embeddings)
                except Exception as e:
                    logger.error(f"Ollama embed failed: {e}")
                    return f"Error: {e}"

            @mcp.tool()
            async def ollama_status() -> str:
                """Get Ollama service status and available models.

                Returns:
                    Status information including loaded models
                """
                try:
                    status = await ollama_client.status()
                    return json.dumps(status)
                except Exception as e:
                    logger.error(f"Ollama status check failed: {e}")
                    return f"Error: {e}"

        except ImportError:
            logger.warning("Ollama client not available for direct integration")

    # ── Health Check Operations ────────────────────────────────────────

    if health_checker:

        @mcp.tool()
        async def vault_health_check() -> str:
            """Check health of all MCP dependencies.

            Tests the following services:
            - Vault filesystem (read/write access)
            - SurrealDB graph database
            - Google Sheets API
            - Ollama service
            - Disk space
            - Process memory usage

            Returns a detailed status report with latencies and connection status.
            """
            try:
                status = await health_checker.run_all_checks(timeout=5)
                return json.dumps(status.to_dict(), indent=2)
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return json.dumps(
                    {
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": None,
                    },
                    indent=2,
                )

    # ── Agent Context Operations (SurrealDB Phase 1) ────────────────────

    if agent_context:

        @mcp.tool()
        def track_session(
            agent_id: str,
            goals: list[str],
            model_used: str = "claude-haiku-4-5",
            phase: str = "research",
        ) -> str:
            """Track the start of an agent session for research lineage.

            Creates an agent_session node in SurrealDB to capture session metadata,
            goals, resource usage, and status.

            Args:
                agent_id: Unique agent identifier (e.g., 'integration-engineer')
                goals: List of goals for this session
                model_used: LLM model name (default: claude-haiku-4-5)
                phase: Session phase (research, decision, implementation, validation)

            Returns:
                JSON with session_id, status, timestamp on success;
                error message on failure
            """
            try:
                result = agent_context.track_session(agent_id, goals, model_used, phase)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error tracking session: {e}")
                return json.dumps({"success": False, "error": str(e)}, indent=2)

        @mcp.tool()
        def record_decision(
            session_id: str,
            decision_type: str,
            reasoning: str,
            papers_applied: list[str],
            confidence_score: float = 0.7,
        ) -> str:
            """Record an architectural decision with research lineage.

            Creates an agent_decision node and APPLIED_RESEARCH edges linking
            the decision to research papers that informed it.

            Args:
                session_id: Session ID from track_session
                decision_type: Type (architecture, feature, refactor, bugfix, data)
                reasoning: Natural language explanation of the decision
                papers_applied: List of paper IDs that informed this decision
                confidence_score: Confidence level (0-1)

            Returns:
                JSON with decision_id, links_created, timestamp on success;
                validation_warnings and error messages on partial failures
            """
            try:
                result = agent_context.record_decision(
                    session_id,
                    decision_type,
                    reasoning,
                    papers_applied,
                    confidence_score,
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error recording decision: {e}")
                return json.dumps({"success": False, "error": str(e)}, indent=2)

        @mcp.tool()
        def record_outcome(
            session_id: str,
            outcome_type: str,
            lessons_learned: list[str],
            metrics: dict = None,
        ) -> str:
            """Record session outcome and validate against lessons learned.

            Creates an agent_outcome node and VALIDATES_LESSON edges linking
            the outcome to lessons from the vault. Also closes the session
            and marks it as completed.

            Args:
                session_id: Session ID from track_session
                outcome_type: Type (success, partial, failed)
                lessons_learned: List of lesson note IDs from vault
                metrics: Dict of outcome metrics (session_duration_min, token_efficiency_ratio, etc)

            Returns:
                JSON with outcome_id, validated_lessons, timestamp on success;
                validation_errors for missing lessons on partial failures
            """
            try:
                result = agent_context.record_outcome(
                    session_id, outcome_type, lessons_learned, metrics
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error recording outcome: {e}")
                return json.dumps({"success": False, "error": str(e)}, indent=2)

    # ── Pocket TTS (Text-to-Speech) ─────────────────────────────────
    try:
        from .pocket_tts import PocketTTSService

        pocket_tts = PocketTTSService()

        @mcp.tool()
        def tts_speak(text: str) -> str:
            """Convert text to speech using Pocket TTS.

            Args:
                text: Text to synthesize (max 4096 characters)

            Returns:
                JSON with audio_base64 (WAV format), duration_ms, sample_rate, and status.
                On error, returns JSON with status="error" and error message.
            """
            result = pocket_tts.speak(text)
            return json.dumps(result, indent=2)

    except ImportError:
        logger.warning("Pocket TTS not available (pip install pocket-tts)")

    from .vault_graph.tools import register_read_tools, register_write_tools

    register_read_tools(mcp)
    if config.surrealdb_enabled:
        register_write_tools(mcp)

    return mcp
