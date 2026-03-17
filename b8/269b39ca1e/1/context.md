# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Remove Serena Plugin from Claude Code

## Context

Serena (`serena@claude-plugins-official`) is a Claude Code plugin providing semantic code analysis tools (`find_symbol`, `replace_symbol_body`, etc.). Its capabilities are fully redundant with Claude Code's built-in `Read`, `Edit`, `Grep`, `Glob`, and `LSP` tools. It injects ~2,000+ tokens of system instructions into every session and loads 20+ deferred tool definitions — pure overhead.

A previous removal on ...

### Prompt 2

Base directory for this skill: /home/mike-anderson/dev/cohezion/.claude/skills/claude-code-plugin-removal

# Claude Code Plugin Removal

## Problem

A Claude Code plugin crashes on startup every session, causing a 30-second connection
timeout. Or a plugin is redundant and needs to be cleanly removed. Simply deleting
the plugin directory is insufficient — state persists in 4 separate locations.

## Context / Trigger Conditions

- Session start shows MCP connection timeout for a specific plugin...

### Prompt 3

What other claude code optimizations can me make?  review /release-notes

