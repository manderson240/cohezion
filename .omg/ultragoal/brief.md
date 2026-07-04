# Duplication Reduction Sprint 2 - Brief

## Objective
Deduplicate internal helper functions in `src/cohezion/api/journey_status.py` using jscpd and the oh-my-antigravity (OmA) ultragoal pattern.

## CAPABILITIES & PLUGINS UTILIZED
1. **Oh-My-Antigravity (OmA)**: The `$ultragoal` playbook manages execution checkpoints.
2. **jscpd MCP Server**: Identifies copy/paste structures inside `journey_status.py`.

## Architecture Boundaries & Constraints
- Extract a clean async helper `_update_journey_state` inside `journey_status.py`.
- Validate functionally with unit tests (`make test-fast`).
