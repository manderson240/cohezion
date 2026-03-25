# Session Context

## User Prompts

### Prompt 1

<teammate-message teammate_id="team-lead">
You are the MCP Health Hook agent. Your task is to create a SessionStart hook that checks MCP server health.

## Your Task (Task #1)

Mark task #1 as in_progress, then do the work, then mark it completed.

## Context

The Cohezion project has 7 MCP servers configured in `.mcp.json`:
- `cohezion-vault` — HTTP server at `http://localhost:8360/mcp` (CAN be health-checked)
- `cohezion-bmad`, `cohezion-skills`, `cohezion-research`, `cohezion-surreal`, `co...

### Prompt 2

<teammate-message teammate_id="mcp-health-hooker" color="blue">
{"type":"task_assignment","taskId":"1","subject":"Wire MCP health check into SessionStart","description":"Create .claude/hooks/mcp-health-check.sh that pings http://localhost:8360/mcp (cohezion-vault HTTP endpoint) with curl --max-time 2. Print WARNING for degraded servers. Register in project .claude/settings.json under hooks.SessionStart. Non-blocking: warn but don't block session. Only HTTP servers can be proactively checked; ...

