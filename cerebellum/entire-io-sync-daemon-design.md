---
title: "Entire.io Sync Daemon Design - Phase 1 Implementation"
date: 2026-02-11
status: proposed
tags: [pattern, architecture, daemon, entire-io, implementation]
aspect: thinker
neural:
  activation: 0.92
  stage: mature
  synapse_in: 19
  synapse_out: 14
---

# Entire.io Sync Daemon Design

Implementation pattern for real-time entire.io checkpoint synchronization to vault and SurrealDB.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ EntireSyncDaemon                                            │
├─────────────────────────────────────────────────────────────┤
│ Async polling loop (5-min intervals)                        │
│  ├─ git log --since={last_check} --format=fuller           │
│  ├─ Filter commits with entire.io markers                  │
│  └─ Queue for processing                                   │
├─────────────────────────────────────────────────────────────┤
│ EntireOps                                                   │
│  ├─ parse_commit_metadata() → CommitData                   │
│  ├─ extract_metrics() → MetricsDict                        │
│  └─ extract_outcomes() → List[OutcomeString]               │
├─────────────────────────────────────────────────────────────┤
│ Batch Processing                                            │
│  ├─ VaultOps: Create checkpoint notes                      │
│  ├─ ObsidianOps: Add wiki-links + frontmatter             │
│  ├─ AgentContextOps: track_session() + record_decision()  │
│  └─ SurrealDBSync: Sync nodes + edges                      │
├─────────────────────────────────────────────────────────────┤
│ Fault Handling                                              │
│  ├─ WorkQueue (SQLite): Track processed SHAs              │
│  ├─ DLQ: Failed commits (unparseable, missing fields)     │
│  └─ Retry: 3 attempts with exponential backoff            │
└─────────────────────────────────────────────────────────────┘
```

## Code Structure

### 1. entire_ops.py (100-120 LOC)

```python
class EntireOps:
    """Extract and transform entire.io checkpoint metadata."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)

    def parse_commit_metadata(self,
        commit_hash: str,
        commit_author: str,
        commit_date: str,
        commit_body: str
    ) -> CommitData:
        """Extract structured data from entire.io checkpoint commit.

        Returns:
            CommitData(
                session_id: str,
                timestamp: datetime,
                agent_id: str,
                outcomes: List[str],  # bullet points
                metrics: Dict[str, float],
                team_status: str,
                next_actions: List[str]
            )
        """
        # 1. Extract timestamp from CommitDate
        # 2. Map git author to agent_id (via config or heuristic)
        # 3. Parse body for:
        #    - "Session Summary" section → outcomes (bullets)
        #    - "Metrics" section → metrics dict
        #    - "Team:" line → team status
        #    - "Next:" line → next actions
        # 4. Return CommitData or raise ParsingError

    def extract_metrics(self, commit_body: str) -> Dict[str, float]:
        """Extract numeric metrics from 'Metrics:' section.

        Example:
            Vault Metrics:
            - Papers: 87% (73/84)
            - Decisions: 88% (15/17)

        Returns:
            {
                "papers_coverage": 0.87,
                "papers_current": 73,
                "papers_total": 84,
                "decisions_coverage": 0.88,
                ...
            }
        """
        # Parse lines matching "- {Name}: {%}% ({current}/{total})"
        # Return dict with normalized keys

    def extract_outcomes(self, commit_body: str) -> List[str]:
        """Extract outcome bullets from 'Session Summary' section.

        Example:
            Session Summary (2026-02-10):
            ✅ Completed semantic linking via Claude Sonnet (78%→90% coverage)
            ✅ SurrealDB sync: 33 new links imported

        Returns:
            [
                "Completed semantic linking via Claude Sonnet (78%→90% coverage)",
                "SurrealDB sync: 33 new links imported",
                ...
            ]
        """
        # Extract bullets between "Session Summary" and next section
        # Strip emoji and whitespace
        # Return list of outcome strings
```

### 2. entire_sync_daemon.py (200-250 LOC)

```python
class EntireSyncDaemon:
    """Async daemon for polling and syncing entire.io checkpoints.

    Reuses sheets_research_daemon.py pattern:
    - AsyncIO polling loop
    - SQLite WorkQueue
    - DeadLetterQueue
    - Graceful shutdown
    """

    def __init__(self,
        vault_path: str,
        surrealdb_sync,
        agent_context_ops,
        vault_ops,
        obsidian_ops,
        poll_interval_seconds: int = 300
    ):
        self.vault_path = vault_path
        self.db = surrealdb_sync
        self.agent_context = agent_context_ops
        self.vault = vault_ops
        self.obsidian = obsidian_ops
        self.poll_interval = poll_interval_seconds

        self.entire_ops = EntireOps(vault_path)
        self.work_queue = WorkQueue(":memory:")  # or SQLite path
        self.dlq = DeadLetterQueue(vault_path / ".entire" / "dlq.db")

    async def start(self) -> None:
        """Start the daemon polling loop."""
        while True:
            try:
                await self.poll_and_sync()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(30)  # Backoff

    async def poll_and_sync(self) -> None:
        """Poll git log for new commits and sync to vault/SurrealDB."""
        # 1. Get last_sync_time from WorkQueue or config
        # 2. Run: git log --since={last_sync} --format=fuller --all
        # 3. Filter commits containing "entire.io" or checkpoint markers
        # 4. For each commit:
        #    a. Check if SHA in WorkQueue (skip if processed)
        #    b. Try to parse metadata
        #    c. If success: add to batch for processing
        #    d. If fail: add to DLQ
        # 5. Batch process all successfully parsed commits
        # 6. Update last_sync_time in config

    async def sync_commit(self, commit_data: CommitData) -> None:
        """Sync single commit to vault and SurrealDB.

        Steps:
        1. Create daily checkpoint note in vault
        2. Add frontmatter with metrics + metadata
        3. Link to related decisions/patterns if possible
        4. Call agent_context.track_session() for SurrealDB
        5. Extract decisions from outcomes + link papers
        6. Record outcome with metrics
        """
        try:
            # 1. Create vault note
            checkpoint_path = f"daily/checkpoints/{commit_data.timestamp.date()}-{commit_data.session_id}.md"
            note_content = self._build_checkpoint_note(commit_data)
            self.vault.write(checkpoint_path, note_content)

            # 2. Track session in SurrealDB
            session_result = self.agent_context.track_session(
                agent_id=commit_data.agent_id,
                goals=commit_data.next_actions,
                phase="checkpoint"
            )

            if not session_result["success"]:
                raise Exception(f"Failed to track session: {session_result}")

            session_id = session_result["session_id"]

            # 3. Record outcomes as decisions (from bullets)
            # For each outcome, extract papers if mentioned
            # Call record_decision() with papers_applied

            # 4. Record final outcome with metrics
            self.agent_context.record_outcome(
                session_id=session_id,
                outcome_type="success",
                lessons_learned=[],  # Phase 2
                metrics=commit_data.metrics
            )

            # 5. Mark commit as processed
            self.work_queue.mark_completed(commit_data.commit_hash)

        except Exception as e:
            logger.error(f"Error syncing commit {commit_data.commit_hash}: {e}")
            self.dlq.add(
                commit_hash=commit_data.commit_hash,
                reason=str(e)
            )

    def _build_checkpoint_note(self, commit_data: CommitData) -> str:
        """Build markdown note for checkpoint."""
        return f"""---
