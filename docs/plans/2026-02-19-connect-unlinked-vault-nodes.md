# Connect Unlinked Vault Nodes Implementation Plan

Created: 2026-02-19
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Fix the vault's broken knowledge graph by resolving 441 broken wiki-links, connecting orphan nodes, populating missing tags on 54 papers, and building a reusable analysis tool for ongoing vault health monitoring.

**Architecture:** A Python package (`tools/vault_linker/`) that parses all vault markdown files, builds a link graph, identifies connectivity issues, and generates fixes. Split into focused modules to stay under 300-line file limits. Operates in two modes: `analyze` (report-only) and `fix` (apply changes). **PyYAML is used for reading frontmatter only; all writes use surgical regex replacement to preserve formatting.**

**Tech Stack:** Python 3.10+, PyYAML (read-only), standard library (pathlib, re, collections, argparse)

## Scope

### In Scope

- Python analysis script to parse vault files, build link graph, find broken links
- Map broken links to existing files where possible (fuzzy matching)
- Create concept stub notes for frequently-referenced broken targets
- Populate `tags: null` on 54 papers using title keywords, body content, and validated `similar_papers` metadata
- Add "Related Papers" and "Related Concepts" sections to files that lack them (detecting existing section variants)
- Convert `similar_papers` frontmatter to wiki-links **only when source and target share tag/keyword overlap** (skip nonsensical cross-domain associations)
- Report generation showing vault health metrics

### Out of Scope

- Changes to the 3D graph plugin code
- Changes to the MCP server code
- Modifying daily notes (143 unlinked — parsed for graph completeness but not modified; these are session logs)
- Creating full content for stub notes (stubs get title + tags + placeholder sections only)
- Automated content-based semantic similarity (we use existing metadata only)

## Prerequisites

- Python 3.10+ available
- PyYAML installed (`pip install pyyaml`)
- Vault files accessible at current working directory
- **Worktree isolation** (Worktree: Yes) provides a clean branch for all modifications, making it safe to experiment and easy to review via `git diff` before merging back

## Context for Implementer

> This section is critical for cross-session continuity.

- **Vault structure:** Markdown files across 20+ directories including `decisions/`, `experiments/`, `patterns/`, `papers/`, `projects/`, `concepts/`, `daily/`, `inbox/`, `learnings/`, `lessons/`, `archived/`, `benchmarks/`, `cycles/`, `missions/`, `research/`, `retrospectives/`, `sessions/`, `skills/`. **The parser must walk the vault root recursively** (excluding `.git/`, `node_modules/`, `.obsidian/`, `mcp-server/`, `obsidian-plugin/`, `.claude/`, `tools/`) rather than enumerate directories.
- **Read-only directories:** `daily/` notes should be **parsed for graph completeness** (their outgoing links count toward incoming link metrics and stub reference counts) but **not modified** by the fix mode.
- **Frontmatter format:** YAML between `---` markers. Tags are arrays: `tags: [concept, ai]`. Papers often have `tags: null` and `similar_papers:` list in frontmatter.
- **Wiki-link format:** `[[note-name]]` or `[[note-name|Display Text]]`. Obsidian resolves these by filename (without directory prefix or `.md` extension).
- **Concept template:** Has sections: Definition, Key Properties, Examples, Primary Sources, Related Papers (with `[[paper-name]]`), Related Concepts (with `[[concept-name]]`), Relevance to Cohezion. See `concepts/quantum-sensors.md` for reference.
- **Paper frontmatter:** Includes `similar_papers:` YAML list (plain strings, not wiki-links), `connectivity`, `cross_domain`, `completion`, `connectivity_summary` metrics. See `papers/jwst-dark-matter-map.md` for reference.
- **Current state:** 684 unique link targets, 441 broken (64%), 243 valid (36%). 54/86 papers have `tags: null`. 22/49 concepts have no outgoing links.
- **Gotchas:**
  - Some wiki-links use `|` for display text: `[[file|display]]`. Some use date prefixes: `[[2026-02-10-decision-name]]`. Case sensitivity matters in filenames but Obsidian is case-insensitive.
  - **PyYAML round-tripping corrupts frontmatter** — `yaml.dump()` changes quote styles, key ordering, and breaks titles with colons. Use PyYAML for **reading only**; all writes must use surgical regex replacement (e.g., replace `tags: null` line directly).
  - **17 papers have inline wiki-links** in a `Relevant to [[...]], [[concept1]], [[concept2]]` pattern. The link injector must scan ALL existing wiki-links in the entire file body (not just `## Related` sections) to avoid duplicating these.
  - **`similar_papers` metadata contains nonsensical associations** (e.g., JWST dark matter paper lists `claude-code-swiftui-skill-patterns`). Never blindly convert — require tag/keyword overlap validation.
  - **Broken link categories:** The 441 broken links include external references (`[[fractal_universe]]`, `[[enhanced_simulator]]`), references to deleted files, and genuine missing concepts. Classify before acting.
  - **Existing "Related" section variants:** Files use `## Related`, `## Related Papers`, `## Related Concepts`, `## See Also`. Detect all variants; append to existing sections rather than creating new ones.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Vault parser and link graph builder
