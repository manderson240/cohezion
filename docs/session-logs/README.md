# Session logs and handoffs

Archive of per-session handoff markdown and raw LOG files (`LOG.old.*`). Kept because they preserve session-end reasoning that MISSION_JOURNAL one-line summaries can't.

## Naming

- `HANDOFF*.md` — structured handoff doc (usually includes git-add sequences, next-step lists)
- `LOG.old.<unix-ms>` — raw session log dump; timestamp is milliseconds since Unix epoch
- `REBOOT_HANDOFF.md` — boot-across-sessions handoff (when machine was power-cycled)

## Querying

```bash
# Handoffs from a specific month
ls docs/session-logs/ | grep 2026-04

# Search across all raw logs
grep -l "HIHO" docs/session-logs/LOG.old.*
```

## Related

- `src/cohezion/knowledge_graph/MISSION_JOURNAL.md` — one-line summary of every session
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` — numbered learnings extracted from sessions
- `memory/MEMORY.md` — compiled cache of recent decisions
