"""Google Sheets research pipeline daemon."""

import asyncio
import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Result from a single row research."""

    row: int
    status: str
    abstractions: str
    domain: str
    integration_point: str


@dataclass
class BatchResult:
    """Result of batch research processing."""

    successful: list[ResearchResult]
    failed: list[tuple[int, str]]  # (row_number, reason)


class DeadLetterQueue:
    """SQLite-backed dead letter queue for failed rows."""

    def __init__(self, db_path: str):
        """Initialize DLQ with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    row_number INTEGER PRIMARY KEY,
                    link TEXT NOT NULL,
                    failure_reason TEXT,
                    failure_count INTEGER DEFAULT 1,
                    last_attempt TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dlq_created ON dead_letter_queue(created_at)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add(self, row_number: int, link: str, reason: str):
        """Add failed row to DLQ."""
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                INSERT INTO dead_letter_queue
                (row_number, link, failure_reason, failure_count, last_attempt)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(row_number) DO UPDATE SET
                    failure_count = failure_count + 1,
                    failure_reason = excluded.failure_reason,
                    last_attempt = excluded.last_attempt
                """,
                (row_number, link, reason, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all(self) -> list[dict]:
        """Get all dead letter queue entries."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT row_number, link, failure_reason, failure_count, last_attempt
                FROM dead_letter_queue
                ORDER BY last_attempt DESC
                """
            )
            entries = [
                {
                    "row": row[0],
                    "link": row[1],
                    "reason": row[2],
                    "failure_count": row[3],
                    "last_attempt": row[4],
                }
                for row in cursor.fetchall()
            ]
            return entries
        finally:
            conn.close()

    def remove(self, row_number: int):
        """Remove entry from DLQ (retry)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                DELETE FROM dead_letter_queue
                WHERE row_number = ?
                """,
                (row_number,),
            )
            conn.commit()
        finally:
            conn.close()

    def get_size(self) -> int:
        """Get number of entries in DLQ."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM dead_letter_queue")
            return cursor.fetchone()[0]
        finally:
            conn.close()


