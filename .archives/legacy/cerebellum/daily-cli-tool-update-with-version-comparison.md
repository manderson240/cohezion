---
title: "Daily CLI Tool Update with Version Comparison"
date: "2026-02-22"
tags: [pattern, tooling, automation, maintenance]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 7
  synapse_out: 7
---

# Daily CLI Tool Update with Version Comparison

## Problem

CLI tools used by AI agent sessions (e.g., `cz`, `claude`, `uv`, `gh`, `mcp-cli`) drift out of date silently. Stale versions cause cryptic errors during agent sessions: deprecated flags, changed output formats, missing features. Debugging these version-related issues wastes tokens and time because the symptoms mimic code bugs rather than tool version problems.

Manual update discipline is unreliable — developers and agents do not routinely check for CLI tool updates before each session.

## Solution

Implement an automated version-compare-and-update script that runs daily (via [[2026-02-22-daily-cli-tool-update-via-systemd-timer]]) and can also be invoked manually:

### Version Comparison Pattern

```bash
#!/bin/bash
# check-and-update-tool.sh — Compare current vs latest, update if stale

TOOL_NAME="$1"
CURRENT_VERSION=""
LATEST_VERSION=""

# Step 1: Get current version
case "$TOOL_NAME" in
    "uv")
        CURRENT_VERSION=$(uv --version 2>/dev/null | awk '{print $2}')
        ;;
    "claude")
        CURRENT_VERSION=$(claude --version 2>/dev/null | head -1)
        ;;
    "gh")
        CURRENT_VERSION=$(gh --version 2>/dev/null | awk '{print $3}')
        ;;
esac

# Step 2: Get latest version (tool-specific)
case "$TOOL_NAME" in
    "uv")
        LATEST_VERSION=$(curl -sL https://pypi.org/pypi/uv/json | jq -r '.info.version')
        ;;
    "gh")
        LATEST_VERSION=$(gh release list -R cli/cli --limit 1 --json tagName -q '.[0].tagName' | sed 's/^v//')
        ;;
esac

# Step 3: Compare and update if needed
if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "[$(date)] $TOOL_NAME: $CURRENT_VERSION → $LATEST_VERSION (updating)"
    # Tool-specific update command here
else
    echo "[$(date)] $TOOL_NAME: $CURRENT_VERSION (up to date)"
fi
```

### Key Design Principles

1. **Compare before updating** — avoid unnecessary reinstalls that waste time and network bandwidth
2. **Idempotent execution** — safe to run multiple times; if already current, exits immediately
3. **Structured logging** — version transitions are logged for audit trail
4. **Failure tolerance** — if version check fails (network down), skip gracefully and retry next day

## When to Use

- **Systemd timer** — daily automated runs to keep tools current without human intervention
- **Session start hook** — optional pre-session check for critical tools only (adds ~3s latency)
- **Manual invocation** — via `/update-tools` skill when an agent encounters version-related errors
- **CI pipelines** — pin tool versions in CI, but validate they are available

**Do not use for:**
- Tools that require careful version management (e.g., Python interpreters, database servers) — these should be pinned and updated deliberately
- Production dependencies — library versions should be managed by lock files, not auto-updated

## Related Patterns

- [[log-rotation-and-monitoring]] — complementary systemd timer pattern for scheduled maintenance
- [[service-initialization-checklist]] — tool version verification is a pre-initialization check

## Related Decisions

- [[2026-02-22-daily-cli-tool-update-via-systemd-timer]] — the architectural decision this pattern implements
- [[2026-02-22-cz-spec-workflow-retrospective]] — broader context on cohezion-engine CLI tooling

## Related Concepts

- [[workflow-orchestration]] — automated CLI updates are a maintenance orchestration pattern
- [[non-blocking-observability]] — version comparison logging provides observability into tool drift
- [[tool-use]] — keeping tools current ensures agents always have the latest capabilities
