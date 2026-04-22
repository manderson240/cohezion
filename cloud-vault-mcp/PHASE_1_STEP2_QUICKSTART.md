# Phase 1 Step 2: MCP Tools Implementation — Quick Start

**Owner**: integration-engineer
**Duration**: 4 hours
**Status**: Ready to start

---

## What You're Building

3 MCP tools that wrap the AgentContextOps service layer:
- `track_session()` - Create agent execution session
- `record_decision()` - Record critical decision
- `record_outcome()` - Record session result

---

## File Locations

**Service Layer** (Already ready):
```
src/mcp_server/agent_context_ops.py  (267 LOC, fully implemented)
```

**Server Integration** (Your work):
```
src/mcp_server/server.py  (add 3 @mcp.tool() decorators)
```

**Tests** (Templates provided):
```
tests/test_agent_context_ops.py  (40+ test cases, ready to run)
```

**Documentation** (Reference):
```
PHASE_1_AGENT_CONTEXT_INTEGRATION.md  (Full roadmap + specs)
```

---

## Implementation Checklist

### 1. Import AgentContextOps (5 min)

In `server.py` at the top with other imports:

```python
from .agent_context_ops import AgentContextOps
```

### 2. Initialize Service in create_server() (5 min)

After line ~46 where other services are initialized:

```python
def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""
    vault = VaultOps(config.vault_path)
    obsidian = ObsidianOps(vault)
    compound = CompoundOps(vault, obsidian)
    teleport = CloudTeleportProtocol(vault)
    memory_bridge = VaultMemoryBridge(vault)

    # ADD THIS:
    agent_context = AgentContextOps(
        surrealdb_url=config.surrealdb_url,
        namespace=config.surrealdb_namespace,
        database=config.surrealdb_database,
        username=config.surrealdb_username,
        password=config.surrealdb_password,
    )

    # ... rest of function
```

### 3. Register track_session() Tool (10 min)

After the other vault tool definitions (around line 150):

```python
@mcp.tool()
def track_session(
    agent_names: list[str],
    duration_ms: int,
    status: str,
    model_used: str = "haiku",
    total_turns: int = 0,
    total_functions: int = 0,
    error_message: str | None = None,
) -> str:
    """Track agent execution session to SurrealDB.

    Args:
        agent_names: List of agent names participating in session
        duration_ms: Session duration in milliseconds
        status: Session status (running | completed | error)
        model_used: Primary model used (haiku | sonnet | opus), default: haiku
        total_turns: Total conversation turns, default: 0
        total_functions: Total function calls, default: 0
        error_message: Error message if status=error

    Returns:
        Session ID (e.g., "session:abc12345")
    """
    try:
        return agent_context.track_session(
            agent_names=agent_names,
            duration_ms=duration_ms,
            status=status,
            model_used=model_used,
            total_turns=total_turns,
            total_functions=total_functions,
            error_message=error_message,
        )
    except Exception as e:
        return f"Error: {e}"
```

### 4. Register record_decision() Tool (15 min)

Right after track_session():

```python
@mcp.tool()
def record_decision(
    session_id: str,
    title: str,
    context: str,
    reasoning: str,
    alternatives: list[str],
    chosen_path: str,
    confidence: float = 0.8,
    reversible: bool = True,
) -> str:
    """Record critical decision during agent work.

    Args:
        session_id: Parent session ID (from track_session)
        title: Decision title
        context: Why was this decision needed?
        reasoning: How was the decision made?
        alternatives: List of alternative paths considered
        chosen_path: Which path was chosen?
        confidence: Confidence level (0.0 - 1.0), default: 0.8
        reversible: Can this decision be undone?, default: True

    Returns:
        Decision ID (e.g., "decision:def67890")
    """
    try:
        return agent_context.record_decision(
            session_id=session_id,
            title=title,
            context=context,
            reasoning=reasoning,
            alternatives=alternatives,
            chosen_path=chosen_path,
            confidence=confidence,
            reversible=reversible,
        )
    except Exception as e:
        return f"Error: {e}"
```

### 5. Register record_outcome() Tool (15 min)

Right after record_decision():

