---
name: daily-research
description: Run the daily research pipeline to discover AI techniques, tools, and patterns relevant to Cohezion
triggers:
  - user says "research", "scan for papers", "find new tools", "what's new in AI"
  - user invokes /research command
---

# Daily Research Pipeline Skill

Orchestrates the Cohezion research pipeline via CLI, presenting results conversationally.

## When to Use
- User asks about new AI research, tools, or techniques
- User wants to discover relevant papers or projects
- User invokes `/research` command
- Scheduled daily research runs

## Execution

```bash
# Full run
research/.venv/bin/python3 research/cli.py run --config research/sources.yaml --vault .

# Quick scan
research/.venv/bin/python3 research/cli.py run --quick --config research/sources.yaml --vault .

# Check status
research/.venv/bin/python3 research/cli.py status --vault .
```

## Presenting Results

After running the pipeline:
1. Parse the JSON output
2. Summarize: X findings discovered, Y inbox notes created, Z skill candidates
3. Highlight top findings per focus area (from the daily digest)
4. Flag skill candidates that could be extracted via `/learn` → `/vault`
5. Suggest triage for high-scoring findings