class WorkQueue:
    """SQLite-backed work queue for tracking sheet rows."""

    def __init__(self, db_path: str):
        """Initialize work queue with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS work_queue (
                    row_number INTEGER PRIMARY KEY,
                    link TEXT NOT NULL,
                    state TEXT DEFAULT 'PENDING',
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_state ON work_queue(state)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_rows(self, rows: list[dict]):
        """Add unresearched rows to work queue."""
        conn = sqlite3.connect(self.db_path)
        try:
            for row in rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO work_queue (row_number, link, state)
                    VALUES (?, ?, 'PENDING')
                    """,
                    (row["row"], row["link"]),
                )
            conn.commit()
        finally:
            conn.close()

    def get_pending_rows(self, limit: int) -> list[dict]:
        """Get pending rows from queue."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT row_number, link FROM work_queue
                WHERE state = 'PENDING'
                LIMIT ?
                """,
                (limit,),
            )
            rows = [{"row": row[0], "link": row[1]} for row in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def mark_in_progress(self, row_numbers: list[int]):
        """Mark rows as in progress."""
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(UTC).isoformat()
            for row_num in row_numbers:
                conn.execute(
                    """
                    UPDATE work_queue
                    SET state = 'IN_PROGRESS', last_attempt = ?
                    WHERE row_number = ?
                    """,
                    (now, row_num),
                )
            conn.commit()
        finally:
            conn.close()

    def mark_completed(self, row_number: int):
        """Mark row as completed."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE work_queue
                SET state = 'COMPLETED'
                WHERE row_number = ?
                """,
                (row_number,),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_failed(self, row_number: int) -> tuple[bool, int]:
        """Increment retry count and update failure timestamp.

        Returns:
            (should_retry, retry_count) - True if row should be retried, False if DLQ
        """
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(UTC).isoformat()
            cursor = conn.execute(
                """
                UPDATE work_queue
                SET state = 'PENDING', retry_count = retry_count + 1, last_attempt = ?
                WHERE row_number = ?
                RETURNING retry_count
                """,
                (now, row_number),
            )
            new_retry_count = cursor.fetchone()[0]
            conn.commit()
            return (new_retry_count < 3, new_retry_count)
        finally:
            conn.close()

    def get_stats(self) -> dict[str, int]:
        """Get work queue statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT state, COUNT(*) FROM work_queue GROUP BY state
                """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return stats
        finally:
            conn.close()


class AgentCoordinator:
    """Spawns and coordinates research agents."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        max_turns: int = 8,
        timeout_seconds: int = 300,
        anthropic_client=None,
    ):
        """Initialize agent coordinator.

        Args:
            model: Model to use for agents
            max_turns: Max turns per agent (for safety cap)
            timeout_seconds: Agent timeout
            anthropic_client: Optional pre-configured Anthropic client
        """
        self.model = model
        self.max_turns = max_turns
        self.timeout_seconds = timeout_seconds
        self.client = anthropic_client

    async def spawn_agent(self, rows: list[dict]) -> str:
        """Spawn a single research agent for a batch of rows via Anthropic API.

        Returns:
            JSON research results
        """
        # Create task prompt
        prompt = self._create_task_prompt(rows)

        try:
            # Use provided client or create one
            if not self.client:
                import json as json_lib
                from pathlib import Path as PathLib

                import anthropic

                # Try OAuth token first (Claude Code)
                auth_token = None
                creds_path = PathLib.home() / ".claude" / ".credentials.json"
                try:
                    creds_data = json_lib.loads(creds_path.read_text())
                    auth_token = creds_data.get("claudeAiOauth", {}).get("accessToken")
                except (FileNotFoundError, json_lib.JSONDecodeError, KeyError):
                    pass

                # Fall back to API key
                if auth_token:
                    self.client = anthropic.Anthropic(auth_token=auth_token)
                else:
                    self.client = anthropic.Anthropic()

            logger.info(f"Spawning agent for {len(rows)} rows via Anthropic API")

            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response text
            response_text = message.content[0].text if message.content else ""
            logger.debug(f"Agent response: {response_text[:200]}...")
            return response_text

        except TimeoutError:
            logger.error(f"Agent timed out after {self.timeout_seconds}s")
            return ""
        except Exception as e:
            logger.error(f"Agent spawn failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return ""

    def extract_json_from_output(self, output: str) -> list[dict]:
        """Extract JSON research results from agent output.

        Pattern:
        - Look for ```json blocks in response text
        - Parse and validate schema
        - Return list of research results
        """
        if not output:
            return []

        try:
            # Extract JSON from ```json blocks
            pattern = r"```json\s*([\s\S]*?)\s*```"
            matches = re.findall(pattern, output)

            if not matches:
                logger.warning(f"No JSON blocks found in agent output: {output[:200]}")
                return []

            # Take the largest JSON block (most complete result)
            largest_match = max(matches, key=len)
            results = json.loads(largest_match)

            if not isinstance(results, list):
                logger.warning("JSON root is not array, wrapping")
                results = [results]

            # Validate schema
            validated = []
            for item in results:
                if all(
                    key in item
                    for key in [
                        "row",
                        "status",
                        "abstractions",
                        "domain",
                        "integration_point",
                    ]
                ):
                    validated.append(item)
                else:
                    logger.warning(f"Invalid result schema: {item}")

            return validated

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return []
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            return []

    def _create_task_prompt(self, rows: list[dict]) -> str:
        """Create task prompt for agent."""
        rows_text = "\n".join([f"- Row {r['row']}: {r['link']}" for r in rows])

        return f"""Research the following links and return ONLY valid JSON array:

ROWS TO RESEARCH:
{rows_text}

OUTPUT FORMAT (REQUIRED):
```json
[
  {{
    "row": <row_number>,
    "status": "Researched" | "Inaccessible",
    "abstractions": "1-2 sentence summary (max 200 chars)",
    "domain": "Domain category (AI, Physics, Biology, etc.)",
    "integration_point": "How this relates to Cohezion agentic AI framework"
  }},
  ...
]
```

INSTRUCTIONS:
- Return ONLY the JSON array (no prose, no explanation)
- Use "Researched" if link is accessible and you can summarize it
- Use "Inaccessible" if link is broken, paywalled, or otherwise unavailable
- Keep abstractions concise (under 200 chars)
- Focus on key concepts relevant to research
- Domain: AI, Physics, Biology, Materials Science, Astronomy, Mathematics, Other
- integration_point: How this research applies to Cohezion's agentic AI goals
"""


class SheetsResearchDaemon:
    """Main daemon orchestrating the research pipeline."""

    def __init__(
        self,
        config,
        sheets_bridge,
        vault_ops,
        anthropic_client=None,
    ):
        """Initialize daemon.

        Args:
            config: ServerConfig instance
            sheets_bridge: SheetsBridge instance
            vault_ops: VaultOps instance
            anthropic_client: Anthropic client (optional, for future features)
        """
        self.config = config
        self.sheets = sheets_bridge
        self.vault = vault_ops
        self.anthropic = anthropic_client

        # Separate databases for work queue and DLQ
        queue_db = config.sheets_research_work_queue_db
        dlq_db = queue_db.replace(".db", "_dlq.db")

        self.work_queue = WorkQueue(queue_db)
        self.dlq = DeadLetterQueue(dlq_db)
        self.coordinator = AgentCoordinator(
            model=config.inbox_model,
            max_turns=8,
            timeout_seconds=config.sheets_research_agent_timeout,
        )

        self.shutdown_event = None
        self.last_poll_time = None
        self.rows_processed_today = 0

    async def run(self):
        """Main daemon loop."""
        logger.info(
            "Sheets research daemon starting (poll_interval=%ds, batch_size=%d, max_agents=%d)",
            self.config.sheets_research_poll_interval,
            self.config.sheets_research_batch_size,
            self.config.sheets_research_max_concurrent_agents,
        )

        self.shutdown_event = asyncio.Event()

        # Set up signal handlers
        loop = asyncio.get_running_loop()

        def handle_shutdown():
            logger.info("Shutdown signal received")
            self.shutdown_event.set()

        import signal

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_shutdown)

        try:
            while not self.shutdown_event.is_set():
                try:
                    await asyncio.wait_for(
                        self._poll_and_process(),
                        timeout=self.config.sheets_research_poll_interval,
                    )
                except TimeoutError:
                    pass
                except Exception:
                    logger.exception("Unexpected error in poll cycle")
        finally:
            logger.info("Sheets research daemon stopped")

    async def _poll_and_process(self):
        """Poll sheet and process unresearched rows."""
        try:
            # Fetch all rows from sheet
            all_rows = self.sheets.get_all_rows()
            logger.info(f"Fetched {len(all_rows)} total rows from sheet")

            # Filter unresearched rows (empty status column)
            unresearched = [r for r in all_rows if r["link"] and not r["status"]]

            if not unresearched:
                logger.debug("No unresearched rows found")
                return

            logger.info(f"Found {len(unresearched)} unresearched rows")

            # Add to work queue
            self.work_queue.add_rows(unresearched)

            # Process pending rows in batches
            while True:
                pending = self.work_queue.get_pending_rows(
                    self.config.sheets_research_batch_size
                    * self.config.sheets_research_max_concurrent_agents
                )

                if not pending:
                    break

                logger.info(f"Processing {len(pending)} pending rows")
                await self._process_batch(pending)

        except Exception:
            logger.exception("Error in poll and process")

    async def _process_batch(self, rows: list[dict]):
        """Process batch of rows using parallel agents."""
        # Split into sub-batches for parallel agent spawn
        batch_size = self.config.sheets_research_batch_size
        sub_batches = [
            rows[i : i + batch_size] for i in range(0, len(rows), batch_size)
        ]

        logger.info(f"Spawning {len(sub_batches)} agents")

        # Mark rows as in progress
        row_nums = [r["row"] for r in rows]
        self.work_queue.mark_in_progress(row_nums)

        # Spawn agents in parallel
        tasks = [self.coordinator.spawn_agent(batch) for batch in sub_batches]

        results = await asyncio.gather(*tasks)

        # Collect and validate results
        all_results = []
        for agent_output in results:
            extracted = self.coordinator.extract_json_from_output(agent_output)
            all_results.extend(extracted)

        logger.info(f"Collected {len(all_results)} research results")

        # Apply updates to sheet and vault
        await self._apply_results(all_results, rows)

    async def _apply_results(
        self,
        results: list[dict],
        submitted_rows: list[dict],
    ):
        """Apply research results to sheet and vault."""
        if not results:
            logger.warning("No results to apply")
            # Mark all as failed and implement retry logic
            for row in submitted_rows:
                should_retry, retry_count = self.work_queue.mark_failed(row["row"])
                if not should_retry:
                    # Move to DLQ after 3 attempts
                    self.dlq.add(
                        row["row"],
                        row["link"],
                        f"No result from agent after {retry_count} attempts",
                    )
                    logger.warning(
                        f"Row {row['row']} moved to DLQ after {retry_count} attempts"
                    )
            return

        # Prepare batch update data
        batch_data = []
        results_by_row = {r["row"]: r for r in results}

        successful = []
        failed = []

        for row in submitted_rows:
            row_num = row["row"]
            result = results_by_row.get(row_num)

            if result:
                batch_data.append(
                    {
                        "range": f"Sheet1!B{row_num}:E{row_num}",
                        "values": [
                            [
                                result["status"],
                                result["abstractions"],
                                result["domain"],
                                result["integration_point"],
                            ]
                        ],
                    }
                )
                successful.append(result)
                self.work_queue.mark_completed(row_num)
            else:
                # Retry logic: 3 attempts before DLQ
                should_retry, retry_count = self.work_queue.mark_failed(row_num)
                if not should_retry:
                    self.dlq.add(
                        row_num,
                        row["link"],
                        f"No result from agent after {retry_count} attempts",
                    )
                    logger.warning(
                        f"Row {row_num} moved to DLQ after {retry_count} attempts"
                    )
                failed.append((row_num, "No result from agent"))

        # Apply batch update to sheet
        if batch_data:
            try:
                logger.info(f"Updating {len(batch_data)} rows in sheet")
                self.sheets.batch_update(batch_data)
            except Exception:
                logger.exception("Batch update failed")
                return

        # Generate vault notes for successful results
        for result in successful:
            try:
                await self._generate_vault_note(result)
            except Exception:
                logger.exception(
                    f"Failed to generate vault note for row {result['row']}"
                )

        self.rows_processed_today += len(successful)
        logger.info(
            f"Processed {len(successful)} rows successfully, {len(failed)} failed"
        )

        if failed:
            logger.warning(f"Failed rows: {failed}")

        # Log DLQ status
        dlq_size = self.dlq.get_size()
        if dlq_size > 0:
            logger.warning(f"DLQ has {dlq_size} rows")

    async def _generate_vault_note(self, result: dict):
        """Generate vault note for researched row."""
        # Create filename from abstractions (first 50 chars)
        title_slug = (
            result["abstractions"][:50].lower().replace(" ", "-").replace("/", "-")
        )
        filename = f"papers/{result['row']}-{title_slug}.md"
        filepath = Path(self.vault.vault_path) / filename

        # Check if note already exists
        if filepath.exists():
            logger.info(f"Vault note already exists: {filename}")
            return

        # Create YAML frontmatter
        now = datetime.now(UTC).strftime("%Y-%m-%d")
        frontmatter = {
            "title": result["abstractions"][:100],
            "date": now,
            "status": "researched",
            "tags": ["sheets-research", result["domain"].lower()],
            "domain": result["domain"],
            "integration_point": result["integration_point"],
            "source": f"Sheets Research Pipeline - Row {result['row']}",
        }

        # Format frontmatter as YAML
        yaml_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}: {json.dumps(value)}")
            else:
                yaml_lines.append(f'{key}: "{value}"')
        yaml_lines.append("---")
        yaml_frontmatter = "\n".join(yaml_lines)

        # Create note content
        content = f"""{yaml_frontmatter}

# {result["abstractions"][:100]}

## Summary

{result["abstractions"]}

## Domain

{result["domain"]}

## Integration Point

{result["integration_point"]}

## Notes

- Researched via automated Sheets Research Pipeline
- Row {result["row"]}
"""

        # Write to vault
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            logger.info(f"Generated vault note: {filename}")

            # Update column F in sheet
            try:
                self.sheets.update_vault_note_column(
                    result["row"],
                    filename,
                )
                logger.info(f"Updated column F for row {result['row']}: {filename}")
            except Exception:
                logger.exception(f"Failed to update column F for row {result['row']}")

        except Exception:
            logger.exception(f"Failed to write vault note: {filename}")

    def get_status(self) -> dict[str, Any]:
        """Get daemon status."""
        stats = self.work_queue.get_stats()
        dlq_size = self.dlq.get_size()
        return {
            "status": "running"
            if self.shutdown_event and not self.shutdown_event.is_set()
            else "stopped",
            "work_queue": stats,
            "dlq_size": dlq_size,
            "rows_processed_today": self.rows_processed_today,
            "config": {
                "poll_interval": self.config.sheets_research_poll_interval,
                "batch_size": self.config.sheets_research_batch_size,
                "max_agents": self.config.sheets_research_max_concurrent_agents,
            },
        }

    def get_dlq_entries(self) -> list[dict]:
        """Get all dead letter queue entries."""
        return self.dlq.get_all()

    def retry_dlq_row(self, row_number: int) -> bool:
        """Retry a specific DLQ row.

        Returns:
            True if row was retried, False if not found
        """
        entries = self.dlq.get_all()
        if any(e["row"] == row_number for e in entries):
            self.dlq.remove(row_number)
            self.work_queue.add_rows([{"row": row_number, "link": ""}])
            logger.info(f"Retrying row {row_number} from DLQ")
            return True
        return False

    def mark_dlq_inaccessible(self, row_number: int) -> bool:
        """Mark a DLQ row as permanently inaccessible.

        Returns:
            True if row was marked, False if not found
        """
        entries = self.dlq.get_all()
        if any(e["row"] == row_number for e in entries):
            self.dlq.remove(row_number)
            logger.info(f"Marked row {row_number} as permanently inaccessible")
            return True
        return False
