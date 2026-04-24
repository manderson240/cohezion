---
name: bmad-brainstorming
description: 'Facilitate interactive brainstorming sessions using diverse creative techniques and ideation methods. Use when the user says help me brainstorm or help me ideate.'
pi_integrated: true
---

Follow the instructions in ./workflow.md.

## Pi Integration

When invoked from within the Pi harness (`.pi/settings.json` present), this skill automatically:
- Loads Pi-specific brainstorming settings from `.pi/settings.json` → `brainstorming` key
- Detects and cross-references Pi session logs for continuation
- Enables MCP tool calls if `brainstorming.mcp_enabled` is configured
- Persists completed sessions to the Cohezion vault if `brainstorming.vault_persistence` is set
