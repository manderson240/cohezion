---
name: vault-keeper
description: Autonomous vault maintenance agent — audits, heals, connects, and serves the knowledge graph so every agent session starts informed
triggers:
  - user says "vault keeper", "maintain vault", "vault maintenance", "keeper"
  - user invokes /vault-keeper command
  - proactive: session start (quick health check)
  - proactive: hook alert (vault-keeper-check.sh detects issues)
  - proactive: after bulk Write/Edit operations on vault .md files
---

# Vault Keeper

Autonomous maintenance agent that keeps the Obsidian vault healthy, dense, navigable, and agent-readable. Orchestrates the five specialist skills (vault-health, link, flesh-out, triage, note) in a single prioritized workflow.

**This skill is PROACTIVE.** It does not wait to be invoked — it monitors vault health continuously and acts when issues are detected.

## Usage

```
/vault-keeper                    # Full maintenance cycle (audit → heal → report)
/vault-keeper --quick            # Quick health check only (read-only, 30 seconds)
/vault-keeper --triage           # Process inbox only
/vault-keeper --densify          # Link + flesh-out cycle only
/vault-keeper --moc              # Generate/update Maps of Content
/vault-keeper --context "query"  # Load relevant vault context for a task
```

---

## Proactive Behavior

The Vault Keeper monitors vault health automatically and acts without waiting for explicit user invocation. This is the **default behavior** — the keeper is always watching.

### Trigger: Session Start

At the **start of every session** in the cohezion-vault:

**Step 1: Load orientation.** Read `VAULT_MANIFEST.md` at the vault root. This tells you:
- Where every directory is and what it's for
- Output routing rules (where to put your work)
- Conventions (frontmatter, linking, naming)
- Entry points (which MOC to start with)

**Step 2: Run silent health check:**

```bash
# 1. Check inbox
inbox_count=$(find thalamus/ -maxdepth 1 -name '*.md' ! -name '_index.md' ! -name '_template.md' 2>/dev/null | wc -l)

# 2. Check for orphans in core dirs (sample — full scan only on explicit run)
orphan_sample=$(for f in cortex/*.md; do
  [ -f "$f" ] || continue
  name="${f##*/}"; name="${name%.md}"
  [ "$name" = "_template" ] && continue
  count=$(grep -rl "\[\[.*$name" cortex/ sensory/ prefrontal/ motor/ 2>/dev/null | grep -v "$f" | wc -l)
  [ "$count" -eq 0 ] && echo "$f"
done | head -5)

# 3. Count thin notes (quick sample)
thin_count=$(find cortex/ sensory/ prefrontal/ -name '*.md' ! -name '_template.md' -size -3k 2>/dev/null | wc -l)
```

**Step 3: Load task-relevant context.** If the user's first message implies a topic:
- Find the matching MOC (`cortex/MOC-*.md`) and skim it
- Check `memory/` for past mistakes in that domain
- Check the relevant directory's `_index.md` for key notes

**Actions based on health check findings:**

| Finding | Action | User Interaction |
|---------|--------|------------------|
| Inbox has items | Report to user: "Inbox has N items. Want me to triage them?" | Ask once |
| Active project P0s | Surface them immediately: list the file and unchecked items | Proactive |
| Orphans detected | Auto-fix silently if < 5, report if >= 5 | Silent for small counts |
| Thin notes > 20 | Mention in first response: "N thin notes could use expansion" | Informational |
| All healthy | Say nothing — don't clutter with "all clear" messages | Silent |

**Step 2b: Scan active projects for P0 work:**

```bash
# Find active projects with unchecked P0 items
for f in motor/*.md; do
  grep -q '^status: active' "$f" 2>/dev/null || continue
  awk '/^### P0/{p=1} p && /^###/ && !/^### P0/{p=0} p && /^\- \[ \]/{print FILENAME": "$0}' "$f"
done
```

If any P0 items are found, surface them in the first response: "There are P0 tasks due in `<project>`. Want me to start on them?"

### Agent Orientation Files

Every content and workflow directory has a `_index.md` file. Agents can read any directory's `_index.md` to understand:
- What goes in that directory
- Naming and frontmatter conventions
- Key notes to reference
- Related MOCs for deeper context

**Discovery pattern for any unfamiliar directory:**
```
Read <directory>/_index.md → understand purpose → follow routing rules
```

### Trigger: Hook Alert

The `vault-keeper-check.sh` PostToolUse hook runs after Write/Edit operations on `.md` files. When it detects issues, it prints an alert message. **When you see a vault-keeper alert in hook output, act on it:**

