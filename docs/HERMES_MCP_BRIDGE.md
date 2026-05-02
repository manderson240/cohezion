---
name: "hermes-codebase-mcp-bridge"
description: "MCP bridge server exposing Cohezion tools to Hermes Agent via stdio JSON-RPC"
metadata:
  version: "1.1.0"
  project: cohezion
  tags: [mcp, hermes, bridge, cohezion]
---

# Hermes Codebase MCP Bridge

## Overview

This MCP bridge integrates your Cohezion codebase with Hermes Agent by exposing
Cohezion's capabilities as MCP tools. Hermes can access the codebase, skills,
source files, and CLI through structured tool calls.

## Installation

```bash
# From the project root
hermes mcp add cohezion \
  --command python3 \
  --args src/cohezion/integrations/hermes_mcp_bridge.py \
  --env COHEZION_ROOT=/home/mike-anderson/dev/cohezion
```

Then restart Hermes or use `/reset` to pick up the tools.

## Architecture

```
Hermes Agent
      |
      | stdio JSON-RPC
      v
hermes_mcp_bridge.py (this file)
      |
      +-- cohezion_crawl_codebase  --&gt; filesystem walk
      +-- cohezion_list_skills     --&gt; loads src/cohezion/skills/*.md
      +-- cohezion_get_skill       --&gt; reads skill file
      +-- cohezion_port_skill      --&gt; calls scripts/prime_to_hermes_converter.py
      +-- cohezion_batch_port      --&gt; batch call converter
      +-- cohezion_run_cli         --&gt; python -m cohezion &lt;args&gt;
      +-- cohezion_hermes_status   --&gt; bridge diagnostics
      +-- cohezion_read_source     --&gt; line-numbered file read
```

## Tool Reference

### cohezion_crawl_codebase
Crawl any subpackage under `src/cohezion/`. Returns file list, line counts, depth.

- subdirectory: e.g. `"flume"`, `"compound"`, `"mcp/servers"`
- max_depth: integer recursion limit
- pattern: file glob, default `"*.py"`

### cohezion_list_skills
List all 225 PRIME skills + local Hermes skills already ported.

### cohezion_get_skill
Read a PRIME skill by its filename stem.

- skill_name: e.g. `"HIHO_STABILITY_PRIME"`
- max_lines: cap lines returned
- offset: starting line (1-indexed)

### cohezion_port_skill_to_hermes
Port a single PRIME skill to Hermes format using the built-in converter.

- skill_name: PRIME stem
- dry_run: boolean

### cohezion_batch_port_skills
Port multiple PRIME skills in one call.

- skill_names: list of PRIME stems
- dry_run: boolean

### cohezion_run_cli
Execute a Cohezion CLI command.

- command: e.g. `"simulate --example hello"`
- timeout: seconds (default 60)

### cohezion_hermes_status
Bridge diagnostics: version, project root, skill counts, module load state.

### cohezion_read_source
Read any project file with line numbers.

- relative_path: path from project root
- limit: max lines (default 100)
- offset: starting line (1-indexed, default 1)

## Changelog

### v1.1.0
- Fixed `_run_command()` to use synchronous subprocess + PYTHONPATH injection
- Added `_resolve_python()` for venv-aware Python selection
- Fixed `_list_local_hermes_skills()` to detect Cohezion skills by frontmatter tags
- `cohezion_run_cli` now works end-to-end (verified with `simulate --example hello`)

### v1.0.0
- Initial MCP bridge with 8 tools
- JSON-RPC 2.0 stdio transport
- MCP protocol v2024-11-05
