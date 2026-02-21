# Maximize Node Connections Implementation Plan

Created: 2026-02-21
Status: PENDING
Approved: No
Iterations: 0
Worktree: Yes

> Planning in progress - exploration complete, design phase next

## Summary

**Goal:** Maximize node connections in the Cohezion vault by making the linking system proactive instead of reactive. Enhance the existing `vault_linker` tool, add Claude Code hooks for automatic link injection on file creation/edit, and improve connection quality using tag-based and content-based matching.

## Exploration Findings (Completed)

### Current State (from vault_linker analyze)
- **Total Files:** 666
- **Total Link Targets:** 801
- **Valid Links:** 448 (55%)
- **Broken Links:** 353 (44%) — 260 missing concepts, 91 external refs, 2 date-prefixed
- **Papers with null tags:** 2
- **Top broken:** `agent context` (27 refs), `mcp infrastructure architecture` (9 refs)

### Existing Infrastructure
1. **vault_linker tool** (`tools/vault_linker/`) — Python package with:
   - `parser.py` — VaultParser: walks vault, builds link graph, classifies broken links
   - `resolver.py` — LinkResolver: fuzzy matching for broken links (4 strategies, confidence-scored)
   - `tagger.py` — TagPopulator: generates tags from keywords + similar_papers inheritance
   - `stubgen.py` — StubGenerator: creates concept stubs for frequently-referenced broken links
   - `injector.py` — LinkInjector: adds Related Papers/Concepts sections based on tag overlap
   - `report.py` — ReportGenerator: vault health metrics
   - `__main__.py` — CLI with `analyze` and `fix` commands
   - Tests: `tools/tests/test_*.py` for each module

2. **Previous plans:**
   - `2026-02-19-connect-unlinked-vault-nodes.md` — VERIFIED, built the vault_linker
   - `2026-02-10-compound-node-linking-plan.md` — Rejected after adversarial review (cost/quality issues)
   - `canvas-driven-manual-linking.md` — Pattern for manual linking (proven 90-100% quality)

3. **Claude Code hooks** (`.claude/settings.json`):
   - Has existing PreToolUse/PostToolUse hooks for `track_session`, `Task`, `record_decision`, `record_outcome`, `TodoWrite`
   - No hooks currently trigger on Write/Edit for vault files

4. **Key gap:** Current system is entirely **reactive** — you must manually run `vault_linker fix`. Nothing happens automatically when notes are created or edited.

### Hook System Capabilities (from Context7)
- **PostToolUse** hooks can trigger on `Write|Edit` matcher
- Command-type hooks receive tool input via stdin JSON (`jq -r '.tool_input.file_path'`)
- Exit 0 = stdout shown in transcript; exit 2 = stderr fed back to Claude
- Can run shell scripts that invoke the vault_linker modules

## Design Questions (To Be Resolved)

1. **Hook scope:** Should the PostToolUse hook trigger on ALL Write/Edit operations, or only vault markdown files?
2. **Hook action:** Should the hook auto-inject links, or just report suggestions to Claude?
3. **Connection strategies to add:**
   - Content-based keyword matching (beyond just tag overlap)
   - Bidirectional link detection (if A links to B, suggest B link to A)
   - Orphan detection on new file creation
   - Batch re-analysis after multiple files change

---

_Planning paused for system reboot. Resume with `/spec docs/plans/2026-02-21-maximize-node-connections.md`_