title: "Checkpoint - {commit_data.timestamp.date()}"
date: {commit_data.timestamp.date().isoformat()}
status: complete
agent_id: {commit_data.agent_id}
session_id: {commit_data.session_id}
tags: [checkpoint, entire-io, {commit_data.agent_id}]
---

# {commit_data.timestamp.date()} Checkpoint

## Outcomes Achieved

{self._format_outcomes(commit_data.outcomes)}

## Metrics

{self._format_metrics(commit_data.metrics)}

## Status

{commit_data.team_status}

## Next Actions

{self._format_next_actions(commit_data.next_actions)}

---

*Synced from entire.io checkpoint: {commit_data.commit_hash}*
"""

class WorkQueue:
    """Track processed commits (SHAs) to prevent re-processing."""
    # Same interface as sheets_research_daemon

class DeadLetterQueue:
    """Track failed commits for manual review/retry."""
    # Same interface as sheets_research_daemon
```

### 3. entire_main.py (100-150 LOC)

```python
"""CLI entry point for entire.io sync daemon."""

@click.group()
def cli():
    """Entire.io synchronization daemon."""
    pass

@cli.command()
@click.option("--poll-interval", default=300, help="Polling interval (seconds)")
def start(poll_interval: int) -> None:
    """Start the sync daemon."""
    daemon = EntireSyncDaemon(
        vault_path=VAULT_PATH,
        poll_interval_seconds=poll_interval
    )
    asyncio.run(daemon.start())

@cli.command()
def status() -> None:
    """Show daemon status and queue state."""
    # Display WorkQueue pending count
    # Display DLQ failed count
    # Display last sync time

@cli.command()
def dlq() -> None:
    """List dead letter queue entries."""
    # Show failed commits with reasons

@cli.command()
@click.argument("commit_hash")
def retry(commit_hash: str) -> None:
    """Retry a failed commit."""
    # Remove from DLQ and re-process
```

## Data Flow Example

```
Input: git log shows new commit 'abc123def'
  ↓
[poll_and_sync] git log --since=2026-02-11T15:00
  ↓
[parse_commit_metadata] Extract:
  - timestamp: 2026-02-11T16:30:00
  - agent_id: data-graph-specialist
  - outcomes: ["Completed schema design", "Created indexes"]
  - metrics: {papers_coverage: 0.87, decisions_coverage: 0.88}
  ↓
[batch_process]
  ├─ [VaultOps] Create daily/checkpoints/2026-02-11-*.md
  ├─ [ObsidianOps] Add frontmatter + wiki-links
  ├─ [AgentContextOps.track_session] Create agent_session node
  ├─ [AgentContextOps.record_decision] Link to papers (if found)
  └─ [AgentContextOps.record_outcome] Record metrics
  ↓
Output: Checkpoint synced to vault + SurrealDB, WorkQueue marked complete
```

## Error Scenarios

| Scenario | Handling |
|----------|----------|
| Unparseable commit body | Add to DLQ, log error, continue |
| Missing agent_id mapping | Use git author as fallback, warn in log |
| SurrealDB unavailable | Retry with backoff, add to DLQ after 3 attempts |
| Duplicate processing (WorkQueue bug) | Idempotent operations (upsert) |
| Large commit history | Index by date, use `--since` to limit scope |

## Testing Strategy

### Unit Tests (entire_ops.py)
```python
def test_parse_commit_metadata():
    """Test parsing of example checkpoint commit."""
    # Use real commit message as test fixture

def test_extract_metrics():
    """Test metric extraction with variations."""
    # Test: "87% (73/84)" format
    # Test: "88% (15/17)" format
    # Test: missing metrics

def test_extract_outcomes():
    """Test outcome bullet extraction."""
    # Test: "✅ Completed semantic linking..."
    # Test: "- Without emoji"
    # Test: multiline bullets
```

### Integration Tests (entire_sync_daemon.py)
```python
def test_full_sync_workflow():
    """Test complete daemon cycle with mock commits."""
    # Create mock commit with entire.io metadata
    # Run poll_and_sync()
    # Verify vault note created
    # Verify SurrealDB nodes created
    # Verify WorkQueue updated
```

## Deployment

### Systemd Service Unit
```ini
[Unit]
Description=Entire.io Sync Daemon
After=network.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
ExecStart=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 \
  -m mcp_server.entire_main start
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Related

**Patterns**: [[event-driven-daemon-pattern]], [[surrealdb-sync-pattern]], [[error-handling-with-dlq]]

**Decisions**: [[2026-02-11-use-event-driven-daemon-for-entire-io]]

**Experiments**: [[2026-02-11-entire-io-api-investigation]]

**Projects**: [[2026-02-12-week-1-handoff-summary]]

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[3d-graph-plugin-selection]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-13-track-b-entire-sync-daemon-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-execution-status]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
