---
title: Vault Link Integrity Is a First-Class Concern
date: 2026-02-24
status: accepted
tags: [decision, vault, links, integrity, obsidian, compound-engineering]
---

# Vault Link Integrity Is a First-Class Concern

## Context

After an 8-pass audit of the 906-note vault, it became clear that broken wiki-links accumulate silently and at scale. Starting with ~728 broken link targets (18.7% of all links), systematic multi-pass repair brought it to ~167 legitimately non-fixable targets — primarily template placeholders, skill file references, and source code paths.

The knowledge graph is only as useful as its navigability. A vault with 728 broken links is effectively a collection of isolated notes, not a connected knowledge base.

## Decision

Treat vault link integrity as a first-class engineering concern with the same discipline as test coverage:

1. **Audit before and after bulk note creation** using the [[vault-link-audit-pattern]]
2. **Exclude `.worktrees/`** from all vault scans (they inflate counts by 3-5×)
3. **Use semantic IDs** for lesson files, not sequential counters tied to corpus size
4. **CI test** that verifies zero broken links in vault content (excluding known-skippable classes)
5. **Multi-pass** is the correct approach — fix classes of breakage, not individual links

## Consequences

- Vault navigation works reliably across 906+ notes
- New notes added via automation must use the established ID conventions
- The lessons index must be regenerated when lesson files change IDs
- A CI check (vault test suite) enforces link integrity going forward

## Alternatives Considered

**Path-prefixed links** (`[[patterns/foo]]`): Obsidian resolves by filename stem only; path prefixes break links silently. Rejected.

**Sequential lesson numbering** (`lesson-118`): Breaks when the corpus boundary changes. Rejected in favor of semantic IDs.

**Ignore broken links**: At 18.7% broken rate, the graph is too fragmented to be useful. Rejected.

## Related

- [[vault-link-audit-pattern]]
- [[lesson-39-vault-audit-must-exclude-worktrees]]
- [[lesson-40-sequential-numbering-offset-corrupts-indexes]]
- [[2026-02-24-vault-link-integrity-sprint]]
