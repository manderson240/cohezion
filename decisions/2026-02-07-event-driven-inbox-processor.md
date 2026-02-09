---
title: "Event-Driven Inbox Processor Daemon"
date: "2026-02-07"
status: proposed
tags: [decision, architecture, automation, inbox]
---
## Context

The Cohezion vault's `inbox/` directory serves as a triage point for raw ideas and unsorted notes. Currently, processing these notes into permanent vault locations (decisions, experiments, patterns, concepts) requires manual intervention — a human must read each note, decide where it belongs, flesh it out, and move it.

The [[compound-engineering]] approach only works if knowledge actually flows from rough capture to structured storage. A bottleneck at the inbox defeats the purpose.

The existing Cloud Vault MCP Server already provides the building blocks: `VaultOps` for filesystem operations, `CompoundOps` for logging decisions/experiments/patterns, and `ObsidianOps` for backlinks and templates. These are battle-tested through the MCP server's API surface.

## Decision

Build a standalone event-driven daemon that watches `inbox/` for new or modified notes and automatically processes them through an AI classification and execution pipeline.

**Architecture:**

1. **File watching** — Use Python's `watchdog` library to monitor `inbox/` for filesystem events (create, modify). Debounce rapid edits to avoid processing mid-write.
2. **Classification** — When a note stabilizes, send its content to Claude for classification: determine the target directory (`decisions/`, `experiments/`, `patterns/`, `concepts/`) and what processing is needed (research expansion, template fitting, cross-linking).
3. **Task execution** — Dispatch a Claude Code agent (general-purpose subagent with web search) to flesh out the note: research the topic, structure content to match the target directory's `_template.md` schema, and add appropriate YAML frontmatter.
4. **Filing** — Move the processed note from `inbox/` to its target directory using `VaultOps`. Add `[[wiki-links]]` to related existing notes using `ObsidianOps` backlink discovery.
5. **Reuse existing ops** — The daemon imports and calls `VaultOps` and `CompoundOps` directly rather than going through the MCP HTTP layer, avoiding unnecessary serialization overhead.

**Daemon lifecycle:** Runs as a background process, configurable via a simple YAML config for watch paths, debounce intervals, and classification prompts.

## Consequences

- **Positive:** Raw ideas captured in `inbox/` automatically become structured vault knowledge, closing the loop on the [[compound-engineering]] workflow.
- **Positive:** Reusing `VaultOps`/`CompoundOps` means the daemon inherits all existing vault conventions (frontmatter schemas, directory structure, git tracking).
- **Positive:** The watchdog approach is simple, well-tested, and requires no polling.
- **Negative:** Requires a running Claude API connection; notes won't process if the API is unavailable.
- **Negative:** AI classification may misfile notes — needs a review mechanism or confidence threshold.
- **Negative:** Cost implications of running Claude on every inbox note.

## Alternatives Considered

- **Cron-based polling:** Simpler but less responsive. Watchdog provides near-instant reaction to new notes.
- **Obsidian plugin:** Would keep everything inside Obsidian but limits the processing to what the plugin API supports. A standalone daemon can use the full Python ecosystem and Claude API.
- **MCP-only approach (HTTP calls):** Going through the MCP server HTTP layer adds latency and complexity for a process running on the same machine. Direct import of the ops modules is cleaner.
- **Manual processing only:** The status quo. Works but creates a bottleneck that discourages quick capture.