```python
@mcp.tool()
def record_outcome(
    session_id: str,
    status: str,
    summary: str,
    metrics: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    vault_notes_created: list[str] | None = None,
) -> str:
    """Record final outcome of agent session.

    Args:
        session_id: Parent session ID (from track_session)
        status: Outcome status (success | partial | failed)
        summary: Human-readable result summary
        metrics: Execution metrics dict with keys like 'total_turns', 'total_functions', 'errors'
        artifacts: List of files/results created during session
        vault_notes_created: List of vault notes created (e.g., ['decisions/2026-02-11-example.md'])

    Returns:
        Outcome ID (e.g., "outcome:ghi12345")
    """
    try:
        return agent_context.record_outcome(
            session_id=session_id,
            status=status,
            summary=summary,
            metrics=metrics,
            artifacts=artifacts,
            vault_notes_created=vault_notes_created,
        )
    except Exception as e:
        return f"Error: {e}"
```

---

## Testing

### 1. Unit Tests (Optional but Recommended)

Run the provided test suite:

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 -m pytest tests/test_agent_context_ops.py -v
```

Expected: All tests pass (some require SurrealDB running)

### 2. Integration Test (Required)

Test the tools via MCP:

```bash
# Start the server
python3 run_mcp.py

# In another terminal, test via curl:
curl -X POST http://localhost:8360/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "track_session",
    "arguments": {
      "agent_names": ["test-agent"],
      "duration_ms": 1000,
      "status": "completed"
    }
  }'
```

Expected: Returns session ID like `session:abc12345`

### 3. End-to-End Flow

Test full flow: session → decision → outcome

```python
# 1. Create session
session_id = track_session(
    agent_names=["researcher"],
    duration_ms=5000,
    status="completed"
)

# 2. Record decision made in that session
decision_id = record_decision(
    session_id=session_id,
    title="Use SurrealDB for agent context",
    context="Need to track agent execution decisions",
    reasoning="Native graph edges enable research lineage queries",
    alternatives=["PostgreSQL", "MongoDB"],
    chosen_path="SurrealDB"
)

# 3. Record outcome
outcome_id = record_outcome(
    session_id=session_id,
    status="success",
    summary="Agent successfully designed schema and created MCP tools",
    metrics={
        "total_turns": 12,
        "total_functions": 45,
        "errors": 0
    }
)
```

Expected: All return IDs, no errors

---

## Gotchas & Tips

### Error: "AgentContextOps import fails"
- Make sure you're importing from `.agent_context_ops` (relative import)
- Check that the file exists at: `src/mcp_server/agent_context_ops.py`

### Error: "SurrealDB connection refused"
- Check that SurrealDB is running: `curl http://localhost:8000/sql`
- Verify config credentials in env variables

### Error: "dict[str, Any] type hint not recognized"
- Add import at top of server.py: `from typing import Any`

### Tip: Copy-paste is okay
- The code above is production-ready, just copy into server.py
- No need to modify the implementation

### Tip: Run tests first
- Run unit tests before touching server.py
- Tests use mocks, don't need SurrealDB

---

## Success Criteria

Step 2 complete when:

- [ ] AgentContextOps imported in server.py
- [ ] 3 MCP tools registered (track_session, record_decision, record_outcome)
- [ ] Unit tests passing (or at least not failing)
- [ ] Integration test works (curl returns session ID)
- [ ] No Python syntax errors (server starts)
- [ ] Each tool has correct docstring

**Time estimate**: 50 min actual work + 30 min testing = 80 min total (well within 4h)

---

## Next Steps

Once Step 2 is done:

1. **data-graph-specialist** starts Step 3 (query testing)
2. **Both** coordinate Step 4 (integration testing)
3. **Final** Step 6 sign-off

---

## Reference

- Full roadmap: `PHASE_1_AGENT_CONTEXT_INTEGRATION.md`
- Service impl: `src/mcp_server/agent_context_ops.py`
- Tests: `tests/test_agent_context_ops.py`
- Server: `src/mcp_server/server.py`

**Questions?** Check PHASE_1_AGENT_CONTEXT_INTEGRATION.md or ask in chat.

Good luck! 🚀