| Alert | Auto-Action |
|-------|-------------|
| `VAULT_KEEPER: inbox has N new items` | Offer to triage |
| `VAULT_KEEPER: new note has no inbound links` | Add 1-3 inbound wiki-links from relevant hub notes immediately |
| `VAULT_KEEPER: note missing frontmatter` | Add proper frontmatter to the note immediately |
| `VAULT_KEEPER: note has tags as string` | Convert tags to array immediately |

**Key rule:** For structural fixes (frontmatter, tags, missing links on new notes), fix immediately without asking. These are vault invariants, not preferences.

### Trigger: Bulk Operations

After any operation that creates or modifies 5+ vault notes (e.g., flesh-out runs, research imports, link campaigns):

1. Run a quick orphan check on affected files
2. Verify all new/modified notes have proper frontmatter
3. Confirm no broken links were introduced
4. Report metrics delta (links before → after)

### Trigger: User Context Clues

Proactively invoke vault keeper logic when the user's request implies vault maintenance, even without saying "vault keeper":

| User Says | Vault Keeper Interprets As |
|-----------|---------------------------|
| "Clean up the vault" | Full maintenance run |
| "What's in the inbox?" | Triage mode |
| "How healthy is the vault?" | Quick audit |
| "Connect these notes" | Link mode |
| "This note is thin" | Flesh-out mode |
| "Make this navigable" | MOC generation |
| "Update the maps" | MOC refresh |

### Proactive Rules

1. **Never announce proactive work unnecessarily.** If you silently fix 2 orphans, don't write a paragraph about it. A one-liner in your response is enough: "Also connected 2 orphan notes."
2. **Always fix invariant violations immediately.** Missing frontmatter, string tags, and orphaned new notes are bugs, not preferences.
3. **Respect context budget.** Proactive checks should cost < 500 tokens. If a full audit is needed, ask the user first.
4. **Don't repeat checks.** If you already ran a health check this session, don't run another unless new notes were created.
5. **Batch alerts.** If multiple issues are found, combine them into one report rather than alerting per-issue.

---

## Architecture

The Vault Keeper runs a **prioritized maintenance pipeline**. Each phase gates the next — critical issues are fixed before cosmetic ones.

```
Phase 1: TRIAGE     → Process inbox (new content enters the graph properly)
Phase 2: AUDIT      → Health check (identify what's broken)
Phase 3: HEAL       → Fix issues found by audit (frontmatter, broken links, orphans)
Phase 4: DENSIFY    → Expand thin notes, add missing connections
Phase 5: NAVIGATE   → Generate/update Maps of Content for traversability
Phase 6: REPORT     → Summary with metrics and deltas
```

---

## Phase 1: TRIAGE — Process Inbox

**Goal:** Zero inbox. New content enters the vault through proper channels.

```bash
ls thalamus/*.md 2>/dev/null | grep -v '.base$'
```

If inbox has notes:
1. Invoke the **triage** skill logic for each note
2. Classify → research → structure → frontmatter → move → cross-link
3. Log what was triaged in the report

If inbox is empty, skip to Phase 2.

---

## Phase 2: AUDIT — Health Check

**Goal:** Identify all vault issues in a single pass.

Run these checks (parallel where possible):

### 2.1 Broken Wiki-Links
```bash
grep -roh '\[\[[^]]*\]\]' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ 2>/dev/null \
  | sed 's/\[\[//;s/\]\]//' | sed 's/|.*//' | sed 's/#.*//' | grep -v '^$' | sort -u | while read link; do
  # Check top-level directory files
  found=0
  for d in cortex sensory prefrontal cerebellum laboratory motor memory thalamus hippocampus Agents genome missions retrospectives teleport docs meta benchmarks research dreaming songlines; do
    [ -f "$d/$link.md" ] && found=1 && break
  done
  # Check subdirectories (Obsidian resolves bare names across subdirs)
  if [ $found -eq 0 ]; then
    match=$(find cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ thalamus/ hippocampus/ Agents/ genome/ missions/ retrospectives/ dreaming/ songlines/ subconscious/ metabolism/ visual-cortex/ benchmarks/ research/ -name "$link.md" -maxdepth 4 2>/dev/null | head -1)
    [ -n "$match" ] && found=1
  fi
  [ $found -eq 0 ] && echo "$link"
done
```

### 2.2 Orphan Notes (No Inbound Links)
```bash
for dir in cortex sensory prefrontal cerebellum laboratory motor memory; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    name="${f##*/}"; name="${name%.md}"
    [ "$name" = "_template" ] && continue
    count=$(grep -rl "\[\[.*$name" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ Agents/ genome/ hippocampus/ missions/ retrospectives/ memory/ 2>/dev/null | grep -v "$f" | wc -l)
    [ "$count" -eq 0 ] && echo "ORPHAN: $f"
  done
done
```

