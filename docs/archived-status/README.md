# Archived status reports

Historical one-off status / breakthrough / summary / final-report markdown files relocated from the repository root as part of root archaeology Wave 3 (Session 104, 2026-04-18).

## Why they're here

The repository root accumulated ~50 `*STATUS*.md` / `*BREAKTHROUGH*.md` / `*COMPLETE*.md` / `*SUMMARY*.md` files across many sessions. Each was useful in the moment (sprint handoffs, research logs, pitch materials) but they created cognitive load at the repo root and made it hard to locate the current working docs (CLAUDE.md, README.md, CONTRIBUTING.md).

They're preserved here verbatim — not pruned — because they contain genuine session reasoning that future retrospectives may want to mine.

## Searching

```bash
# Find all status reports mentioning a specific topic
grep -ri "HIHO" docs/archived-status/

# List by recency of filename-embedded date
ls docs/archived-status/ | grep 2026-04 | sort
```

## When to promote content back out

If you find yourself re-reading one of these frequently, promote its distilled content to:
- `CLAUDE.md` — if it's a coding standard or operational pattern
- `.agent/CONSTITUTION.md` — if it's a new hard constraint
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` — if it's a new learning worth a L-number
- `docs/<appropriate-dir>/` — if it's reference material

## Related

- `docs/session-logs/` — session handoffs and old LOG files (Wave 3 Cat D)
- `docs/application/` — Anthropic application artifacts (Wave 3 Cat C)
- `docs/archaeology/INVENTORY.md` — the triage catalog that drove these moves
