# Proactive BMad - Integrated with BMad MCP Server

## Overview

Proactive BMad anticipates needs and suggests actions automatically, integrated as tools in the existing BMad MCP Server (port 8361).

## MCP Tools Added

### 1. `bmad_proactive_scan`
**Endpoint:** `POST /proactive/scan`

Scans codebase for BMad alignment suggestions.

**Response:**
```json
{
  "suggestions": [
    {
      "id": "repo-workflow-missing",
      "title": "Repository Operations Missing BMad Workflows",
      "priority": "high",
      "auto_executable": true,
      "confidence": 0.9
    }
  ],
  "summary": {
    "total_patterns": 5,
    "active_suggestions": 3,
    "by_priority": {"high": 2, "medium": 1}
  }
}
```

### 2. `bmad_proactive_execute`
**Endpoint:** `POST /proactive/execute`

Execute a proactive suggestion.

**Request:**
```json
{
  "suggestion_id": "repo-workflow-missing",
  "confirm": true
}
```

### 3. `bmad_proactive_summary`
**Endpoint:** `GET /proactive/summary`

Get summary of proactive monitoring state.

### 4. `bmad_proactive_list_patterns`
**Endpoint:** `GET /proactive/patterns`

List all proactive detection patterns.

### 5. `bmad_proactive_enable_pattern`
**Endpoint:** `POST /proactive/pattern/{pattern_id}/enable`

Enable/disable a specific pattern.

## Detection Patterns

### Repository Layer Patterns

1. **repository-workflow-gap**
   - Detects: New repository without BMad workflow
   - Suggests: Create BMad workflows for repository operations
   - Auto-executable: ✅

2. **metrics-observability-gap**
   - Detects: RepositoryMetrics not integrated with BMad observability
   - Suggests: Create observability integration
   - Auto-executable: ✅

3. **batch-tasks-missing**
   - Detects: Batch operations not in task-manifest.csv
   - Suggests: Add batch tasks to manifest
   - Auto-executable: ✅

### Quality Patterns

4. **adversarial-quality-gap**
   - Detects: Adversarial review without BMad quality gate
   - Suggests: Create quality gate definition
   - Auto-executable: ✅

5. **low-test-coverage**
   - Detects: Test coverage below 80%
   - Suggests: Run coverage analysis
   - Auto-executable: ❌ (requires user action)

## Usage Examples

### CLI Usage

```bash
# Run proactive scan
uv run python -m cohezion.mcp.servers.bmad.proactive_monitor .

# Scan and auto-execute with confirmation
uv run python -m cohezion.mcp.servers.bmad.proactive_monitor . --auto-execute
```

### MCP Tool Usage (via Claude Code)

```
# Scan for suggestions
mcp__cohezion_bmad__proactive_scan()

# Execute a suggestion
mcp__cohezion_bmad__proactive_execute(suggestion_id="repo-workflow-missing", confirm=true)

# Get summary
mcp__cohezion_bmad__proactive_summary()
```

### HTTP API Usage

```bash
# Scan
curl -X POST http://localhost:8361/proactive/scan \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H "Content-Type: application/json"

# Execute
curl -X POST http://localhost:8361/proactive/execute \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_id": "repo-workflow-missing", "confirm": true}'
```

## Integration with Party Mode

Proactive BMad integrates with BMad Party Mode:

1. **Automatic Scanning**: Party mode can trigger proactive scan on startup
2. **Agent Discussion**: Suggestions become discussion topics for agents
3. **Collaborative Execution**: Agents can help execute suggestions

Example party mode flow:
```
1. User starts party mode
2. Proactive scan runs automatically
3. Winston (Architect) discusses repository-workflow-gap
4. Wendy (Workflow Builder) suggests workflow structure
5. Amelia (Developer) offers to implement
6. User confirms execution
7. BMad Master executes suggestion
```

## Files

- `src/cohezion/mcp/servers/bmad/routes_proactive.py` - MCP route handlers
- `src/cohezion/mcp/servers/bmad/proactive_monitor.py` - Detection engine
- `_bmad/core/proactive/README.md` - This documentation

## Architecture

```
┌─────────────────────────────────────────────┐
│  BMad MCP Server (Port 8361)                │
│  ┌─────────────────────────────────────┐   │
│  │ Proactive Routes                     │   │
│  │ - /proactive/scan                    │   │
│  │ - /proactive/execute                 │   │
│  │ - /proactive/summary                 │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ ProactiveMonitor                     │   │
│  │ - Pattern detection                  │   │
│  │ - Suggestion generation              │   │
│  │ - Auto-execution                     │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
           │
           │ Scans
           ▼
┌─────────────────────────────────────────────┐
│  Codebase                                   │
│  - Repository layer                         │
│  - Workflow definitions                     │
│  - Task manifests                           │
│  - Test coverage                            │
└─────────────────────────────────────────────┘
```

## Next Steps

1. **Add More Patterns**: Detect more alignment gaps
2. **Party Mode Integration**: Auto-scan on party mode start
3. **Learning**: Track which suggestions users accept/reject
4. **Priority Adjustment**: Auto-adjust pattern confidence based on feedback

## Benefits

- **Proactive**: Suggests actions before user asks
- **Integrated**: Uses existing BMad MCP infrastructure
- **Safe**: Requires confirmation before auto-execution
- **Extensible**: Easy to add new detection patterns
- **Observable**: Metrics and logging for all detections