### 2.3 Frontmatter Issues
```bash
for dir in cortex sensory prefrontal cerebellum laboratory motor memory; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    head -1 "$f" | grep -q '^---' || echo "NO_FRONTMATTER: $f"
  done
done

# Tags as string instead of array
grep -rl '^tags:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ 2>/dev/null | while read f; do
  grep '^tags:' "$f" | grep -qv '\[' && echo "TAGS_NOT_ARRAY: $f"
done

# Missing aspect field
grep -rL '^aspect:' cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ 2>/dev/null \
  | grep -v '_template.md' | while read f; do echo "NO_ASPECT: $f"; done
```

### 2.4 Thin Notes (Under 3KB)
```bash
for dir in cortex sensory prefrontal cerebellum laboratory memory; do
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    b="${f##*/}"; [ "$b" = "_template.md" ] && continue
    sz=$(wc -c < "$f")
    [ "$sz" -lt 3000 ] && echo "THIN: $sz $f"
  done
done
```

### 2.5 Under-Connected Hubs (High Inbound, Low Outbound)
```bash
for f in cortex/*.md; do
  b="${f##*/}"; n="${b%.md}"; [ "$n" = "_template" ] && continue
  outbound=$(grep -oh '\[\[[^]]*\]\]' "$f" 2>/dev/null | wc -l)
  inbound=$(grep -rl "\[\[.*$n" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ 2>/dev/null | grep -v "$f" | wc -l)
  if [ "$inbound" -gt 15 ] && [ "$outbound" -lt 5 ]; then
    echo "UNDER-CONNECTED: $f (in:$inbound, out:$outbound)"
  fi
done
```

### 2.6 Missing Maps of Content
```bash
ls cortex/MOC-*.md 2>/dev/null | wc -l
# Target: at least 5 MOCs covering major topic clusters
```

Classify issues by severity:

| Severity | Issues |
|----------|--------|
| **CRITICAL** | Broken links in core concepts, orphan concepts, missing frontmatter |
| **HIGH** | Orphan sensory/prefrontal/patterns, tags not arrays, under-connected hubs |
| **MEDIUM** | Thin notes (<3KB), missing MOCs |
| **LOW** | Thin lessons, cosmetic link improvements |

---

## Phase 3: HEAL — Fix Issues

**Goal:** Resolve all CRITICAL and HIGH issues automatically.

### 3.1 Fix Frontmatter
For each `NO_FRONTMATTER` or `TAGS_NOT_ARRAY` issue:
- Read the file
- Add/fix frontmatter with proper YAML (tags as arrays, title, date)
- Preserve all existing content

### 3.2 Fix Orphans
For each orphan note:
- Read the file to understand its topic
- Find 1-3 relevant hub notes
- Add inbound `[[wiki-links]]` from hub notes to the orphan

### 3.3 Fix Broken Links
For each broken link:
- Classify: is it a real missing note, a typo, or a code/template reference?
- Real missing note with 3+ references → create a stub concept note
- Typo → fix the link
- Code/template → ignore (non-actionable)

### 3.4 Fix Under-Connected Hubs
For each hub with high inbound but low outbound:
- Read the note
- Add 5-10 relevant outbound `[[wiki-links]]` to related notes

---

## Phase 4: DENSIFY — Expand and Connect

**Goal:** Increase content depth and graph density.

### 4.1 Flesh Out Thin Notes
Prioritize by inbound link count (highest-impact first):
1. Read the thin note
2. Research the topic (WebSearch for authoritative info)
3. Expand with: definition, key properties, examples, primary sources
4. Add outbound `[[wiki-links]]` (3-5 per note)
5. Add "Relevance to Cohezion" section if missing

**Budget:** Expand up to 15 notes per run (quality over quantity).

### 4.2 Add Missing Cross-Links
Run the **link** skill logic:
- Tag-based: notes sharing 2+ tags that don't link to each other
- Content-based: notes mentioning concepts that exist as vault notes
- Semantic proximity: notes in the same domain that should cross-reference

**Budget:** Add up to 50 bidirectional link pairs per run.

---

## Phase 5: NAVIGATE — Maps of Content

**Goal:** Make the vault traversable via curated entry points.

### 5.1 Identify Topic Clusters

