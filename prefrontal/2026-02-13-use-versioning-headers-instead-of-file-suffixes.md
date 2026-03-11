---
title: Use Versioning Headers Instead of File Suffixes
date: '2026-02-13'
status: accepted
tags: [decision, versioning, vault, file-management]
aspect: thinker
neural:
  activation: 0.462
  stage: growing
  cluster: decisions
---

# Use Versioning Headers Instead of File Suffixes

## Context

During the compound engineering workflow, vault notes (plans, decisions, patterns) evolved through multiple iterations. The initial approach was to create versioned copies using file suffixes: `plan_v1.md`, `plan_v2.md`, `plan_v5.md`. This caused several problems:

1. **File proliferation** — a note revised 5 times created 5 separate files, cluttering directory listings
2. **Version guessing** — finding the latest version required scanning all suffixed files and comparing numbers
3. **Broken wiki-links** — `[[plan]]` pointed to the unsuffixed original; versioned copies had different names and were not linked
4. **Lost history** — git history was fragmented across files instead of showing a clean evolution of a single file
5. **Orphaned versions** — old versions were never deleted, creating confusion about which was canonical

## Decision

Use **versioning headers inside the file** instead of file suffixes. Each file maintains a single canonical path. Version history is tracked via a YAML frontmatter field and/or a changelog section within the note.

```yaml
---
title: Compound Engineering Roadmap
date: 2026-02-13
version: 5
version_history:
  - v1: Initial draft (2026-02-10)
  - v2: Added phases 6-10 (2026-02-11)
  - v3: Incorporated adversarial review feedback (2026-02-12)
  - v4: Revised cost estimates (2026-02-12)
  - v5: Final approved version (2026-02-13)
---
```

Git history shows the full evolution naturally via `git log -- path/to/file.md`.

## Consequences

**Positive:**
- Single source of truth — no file proliferation, no guessing which version is current
- Git history shows evolution naturally — `git log` and `git diff` work on one file
- Wiki-links never break — `[[note-name]]` always resolves to the current version
- Cleaner directory listings — one file per concept, not five
- Version history is human-readable in the frontmatter

**Negative:**
- Cannot view two versions side-by-side without using git diff
- Large notes with many revisions accumulate a long version_history section
- Requires discipline to update the version header on each edit

## Alternatives Considered

**File suffixes (`_v1`, `_v2`):** The approach being replaced. Rejected for the reasons listed in Context above — file proliferation, broken links, and lost history.

**Git tags per version:** Tag specific commits that represent "version milestones." Overly heavy for document versioning within a vault — tags are better suited for software releases. Rejected for ceremony-to-value ratio.

**Separate `_archive/` directory:** Move old versions to an archive directory. Partially solves file proliferation but still creates duplicate files and broken links. Rejected as a half-measure.

## Related

- [[safe-file-split-checklist]] — the checklist that governs file operations (including ensuring no orphaned versions)
- [[vault-link-audit-pattern]] — link auditing catches broken references caused by file renaming or versioning errors
- [[2026-02-24-vault-link-integrity-first-principle]] — link integrity is a first-class concern that versioning headers support
- [[concept-modularity]] — atomic notes with versioning headers maintain modularity better than versioned file copies