- [x] Task 2: Broken link resolver (fuzzy matching)
- [x] Task 3: Paper tag populator
- [x] Task 4: Concept stub generator
- [x] Task 5: Cross-reference link injector
- [x] Task 6: Analysis report and CLI interface
- [x] Task 7: Run tool and apply fixes to vault

**Total Tasks:** 7 | **Completed:** 7 | **Remaining:** 0

## Implementation Tasks

### Task 1: Vault Parser and Link Graph Builder

**Objective:** Create the core parsing engine that reads all vault markdown files, extracts frontmatter and wiki-links, and builds an in-memory graph of connections.

**Dependencies:** None

**Files:**
- Create: `tools/vault_linker/__init__.py`
- Create: `tools/vault_linker/__main__.py` (CLI entry point — Task 6)
- Create: `tools/vault_linker/parser.py` (this task)
- Test: `tools/tests/test_parser.py`

**Key Decisions / Notes:**
- Use `PyYAML` for frontmatter **reading only**, `re` for wiki-link extraction
- **Recursively walk vault root** for `.md` files, excluding `.git/`, `node_modules/`, `.obsidian/`, `mcp-server/`, `obsidian-plugin/`, `.claude/`, `tools/`, `htmlcov/`, `docs/`
- Build two data structures: `files_index` (filename → metadata) and `link_graph` (adjacency list of outgoing/incoming links)
- Handle wiki-link variants: `[[name]]`, `[[name|display]]`, `[[name#heading]]`
- Index files by stem (no directory prefix, no `.md`), case-insensitive for matching
- Parse `similar_papers` from paper frontmatter as additional connection data
- Track which directory each file belongs to (needed for read-only enforcement on `daily/`)
- Classify broken links into categories: (a) resolvable via fuzzy match, (b) external/non-vault references, (c) references to deleted files, (d) genuinely missing concepts

**Definition of Done:**
- [ ] Parser correctly extracts frontmatter from all vault files
- [ ] Wiki-links extracted including display-text and heading variants
- [ ] Link graph built with incoming and outgoing edges
- [ ] `similar_papers` frontmatter parsed and stored
- [ ] Files indexed case-insensitively by stem name

**Verify:**
- `cd tools && python -m pytest tests/test_vault_linker.py -q -k "test_parse"` — parser tests pass

### Task 2: Broken Link Resolver (Fuzzy Matching)

**Objective:** Build a resolver that maps broken wiki-links to existing files using fuzzy matching (case-insensitive, slug normalization, common transforms).

**Dependencies:** Task 1

**Files:**
- Create: `tools/vault_linker/resolver.py`
- Test: `tools/tests/test_resolver.py`

**Key Decisions / Notes:**
- Matching strategies in priority order:
  1. Case-insensitive exact match (`[[Agentic Ai]]` → `agentic-ai.md`)
  2. Slug normalization: spaces→hyphens, remove special chars (`[[Agent Architecture]]` → `agent-architecture.md` if it exists)
  3. Prefix stripping: remove date prefixes for matching (`[[2026-02-10-decision]]` → look for `decision.md`)
  4. **Constrained partial match:** link text must match a full hyphen-delimited slug segment (e.g., `[[dark-matter]]` matches `dark-matter-detection.md` but `[[ai]]` does NOT match `ai-safety-alignment.md`). Partial matches are **report-only suggestions**, never auto-applied.
- Output a mapping: `{broken_link: suggested_target}` with confidence scores
- Links with no match remain flagged as "unresolvable"
- **Only auto-apply matches with confidence >= 0.8** (strategies 1-3). Strategy 4 matches are suggestions only.

**Definition of Done:**
- [ ] Case-insensitive matching resolves links like `[[Agentic Ai]]` → `agentic-ai`
- [ ] Slug normalization handles spaces, underscores, special characters
- [ ] Mapping output includes confidence score per match
- [ ] Unresolvable links are tracked separately