Group notes by primary tag or domain:
```bash
# Find most common tags
grep -roh "tags: \[.*\]" cortex/ sensory/ prefrontal/ cerebellum/ laboratory/ motor/ memory/ 2>/dev/null \
  | sed 's/tags: \[//;s/\]//' | tr ',' '\n' | sed 's/^ *//;s/ *$//' | sort | uniq -c | sort -rn | head -20
```

### 5.2 Generate/Update MOCs

For each major topic cluster (5+ notes), create or update a Map of Content:

```markdown
---
title: "MOC — [Topic Name]"
date: 2026-03-04
tags: [moc, navigation, [topic-tag]]
---

# Map of Content — [Topic Name]

## Overview
[1-2 sentences describing this topic area and its role in the vault]

## Core Concepts
- [[concept-1]] — [brief annotation from first sentence of note]
- [[concept-2]] — [annotation]

## Key Decisions
- [[decision-1]] — [annotation]

## Patterns
- [[pattern-1]] — [annotation]

## Research Papers
- [[paper-1]] — [annotation]

## Lessons Learned
- [[lesson-1]] — [annotation]

## Experiments
- [[experiment-1]] — [annotation]

## Entry Points
- Start here: [[most-linked-concept]]
- Deep dive: [[most-detailed-note]]
- Recent: [[most-recently-modified]]
```

**Target MOCs** (minimum set):
1. `MOC-agentic-ai.md` — Agent architecture, multi-agent systems, orchestration
2. `MOC-quantum-physics.md` — Quantum mechanics, computing, sensors, entanglement
3. `MOC-vault-architecture.md` — Knowledge graph, linking, vault health, conventions
4. `MOC-platform-infrastructure.md` — MCP, SurrealDB, Ollama, CI/CD, runbooks
5. `MOC-machine-learning.md` — ML, neural nets, training, optimization
6. `MOC-astrophysics.md` — Space, JWST, dark matter, exoplanets, gravitational waves
7. `MOC-compound-engineering.md` — Compound methodology, sessions, retrospectives
8. `MOC-safety-alignment.md` — AI safety, adversarial review, alignment, guardrails

### 5.3 Link MOCs to Each Other
Each MOC should link to 2-3 related MOCs in a "## Related Maps" section, creating a navigable top-level layer.

---

## Phase 6: REPORT — Summary

Generate a structured report:

```markdown
## Vault Keeper Report — YYYY-MM-DD

### Metrics
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total notes | X | Y | +Z |
| Wiki-links | X | Y | +Z |
| Orphan notes | X | Y | -Z |
| Broken links | X | Y | -Z |
| Frontmatter issues | X | Y | -Z |
| Thin notes (<3KB) | X | Y | -Z |
| Maps of Content | X | Y | +Z |
| Inbox items | X | Y | -Z |

### Actions Taken
- **Triaged:** X inbox notes processed
- **Healed:** X frontmatter fixes, Y orphans connected, Z broken links resolved
- **Densified:** X notes expanded, Y new cross-links added
- **Navigation:** X MOCs created/updated

### Remaining Issues
| Priority | Issue | Count |
|----------|-------|-------|
| MEDIUM | Thin notes | X |
| LOW | Cosmetic links | Y |

### Recommendations
1. [Top priority for next run]
2. [Second priority]
3. [Third priority]
```

---

## Quick Mode (`--quick`)

Skip Phases 1, 3, 4, 5. Only run Phase 2 (audit) and Phase 6 (report). Read-only — no modifications.

Useful for: daily check-ins, pre-session health verification, CI/CD integration.

## Context Mode (`--context "query"`)

Load relevant vault knowledge for a specific task:

1. Search vault for notes matching the query (by title, tags, content)
2. Load the most relevant MOC as a navigation entry point
3. Return top 5-10 notes with brief summaries
4. Include any relevant lessons (filtered by topic)

Output format:
```markdown
## Vault Context for: "[query]"

### Map of Content
→ [[MOC-relevant-topic]]

### Most Relevant Notes
1. [[note-1]] — [first sentence summary]
2. [[note-2]] — [summary]
...

### Applicable Lessons
- [[lesson-XX]] (severity: HIGH) — [title]
- [[lesson-YY]] (severity: MEDIUM) — [title]

### Related Decisions
- [[decision-1]] — [status: accepted]
```

This is the output that context hooks should inject at session startup.

---

## Neural Intelligence (Pre-Computed Graph Alerts)

The vault_sync daemon's **GraphReactor** continuously queries SurrealDB and writes
pre-computed intelligence to `metabolism/graph-alerts.md`. This is the **primary**
source of graph intelligence — read this file instead of making SurrealDB queries.

### At Session Start: Read Graph Alerts

```bash
cat metabolism/graph-alerts.md
```

