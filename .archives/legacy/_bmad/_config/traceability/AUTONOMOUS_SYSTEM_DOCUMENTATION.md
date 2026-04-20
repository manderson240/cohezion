# Autonomous BMAD Traceability System

## Overview

The Autonomous BMAD Traceability System provides continuous, self-improving repository health monitoring with zero human intervention. It combines:

- **BMAD Method compliance** - Full workflow automation
- **Multi-agent adversarial review** - 5-agent party mode
- **TDD validation** - 34 tests ensuring correctness
- **Auto-commit improvements** - Autonomous code quality enhancement
- **MCP integration** - Model Context Protocol for AI agent access
- **Daemon mode** - Continuous background operation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Autonomous Traceability MCP                 │
│                     Server (port 8362)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Scheduler   │  │   Watcher    │  │  Dashboard   │     │
│  │  (Cron)      │  │  (Git Hook)  │  │  (Web UI)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  Orchestrator   │                       │
│                  │  (Main Loop)    │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         │                 │                 │              │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐       │
│  │  Trace      │  │   Health    │  │   Party     │       │
│  │  Engine     │  │   Engine    │  │   Review    │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  BMAD Workflow  │                       │
│                  │  Executor       │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         │                 │                 │              │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐       │
│  │  Validate   │  │   Document  │  │   Commit    │       │
│  │  Module     │  │   Project   │  │  Changes    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Git Repository │
                  │  (Auto-commit)  │
                  └─────────────────┘
```

## Components

### 1. Traceability Engine
- **Location:** `_bmad/_config/traceability/traceability_engine.py`
- **Purpose:** Extract agent→workflow→task mappings
- **Output:** 4 CSV matrices + reports
- **Tests:** 18 unit tests + 8 edge case + 8 E2E

### 2. Repo Health Engine
- **Location:** `_bmad/_config/traceability/repo_health/repo_health_engine.py`
- **Purpose:** Multi-dimensional health scoring
- **Metrics:** Code quality, test health, tech debt, git health, docs
- **Score:** 0-100 scale (current: 66.6 → target: 80+)

### 3. Party-Mode Review
- **Location:** `_bmad/_config/traceability/workflows/run_party_review.py`
- **Agents:** 5 (Amelia-Dev, Quinn-QA, Winston-Arch, Murat-Test, BMad Master)
- **Findings:** Categorized by severity (HIGH/MEDIUM/LOW)
- **Auto-Fix:** HIGH priority findings auto-resolved

### 4. Recursive Loop
- **Location:** `_bmad/_config/traceability/recursive_loop.py`
- **Features:** Self-trace, snapshot versioning, gap detection
- **Auto-Trigger:** Party review when gaps detected

### 5. Daemon Mode
- **Location:** `_bmad/_config/traceability/daemon.py`
- **Modes:** Background, foreground, cron, git-hook
- **Schedule:** Configurable intervals (default: 60 min)

### 6. MCP Server
- **Location:** `src/cohezion/mcp/servers/traceability/server.py`
- **Port:** 8362
- **Tools:** 6 MCP tools for AI agent access
- **Dashboard:** Web UI for health visualization

## Installation

### Quick Start

```bash
# 1. Install daemon as systemd service
sudo systemctl enable traceability
sudo systemctl start traceability

# 2. Install git hook
uv run python -m cohezion.mcp.servers.traceability.daemon --install-hook

# 3. Verify running
curl http://localhost:8362/health

# 4. View dashboard
curl http://localhost:8362/dashboard
```

### Manual Execution

```bash
# Run daemon in foreground (debugging)
uv run python -m cohezion.mcp.servers.traceability.daemon --foreground

# Run single health check
uv run python _bmad/_config/traceability/repo_health/repo_health_engine.py

# Trigger party review
uv run python _bmad/_config/traceability/workflows/run_party_review.py

# Run full BMAD workflow
uv run python _bmad/_config/traceability/recursive_loop.py
```

## Configuration

### Health Config

**File:** `_bmad/_config/traceability/health_config.py`

```python
from health_config import HealthConfig

# Default weights
config = HealthConfig()
config.weights.code_quality = 0.30  # 30%
config.weights.test_health = 0.25   # 25%
config.weights.tech_debt = 0.20     # 20%
config.weights.git_health = 0.15    # 15%
config.weights.doc_health = 0.10    # 10%

# Thresholds
config.thresholds.coverage_target_percent = 80.0
config.thresholds.lint_errors_max = 100
config.thresholds.failing_tests_max = 10
```

### Daemon Config

**File:** `_bmad/_config/traceability/daemon_config.yaml`

```yaml
daemon:
  mode: background  # background|foreground|cron|git-hook
  interval_minutes: 60
  auto_commit: true
  auto_commit_scope: HIGH  # HIGH|ALL|NONE
  party_review_trigger: gaps  # gaps|scheduled|both
  bmads_workflow_schedule: nightly  # nightly|every_commit|never
  
git_hook:
  enabled: true
  trigger_on: commit  # commit|push|merge
  
dashboard:
  enabled: true
  port: 8362
  refresh_seconds: 300