**Verify:**
- `cd tools && python -m pytest tests/test_vault_linker.py -q -k "test_resolve"` — resolver tests pass

### Task 3: Paper Tag Populator

**Objective:** Generate meaningful tags for the 54 papers that have `tags: null` using their title, body content, and validated `similar_papers` metadata.

**Dependencies:** Task 1

**Files:**
- Create: `tools/vault_linker/tagger.py`
- Test: `tools/tests/test_tagger.py`

**Key Decisions / Notes:**
- Extract keywords from paper title AND first paragraph/key findings section (lowercase, split, remove stopwords)
- Cross-reference with existing concept names — if a concept matches a keyword, use that concept name as a tag
- Use the tag vocabulary from the 32 papers that already have tags as a controlled vocabulary
- If paper has `similar_papers` that have tags, inherit common tags **only from similar_papers that share keyword overlap** (skip irrelevant associations)
- Generate 3-5 tags per paper
- **Write tags using surgical regex replacement** — find the `tags: null` line and replace with `tags: [tag1, tag2, ...]`. Do NOT use `yaml.dump()` (corrupts formatting)

**Definition of Done:**
- [ ] Papers with `tags: null` get 3-5 meaningful tags generated
- [ ] Tags are derived from title keywords and cross-referenced with existing concepts
- [ ] Tags written as proper YAML arrays in frontmatter
- [ ] Existing papers with valid tags are not modified

**Verify:**
- `cd tools && python -m pytest tests/test_vault_linker.py -q -k "test_tag"` — tag generation tests pass

### Task 4: Concept Stub Generator

**Objective:** Create minimal concept stub files for frequently-referenced broken link targets that don't map to existing files (top 20+ by reference count).

**Dependencies:** Task 2

**Files:**
- Create: `tools/vault_linker/stubgen.py`
- Test: `tools/tests/test_stubgen.py`

**Key Decisions / Notes:**
- Only create stubs for broken links referenced 3+ times
- **Skip date-prefixed links** (e.g., `[[2026-02-10-decision-name]]`) — these are references to dated artifacts, not concepts
- **Skip known external references** (e.g., `[[fractal_universe]]`, `[[enhanced_simulator]]`, `[[lab_agent.py]]`) — these reference code/systems, not concepts
- Follow existing concept template: frontmatter (title, date, tags), Definition placeholder, Related Papers (auto-populated from files that link to it), Related Concepts (auto-populated from co-occurring links)
- File created at `concepts/<slug>.md`
- Stubs are clearly marked as auto-generated: `> Auto-generated stub. Expand with full content.`

**Definition of Done:**
- [ ] Stubs created for broken links with 3+ references
- [ ] Stubs follow concept template with proper frontmatter
- [ ] Related Papers section populated from files that reference the concept
- [ ] Stubs marked as auto-generated

**Verify:**
- `cd tools && python -m pytest tests/test_vault_linker.py -q -k "test_stub"` — stub generation tests pass

### Task 5: Cross-Reference Link Injector

**Objective:** Add wiki-links to papers and concepts that lack "Related" sections, using existing metadata (`similar_papers`, shared tags, co-occurrence in other notes).

**Dependencies:** Task 1, Task 3

**Files:**
- Create: `tools/vault_linker/injector.py`
- Test: `tools/tests/test_injector.py`

**Key Decisions / Notes:**
- **Relevance validation for `similar_papers`:** Only convert entries where source and target share at least one tag or concept keyword. Skip nonsensical cross-domain associations.
- For papers: convert validated `similar_papers` to a "## Related Papers" section with wiki-links at the bottom
- For papers: add "## Related Concepts" section linking to concepts that share tags
- For concepts missing "Related Papers": find papers whose tags overlap with the concept's tags
- **Scan ALL existing wiki-links in the entire file body** (not just `## Related` sections) before injecting — 17 papers have inline `Relevant to [[...]]` links that must not be duplicated
- **Detect existing section variants:** `## Related`, `## Related Papers`, `## Related Concepts`, `## See Also`. Append to existing sections rather than creating new ones
- Limit to 5-8 related items per section to avoid noise

**Definition of Done:**
- [ ] Papers get "Related Papers" section from `similar_papers` frontmatter
- [ ] Papers get "Related Concepts" section from shared tags
- [ ] Concepts get "Related Papers" populated from tag overlap
- [ ] No duplicate links added to files that already have them
- [ ] Related sections limited to 5-8 items