This file contains:
- **Dark Countries** (health < 0.3) — directories needing content expansion
- **Low Countries** (0.3-0.5) — at-risk areas to monitor
- **Orphan Neurons** — high-activation notes with 0 inbound synapses
- **Resting Notes** — candidates for renewal or composting
- **Synapse Gaps** — note pairs sharing tags but no links (cross-link targets)
- **HIHO Fusion Events** — recent coherence breakthroughs

**Actions based on alerts:**

| Alert | Action |
|-------|--------|
| Dark Country | Flesh out notes in that directory, add cross-links |
| Orphan Neuron (cortex/) | Add inbound links from relevant hub notes |
| Synapse Gap | Add [[wiki-link]] between the two notes |
| HIHO Fusion | Check `dreaming/` for today's resonances |

### Fallback: Direct SurrealDB Queries

Only use these if the graph-alerts file is stale (>24h old) or missing:

```bash
# Regenerate alerts manually
python3 scripts/vault_sync.py --react

# Or query SurrealDB directly (higher token cost)
curl -s -u root:root -X POST "http://localhost:8001/sql" \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -H "Content-Type: text/plain" \
  --data-raw 'SELECT name, health, neuron_count FROM country ORDER BY health ASC LIMIT 5;'
```

### Dreaming Engine Invocation

Run `python3 scripts/dreaming-engine.py` to:
- Refresh Country health
- Find today's cross-domain resonances → `dreaming/YYYY-MM-DD-resonances.md`
- Update `metabolism/metabolism-dashboard.md`
- Log HIHO fusion events

Run after any bulk operation that adds 10+ notes.

### Daemon Mode

Start the sync daemon for continuous graph intelligence:

```bash
python3 scripts/vault_sync.py --watch &
```

This provides:
- Phase 1: Real-time vault→SurrealDB sync via inotify (<1s latency)
- Phase 2: Graph reactor updates `metabolism/graph-alerts.md` every 60s after changes

---

## Scheduling

### Automated (Cron — runs unattended)

| Schedule | Command | Purpose |
|----------|---------|---------|
| Every 6h (0,6,12,18) | `dreaming-cron.sh --quick` | Engines 1-4: country health, resonances, HIHO fusion, metabolism dashboard |
| Daily 2:30 AM | `dreaming-cron.sh` | Full run: all 7 engines including kinship, songlines, subconscious |

The cron wrapper (`scripts/dreaming-cron.sh`) checks SurrealDB health before running,
uses a lockfile to prevent overlapping runs, and logs to `logs/dreaming-engine.log`.

### On-Demand (Agent-driven)

| Frequency | Mode | Purpose |
|-----------|------|---------|
| Every session start | Read `metabolism/graph-alerts.md` | Pre-computed graph intelligence (zero query cost) |
| Every session start | `--context` | Load relevant knowledge |
| After bulk imports | Full vault-keeper run | Integration and linking |
| After `/flesh-out` or `/link` runs | `--quick` | Verify improvements |

### Real-Time (Daemon — Phase 1+2)

The `vault_sync.py --watch` daemon runs continuously and provides:
- **Phase 1**: inotify-based vault-to-SurrealDB sync (<1s latency)
- **Phase 2**: GraphReactor updates `metabolism/graph-alerts.md` every 60s after changes

## Agent Deployment Strategy

For full maintenance runs, deploy specialist agents in parallel:

```
Agent 1: Triage (inbox processing)
Agent 2: Audit + Heal (health check and fixes)
Agent 3: Densify (flesh-out thin notes)
Agent 4: Densify (cross-linking)
Agent 5: Navigate (MOC generation)
```

This matches the proven pattern from vault densification sessions — 5 parallel agents with non-overlapping file scopes.

## Integration Points

### Claude Code Hooks
- **PreToolUse hook**: Run `--context` to load relevant vault knowledge before agent responds
- **PostToolUse hook**: Save session results back to vault (daily notes, new concepts)

### Cloud Vault MCP (port 8360)
- Use VaultOps for programmatic search
- Use ObsidianOps for frontmatter updates
- Use SurrealDB for graph queries

### Obsidian Graph View
- MOCs appear as high-connectivity hubs in the graph
- Color-code by directory type for visual navigation

## Quality Standards

**A healthy vault has:**
- 0 orphan notes in core directories
- 0 frontmatter issues
- 0 actionable broken links
- < 10% thin notes (<3KB) in any directory
- At least 5 Maps of Content
- Average 6+ wiki-links per note
- Every new note connected within 24 hours of creation

**The Vault Keeper's job is to maintain these invariants continuously.**
