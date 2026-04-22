---
title: "10 Claude Log Mining Architecture"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.78
  stage: growing
  synapse_in: 9
  synapse_out: 13
---
## Definition

Claude log mining architecture is the system for extracting structured knowledge from Claude Code session logs. Each Claude Code session generates detailed logs containing tool calls, reasoning traces, error patterns, and recovery strategies. Log mining transforms these raw logs into actionable vault content -- lessons learned, operational patterns, performance metrics, and debugging insights that inform future agent sessions.

The architecture has three stages: **collection** (reading JSONL session logs from `~/.claude/projects/`), **extraction** (parsing tool calls, errors, and outcomes into structured records), and **integration** (converting extracted records into vault notes with proper frontmatter and wiki-links).

## Key Properties

- **JSONL source format**: Claude Code logs are stored as newline-delimited JSON, one entry per tool call or message.
- **Pattern detection**: Mining identifies recurring error patterns, successful recovery strategies, and performance bottlenecks.
- **Lesson generation**: Extracted patterns become numbered lesson notes (e.g., `lesson-17-stale-branch-mining`).
- **Adversarial review**: Mined insights are validated through [[10-log-mining-adversarial-review]] before becoming permanent vault content.
- **Privacy awareness**: Logs may contain sensitive data; mining pipelines must filter credentials and personal information.

## Examples

- Mining session logs to discover that Ollama cold-start latency consistently costs 5-30 seconds (became [[lesson-06-ollama-latency]])
- Extracting the pattern that unmocked live services cause test hangs (became [[lesson-34-test-hang-unmocked-live-service]])
- Identifying that stale git branches contain valuable historical context worth preserving (became [[lesson-17-stale-branch-mining]])

## Related Papers

- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]]
- [[lesson-16-pre-commit-hooks-stage-override]]
- [[lesson-17-stale-branch-mining]]
- [[lesson-21-runtime-json-pollution]]
- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-34-test-hang-unmocked-live-service]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[lesson-38-singleton-executor-for-sessions-new]]

## Related Concepts

- [[10-log-mining-adversarial-review]] -- adversarial validation of mined insights
- [[experience-feedback-loop]] -- the broader loop from experience to knowledge to improved performance
- [[session-retrospective]] -- manual review that complements automated log mining
- [[non-blocking-observability]] -- telemetry patterns that make log mining possible without impacting performance

## Relevance to Cohezion

Log mining is how the Cohezion vault learns from its own operational history. The 38+ lessons in this vault were extracted from real Claude Code sessions through this architecture. Each lesson represents a non-obvious discovery -- a bug, a workaround, a performance insight -- that agents now load as context to avoid repeating mistakes. Log mining is the feedback loop that makes the vault a living knowledge system rather than a static document store.
