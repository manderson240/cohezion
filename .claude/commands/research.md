---
description: Run the daily research pipeline to discover new techniques and tools
argument-hint: '"run", "run --quick", "triage", or "status"'
---

# /research — Daily Research Pipeline

Run the Cohezion research pipeline to scan public sources for new techniques, tools, and patterns.

## Usage

The user's argument is: $ARGUMENTS

## Commands

### `run` (default)
Full pipeline: harvest → score → publish. Creates inbox notes and daily digest.

```bash
research/.venv/bin/python3 research/cli.py run --config research/sources.yaml --vault .
```

### `run --quick`
Quick mode: web search only, keyword scoring, no Ollama LLM scoring.

```bash
research/.venv/bin/python3 research/cli.py run --quick --config research/sources.yaml --vault .
```

### `run --focus <area>`
Filter to one focus area: `compound-engineering`, `token-efficiency`, `context-awareness`, or `app-creation`.

```bash
research/.venv/bin/python3 research/cli.py run --focus compound-engineering --config research/sources.yaml --vault .
```

### `triage`
Review existing inbox research notes and suggest vault placement.

```bash
research/.venv/bin/python3 research/cli.py triage --vault .
```

### `status`
Show last run statistics.

```bash
research/.venv/bin/python3 research/cli.py status --vault .
```

## After Running

1. Read the CLI's JSON output and summarize results for the user
2. If `run` was executed, read the daily digest note and present highlights
3. If skill candidates were found, mention them with `/learn` integration path
4. If `triage` was executed, present the inbox notes with vault placement suggestions