**Verify:**
- `cd tools && python -m pytest tests/test_vault_linker.py -q -k "test_inject"` — injection tests pass

### Task 6: Analysis Report and CLI Interface

**Objective:** Add CLI interface with `analyze` and `fix` modes, plus a markdown report showing vault health metrics before and after fixes.

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5

**Files:**
- Create: `tools/vault_linker/__main__.py` (CLI entry point)
- Create: `tools/vault_linker/report.py`
- Test: `tools/tests/test_cli.py`

**Key Decisions / Notes:**
- CLI: `python -m tools.vault_linker analyze [--vault-path .]` — report only
- CLI: `python -m tools.vault_linker fix [--vault-path .] [--dry-run]` — apply fixes
- CLI: `python -m tools.vault_linker fix [--vault-path .] --dry-run` — preview changes without writing
- Report output: `tools/vault_health_report.md` with metrics table, broken links by category, actions taken
- Report should show broken link categories separately: resolvable, external, deleted, missing concepts
- Use `argparse` for CLI

**Definition of Done:**
- [ ] `analyze` mode produces health report without modifying files
- [ ] `fix` mode applies all fixes (tags, stubs, links, broken link resolution)
- [ ] `--dry-run` flag previews changes without writing
- [ ] Report includes before/after metrics
- [ ] Exit code 0 on success, 1 on errors

**Verify:**
- `python tools/vault_linker.py analyze --vault-path . | head -20` — report generated
- `python tools/vault_linker.py fix --vault-path . --dry-run | head -20` — dry run shows planned changes

### Task 7: Run Tool and Apply Fixes to Vault

**Objective:** Execute the tool in `fix` mode against the vault, verify the results, and curate any edge cases.

**Dependencies:** Task 6

**Files:**
- Modify: Multiple vault markdown files (papers, concepts, decisions, patterns)
- Create: New concept stub files in `concepts/`
- Create: `tools/vault_health_report.md`

**Key Decisions / Notes:**
- Run `analyze` first to get baseline metrics
- Run `fix --dry-run` to preview changes
- Run `fix` to apply
- Run `analyze` again to get post-fix metrics
- **Review changes via `git diff`** in the worktree before merging back
- Manually review a sample of modified files to verify quality

**Definition of Done:**
- [ ] Baseline analysis report generated
- [ ] Fixes applied successfully (non-zero file modifications)
- [ ] Post-fix analysis shows improvement in link connectivity
- [ ] Resolvable broken link count reduced by >50% (excluding external refs and deleted files)
- [ ] Papers with `tags: null` reduced to 0
- [ ] Sample of 5+ modified files manually verified for quality
- [ ] `git diff` reviewed — no frontmatter corruption or duplicate links

**Verify:**
- `python tools/vault_linker.py analyze --vault-path .` — post-fix report shows improved metrics
- `rg 'tags: null' papers/ --glob '*.md' | wc -l` — returns 0

## Testing Strategy

- **Unit tests:** Test each component in isolation (parser, resolver, tag generator, stub generator, link injector) using small test fixtures
- **Integration test:** Run `analyze` on the actual vault and verify report accuracy
- **Manual verification:** After applying fixes, spot-check 5-10 modified files for link quality

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fuzzy matching creates incorrect link mappings | Medium | Medium | Only auto-apply matches with confidence >= 0.8; partial matches are report-only suggestions; `--dry-run` mode for preview |
| Generated tags are irrelevant or too generic | Low | Low | Use controlled tag vocabulary from existing papers; cross-reference with concept names; analyze body content not just titles |
| Concept stubs create noise in the vault | Low | Low | Only stub links with 3+ references; skip date-prefixed and external refs; clearly mark as auto-generated |
| PyYAML corrupts frontmatter on write | High | High | Use PyYAML for **reading only**; all writes use surgical regex replacement on the specific line being changed |
| `similar_papers` contains nonsensical associations | High | Medium | Require tag/keyword overlap validation before converting to wiki-links; skip pairs with zero relevance |
| Inline wiki-links get duplicated | High | Medium | Scan ALL wiki-links in entire file body before injecting; deduplicate against all existing outgoing links |
| Large number of file modifications overwhelms review | Medium | Medium | Worktree isolation + `git diff` review; `--dry-run` mode; report shows all planned changes |

## Open Questions

- None — scope and approach are clear from exploration and user decisions.

### Deferred Ideas

- Semantic similarity using Ollama embeddings for link suggestions (requires running Ollama)
- Integration with 3D graph plugin data regeneration after fixes
- Automated re-linking when new notes are added (daemon/hook)