```

## Operation Modes

### Full Autonomy (Aggressive)
- Daemon runs every 15 minutes
- Auto-commit all fixes (HIGH + MEDIUM + LOW)
- Party review every 4 hours + on gaps
- Full BMAD workflow on every significant change
- **Best for:** Rapid improvement sprints

### Conservative Autonomy
- Daemon runs every 60 minutes
- Auto-commit HIGH priority fixes only
- Party review only on gaps
- Full BMAD workflow nightly (2 AM)
- Create PRs for MEDIUM/LOW fixes
- **Best for:** Production environments

### Manual Mode
- Daemon disabled
- All operations manual trigger
- **Best for:** Debugging, development

## MCP Tools

The traceability MCP server provides 6 tools for AI agents:

1. **`traceability_run_engine`** - Execute traceability extraction
2. **`traceability_run_health`** - Run health check
3. **`traceability_trigger_party`** - Trigger party review
4. **`traceability_get_dashboard`** - Get health dashboard
5. **`traceability_get_findings`** - Get recent findings
6. **`traceability_auto_commit`** - Commit improvements

### Usage Example

```python
# From AI agent via MCP
result = await mcp_client.call_tool(
    "traceability_run_health",
    {"self_trace": True}
)
print(f"Health score: {result['score']}")
```

## Git Hook Integration

### Installation

```bash
uv run python -m cohezion.mcp.servers.traceability.daemon --install-hook
```

### Hook Behavior

**On every `git commit`:**
1. Run health check
2. If score improved → update dashboard
3. If gaps detected → trigger party review
4. If HIGH findings → auto-fix + auto-commit
5. Log to `.git/traceability.log`

### Uninstall

```bash
rm .git/hooks/post-commit
```

## Dashboard

**URL:** `http://localhost:8362/dashboard`

**Displays:**
- Overall health score (0-100)
- Category breakdown (code, test, debt, git, docs)
- Recent findings (HIGH/MEDIUM/LOW)
- Auto-commit history
- Party review status
- Next scheduled run

**Auto-refresh:** Every 5 minutes

## Logging

### Log Location

`_bmad/_config/traceability/traceability.log`

### Log Levels

- **INFO:** Normal operation
- **WARNING:** Gaps detected, party review triggered
- **ERROR:** Engine failures, test failures
- **DEBUG:** Detailed execution traces

### View Logs

```bash
# Tail logs
tail -f _bmad/_config/traceability/traceability.log

# Systemd logs
journalctl -u traceability -f

# Grep errors
grep ERROR _bmad/_config/traceability/traceability.log
```

## Troubleshooting

### Daemon Not Starting

```bash
# Check status
sudo systemctl status traceability

# Restart
sudo systemctl restart traceability

# Check logs
journalctl -u traceability --no-pager -n 50
```

### Health Check Failing

```bash
# Run manually with verbose output
uv run python _bmad/_config/traceability/repo_health/repo_health_engine.py --verbose

# Check timeout issues
uv run python _bmad/_config/traceability/repo_health/repo_health_engine.py --timeout=600
```

### Party Review Not Triggering

```bash
# Manually trigger
uv run python _bmad/_config/traceability/workflows/run_party_review.py

# Check gap detection logic
uv run python _bmad/_config/traceability/recursive_loop.py
```

### MCP Server Not Responding

```bash
# Check port
netstat -tlnp | grep 8362

# Restart server
pkill -f traceability_server
uv run python -m cohezion.mcp.servers.traceability.server &

# Test health endpoint
curl http://localhost:8362/health
```

## Performance

### Benchmarks

- **Traceability engine:** ~30 seconds (609 Python files)
- **Health check:** ~90 seconds (full test suite skipped)
- **Party review:** ~60 seconds (5 agents)
- **Full BMAD workflow:** ~300 seconds (validate + document)

### Optimization

```yaml
# daemon_config.yaml
performance:
  skip_full_test_run: true  # Use cached coverage
  parallel_agents: true     # Run agents concurrently
  cache_snapshots: true     # Cache previous results
```

## Security

### Authentication

MCP server uses ephemeral tokens:
```bash
# Generate token
uv run python -m cohezion.mcp.manager.auth

# Token location: ~/.cohezion/auth.token
# Permissions: 600 (user read/write only)
```

### Auto-Commit Safety

```yaml
# daemon_config.yaml
security:
  auto_commit_branch: session-traceability-autonomy  # Never main
  require_tests_pass: true  # Block commit if tests fail
  max_commit_per_hour: 5    # Rate limiting
  dry_run: false            # Set true for testing
```

## Metrics

### Tracked Metrics

- Health score trend (over time)
- Findings resolved count
- Auto-commit count
- Party review frequency
- Test pass rate
- BMAD compliance score

### Export

```bash
# Export metrics as CSV
curl http://localhost:8362/api/metrics > metrics.csv

# Export as JSON
curl http://localhost:8362/api/metrics.json > metrics.json
```

## Roadmap

### Phase 1 (Implemented)
- ✅ Traceability engine
- ✅ Health monitoring
- ✅ Party-mode review
- ✅ Recursive loop
- ✅ MCP server
- ✅ Daemon mode
- ✅ Git hook

### Phase 2 (Next)
- 📋 Web dashboard (real-time UI)
- 📋 Slack/Email notifications
- 📋 PR auto-creation for MEDIUM/LOW
- 📋 Multi-repo support

### Phase 3 (Future)
- 📋 ML-based gap prediction
- 📋 Auto-prioritization learning
- 📋 Cross-project benchmarking
- 📋 Distributed agent swarm

## Support

### Documentation

- `_bmad/_config/traceability/COMPOUND_ENGINEERING_SUMMARY.md` - System overview
- `_bmad/_config/traceability/ADVERSARIAL_REVIEW_FINDINGS.md` - Review findings
- `_bmad/_config/traceability/workflows/MULTI_AGENT_REVIEW_FINDINGS.md` - Agent findings

### Contact

- **Issues:** GitHub issues on cohezion repo
- **Chat:** MCP server `/help` command
- **Logs:** `_bmad/_config/traceability/traceability.log`

---

**Version:** 1.0.0  
**Last Updated:** 2026-03-22  
**Status:** Production Ready (Full Autonomy Mode)
