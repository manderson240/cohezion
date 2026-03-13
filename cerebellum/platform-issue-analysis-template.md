---
title: "Platform Issue Analysis Template"
date: "2026-02-17"
tags: [pattern, debugging, operational-forensics, methodology]
aspect: thinker
neural:
  activation: 0.72
  stage: growing
  synapse_in: 5
  synapse_out: 8
---

# Platform Issue Analysis Template

## Problem

When a platform issue is reported (test failures, service outages, configuration errors, performance degradation), investigation often proceeds haphazardly: jumping between hypotheses, checking random logs, and applying speculative fixes. Without a structured analysis framework, debugging wastes time on irrelevant paths and fails to identify root causes systematically. The "fix it and hope" approach leads to recurrence because the underlying cause is not understood.

## Solution

Apply a **structured 5-step analysis template** to every platform issue. The template enforces systematic investigation before any fix is attempted:

### Step 1: Symptom Capture
Document the observable symptoms exactly as reported:
- Error messages (full text, not paraphrased)
- Failing test names and output
- Affected services/endpoints
- When it started (or was first noticed)
- Who/what is impacted

### Step 2: Reproduction
Establish a reliable reproduction path:
- Exact commands to reproduce the issue
- Environment details (OS, Python version, dependency versions)
- Whether it reproduces consistently or intermittently
- Minimal reproduction case (strip away unrelated context)

### Step 3: Investigation
Systematic evidence gathering:
- Check recent changes (`git log`, `git diff` since last known good state)
- Check configuration (env vars, config files, `.env`)
- Check dependencies (`uv tree`, `pip list`, version mismatches)
- Check infrastructure (service status, port availability, disk space)
- Check logs (journald, application logs, stderr output)

### Step 4: Root Cause
Identify the root cause with evidence:
- What specifically changed or failed?
- Why did the existing safeguards not catch it?
- Is this a new issue or a latent bug exposed by a trigger?

### Step 5: Fix + Prevention
Apply the fix and prevent recurrence:
- Minimal fix that addresses root cause (not symptoms)
- Test that reproduces the issue (RED) then verifies the fix (GREEN)
- Prevention mechanism (lint rule, CI check, configuration validation)

## Code Example

Applying the template to a real issue:

```markdown
## Issue: 62 tests fail after system crash

### Step 1: Symptom
- `uv run pytest` → ModuleNotFoundError: No module named 'pytest'
- All 62 tests fail to start (not individual failures)

### Step 2: Reproduction
- After power loss on 2026-02-22
- Reproduces every time with `uv run pytest`
- pyproject.toml shows pytest in dev dependencies

### Step 3: Investigation
- `uv.lock` intact, `pyproject.toml` intact
- `.venv/lib/python3.12/site-packages/` missing pytest directory
- Other packages (asyncio, pathlib) present → partial corruption
- Crash interrupted venv package installation mid-write

### Step 4: Root Cause
- Crash corrupted venv site-packages (partial write)
- uv checks lock file, sees versions match, skips reinstall
- Lock file says "installed" but filesystem says "missing"

### Step 5: Fix
- `uv add --dev pytest pytest-cov pytest-asyncio` (force reinstall)
- Added venv integrity check to session start checklist
- Created: decisions/2026-02-22-post-crash-venv-recovery.md
```

## When to Use

- **Any platform issue that takes >5 minutes to diagnose** — the template pays for itself
- **Recurring issues** — if an issue has been "fixed" before but came back, the previous fix missed the root cause
- **Cross-team debugging** — the template creates a shared investigation artifact that others can review
- **Post-incident documentation** — the completed template serves as the post-mortem document

**Skip for:** Obvious typos, missing imports, and other issues where the symptom immediately reveals the fix.

## Related Decisions

- [[2026-02-10-operational-forensics-compound-engineering]] — the decision that created the operational forensics methodology this template operationalizes
- [[2026-02-17-phase-2-service-initialization-gap-discovery]] — concrete example of platform issue analysis in action
- [[2026-02-14-settings-files-validation-and-fix]] — canonical application: /doctor diagnostic to investigation to root cause to fix
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]] — repo size investigation using this methodology

## Related Patterns

- [[service-initialization-checklist]] — initialization issues are a common class of platform problems this template diagnoses
- [[troubleshooting-mcp-infrastructure]] — MCP-specific troubleshooting runbook that follows this analysis structure
- [[runbook-health-checks]] — health checks as a proactive version of platform issue detection
- [[session-retrospective-notes]] — completed issue analyses feed into session retrospectives as lessons learned
