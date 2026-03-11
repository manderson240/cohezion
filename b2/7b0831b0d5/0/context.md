# Session Context

## User Prompts

### Prompt 1

[Request interrupted by user for tool use]

### Prompt 2

Implement the following plan:

# Serena MCP Plugin — Investigation & Recommendation

## Context

Serena is a Claude Code plugin (by Oraios) that provides semantic code analysis via Language Server Protocol (LSP). It's installed as a Claude Code plugin at `~/.claude/plugins/cache/claude-plugins-official/serena/`. It launches via `uvx --from git+https://github.com/oraios/serena serena start-mcp-server`.

**Problem**: Serena crashes on startup every session with:
```
SerenaConfigError: `projects...

### Prompt 3

Provide a code review for the given pull request.

To do this, follow these steps precisely:

1. Use a Haiku agent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from you from earlier. If so, do not proceed.
2. Use another Haiku agent to give you a list of file paths to (but not the contents of) any relevant CLAUDE.md files from the c...

### Prompt 4

1

