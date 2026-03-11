---
type: antigravity-artifact
session_id: bee84f15-8915-4cbf-8400-f5ca9e10c3f2
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.319
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Cohezion CLI Hardening

The user requested "Hardened Security" and "Edge Case" consideration. 

## User Review Required
> [!IMPORTANT]
> The `verify` command's `subprocess` call will be wrapped in strict sanitization to prevent potential shell injection if input sources are ever externalized.

## Proposed Changes

### [CLI Hardening]
#### [MODIFY] [cohezion_cli.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/cohezion_cli.py)
- **Input Validation:**
    - `cmd_research`: Enforce strict alphanumeric+space regex for queries.
    - `cmd_browser`: Validate URL schema (http/https) before launching agent.
- **Robustness:**
    - `TerminalNexus.run`: Wrap the main loop in a broad `try/except` to log errors and restart the `digest_logs` stream instead of crashing.
    - `cmd_journey`: Handle `KeyboardInterrupt` gracefully to allow clean exit from interactive mode.
- **Security:**
    - `verify`: Use `shlex.split` for constructing commands if strings are used, or strictly typed lists for `subprocess.run`.

## Verification Plan

### Edge Case Tests
1. **Invalid URL**: Run `python scripts/drivers/cohezion_cli.py browser "javascript:alert(1)"` -> Expect Error.
2. **Dashboard Crash Simulation**: Corrupt the log file while `dash` is running -> Expect UI to recover or display error status, not exit.
3. **Interrupt**: `Ctrl+C` in Journey -> Expect "Journey Aborted" cleanly.

### Security Smoke Test
- Run `research` with special characters `; rm -rf /`.
