---
tags: [obsidian, best-practices, ai-agents, knowledge-management]
created: 2026-03-04
updated: 2026-03-04
related: [[cloud-vault-mcp]], [[tool-use]], [[knowledge-graph-systems]]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 3
  synapse_out: 16
title: "Obsidian Best Practices for AI Agents"
date: 2026-03-04
---

# Obsidian Best Practices for AI Agents

## 📖 Overview

This document synthesizes best practices for AI agents (Claude Code, OpenCode, Gemini CLI) interacting with Obsidian Vaults. Based on research from Obsidian documentation, community plugins, and real-world usage patterns.

---

## 🎯 Core Principles

### 1. **Atomic Notes**
- One idea per note
- Keep notes under 500 words (exception: daily notes, meeting notes)
- Use **descriptive filenames** (not "note1.md" but "obsidian-vault-structure.md")

### 2. **Bidirectional Linking**
- Always link to related notes: `[[Related Concept]]`
- Use **embedded links** for context: `![[Diagram.png]]`
- Create **Maps of Content (MOCs)** as hub notes

### 3. **Frontmatter Standards**
```yaml
---
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
related: [[Note1]], [[Note2]]
aliases: ["Alternative Name", "Another Alias"]
status: draft|in-progress|complete|archived
---
```

### 4. **Folder Structure**
```
vault/
├── 📁 daily/           # Daily notes (YYYY-MM-DD-note.md)
├── 📁 concepts/        # Atomic concept notes
├── 📁 projects/        # Project-specific notes
├── 📁 people/          # People/roles
├── 📁 organizations/   # Companies, teams
├── 📁 templates/       # Note templates
├── 📁 attachments/     # Images, PDFs, files
├── 📁 archives/        # Inactive notes
└── 📁 moc/             # Maps of Content (hub notes)
```

---

## 🔧 AI Agent Workflows

### Workflow 1: **Note Creation**
```markdown
1. Check for existing notes on topic (search)
2. Create new note with frontmatter
3. Link to 2-3 related existing notes
4. Add to relevant MOC
5. Tag appropriately (2-5 tags max)
```

### Workflow 2: **Knowledge Synthesis**
```markdown
1. Gather source notes
2. Extract key insights (bullet points)
3. Identify connections (link analysis)
4. Create synthesis note with:
   - Summary
   - Key insights
   - Connections to existing knowledge
   - Action items
5. Update source notes with backlinks
```

### Workflow 3: **Daily Note Ritual**
```markdown
1. Create daily note (YYYY-MM-DD.md)
2. Add date to frontmatter
3. Link to yesterday/tomorrow
4. Review yesterday's todos
5. Plan today's focus
6. Capture meeting notes, insights during day
7. End-of-day: extract永久笔记 (permanent notes)
```

---

## 📝 Query Patterns (Dataview)

### Find notes by tag:
```dataview
TABLE created, updated, status
FROM #concept
WHERE contains(tags, "obsidian")
SORT created DESC
```

### Find orphaned notes:
```dataview
TABLE file.name
FROM ""
WHERE length(file.links) = 0
  AND file.name != "index"
```

### Find notes needing updates:
```dataview
TABLE updated, file.name
FROM ""
WHERE updated < date(today) - dur(30 days)
SORT updated ASC
```

---

## 🔗 Linking Conventions

### Internal Links:
- `[[Note Name]]` - Basic link
- `[[Note Name#Heading]]` - Link to heading
- `[[Note Name|Display Text]]` - Custom display
- `![[Image.png]]` - Embed image
- `![[Note Name]]` - Embed entire note

### External Links:
- Use **descriptive anchor text**
- Prefer permalinks over dynamic URLs
- Archive important web pages (use Obsidian Web Clipper)

---

## 🏷️ Tagging Strategy

### Hierarchy vs. Flat:
**Recommended:** Flat tags with clear ontology
- ✅ `#ai-agent`, `#obsidian`, `#best-practice`
- ❌ `#ai/agent/obsidian` (too deep)

### Tag Guidelines:
- 2-5 tags per note
- Use **singular** form (`#concept` not `#concepts`)
- Avoid tagging what's already in folder name
- Create **tag MOCs** for frequently used tags

---

## 📊 Knowledge Graph Health

### Metrics to Track:
1. **Link Density**: Average links per note (target: 3-5)
2. **Orphan Rate**: % of notes with no links (target: <10%)
3. **Update Frequency**: Notes updated in last 30 days
4. **Tag Coverage**: Notes with 2+ tags

### Weekly Review:
- Merge duplicate notes
- Split notes >1000 words
- Add missing links
- Archive inactive projects
- Update MOCs

---

## 🤖 AI Agent Integration Patterns

### Pattern 1: **Context Injection**
Before answering, AI should:
1. Search vault for related notes
2. Read 3-5 most relevant notes
3. Synthesize answer with citations: `[[Note Name]]`
4. Suggest new notes to create

### Pattern 2: **Progressive Summarization**
1. Capture raw notes (meeting transcript, article highlights)
2. Create summary note with key points
3. Extract atomic concept notes
4. Link to MOCs

### Pattern 3: **Spaced Repetition**
1. Tag notes for review: `#review/weekly`, `#review/monthly`
2. Generate review queue with Dataview
3. Update notes with new insights
4. Archive obsolete notes

---

## ⚠️ Anti-Patterns to Avoid

### ❌ Don't:
- Create notes without links (orphans)
- Use vague filenames (`notes.md`, `ideas.md`)
- Over-tag (>10 tags per note)
- Create deep folder hierarchies (>3 levels)
- Duplicate content (link instead)
- Let notes grow beyond 1000 words without splitting

### ✅ Do:
- Link liberally (3-5 links minimum)
- Use descriptive, unique filenames
- Keep tags focused (2-5 per note)
- Prefer links over folders
- Extract atomic concepts from long notes
- Review and prune weekly

---

## 🛠️ Essential Plugins for AI Agents

### Core:
- **Dataview** - Query vault as database
- **Templates** - Note templates
- **Daily Notes** - Automatic daily note creation
- **Backlinks** - See what links to current note
- **Outline** - Navigate headings

### Enhanced:
- **Obsidian Git** - Version control integration
- **Smart Connections** - AI-powered link suggestions
- **Note Refactor** - Extract selections to new notes
- **Waypoint** - MOC auto-generation
- **Calendar** - Visual calendar for daily notes

### AI-Specific:
- **Smart Typings** - Autocomplete for links/tags
- **Various AI plugins** (Copilot, Smart AI, etc.)

---

## 📈 Maturity Levels

### Level 1: **Collector** (Weeks 1-4)
- Creating notes consistently
- Building initial tag vocabulary
- Learning linking basics
- Goal: 100 notes

### Level 2: **Connector** (Months 2-3)
- Linking notes regularly
- Creating MOCs
- Pruning duplicates
- Goal: <20% orphan rate

### Level 3: **Synthesizer** (Months 4-6)
- Progressive summarization workflow
- Regular review/prune cycle
- Knowledge graph health monitoring
- Goal: 3-5 links per note average

### Level 4: **Knowledge Worker** (6+ months)
- Spaced repetition integration
- Automated workflows
- AI-assisted synthesis
- Goal: Living knowledge organism

---

## 🔍 Search Strategies

### Basic Search:
```
#tag
path:folder
"exact phrase"
```

### Advanced Search:
```
tag:#ai-agent -#deprecated
file:(modified > today - 30 days)
line:(error OR failure)
```

### Saved Searches (as notes):
Create notes in `/moc/search-queries.md` with common patterns

---

## 📚 Additional Resources

- [[concept-modularity]] - Atomic note structure patterns
- [[context-management]] - Context injection strategies for AI agents
- [[workflow-orchestration]] - Automated workflow patterns

---

**Status:** ✅ Complete
**Review Date:** 2026-04-04 (monthly)
**Owner:** AI Agent Collective

---

## 🤖 **Autonomous Context Hooks (NEW 2026-03-04)**

### Pre-Operation Hooks (Load Context Automatically)

**For Claude Code:**
```bash
# Hook automatically loads before every prompt
~/.claude/hooks/vault-context-pre.py

# Configuration
{
  "enabled": true,
  "vault_path": "/home/mike-anderson/vaults/cohezion-vault",
  "context_limit": 10,
  "default_tags": ["#anthropic-portfolio"]
}
```

**For OpenCode:**
```bash
# Shell hook
~/.opencode/hooks/vault-context.sh

# Configuration in ~/.opencode/vault-context.json
```

**For Gemini CLI:**
```bash
# Python hook
~/.gemini/hooks/vault-context.py
```

### Post-Operation Hooks (Save Results Automatically)

**How It Works:**
1. AI completes response
2. Post-hook intercepts output
3. Saves to `~/vaults/cohezion-vault/daily/YYYY-MM-DD.md`
4. Auto-extracts permanent notes from ## headings
5. Creates backlinks to source notes
6. Logs session metrics

**Example Daily Note Auto-Update:**
```markdown
## AI Sessions
- **Session:** claude-12345
- **Type:** portfolio-planning
- **Duration:** 125.3s
- **Context:** 8 notes loaded
- **Output:** 3 permanent notes created
```

### Installation (Quick Start)

```bash
# Claude Code
cp .claude/hooks/vault-context-*.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.py
cat > ~/.claude/vault-context.json << 'JSON'
{
  "enabled": true,
  "vault_path": "$HOME/vaults/cohezion-vault",
  "auto_save": true
}
JSON

# OpenCode
cp .opencode/hooks/*.sh ~/.opencode/hooks/
chmod +x ~/.opencode/hooks/*.sh

# Gemini CLI
cp .gemini/hooks/*.py ~/.gemini/hooks/
chmod +x ~/.gemini/hooks/*.py

# Test
python src/cohezion/hooks/vault_context_loader.py pre \
  --session-id test-123 \
  --query "anthropic portfolio"
```

### Context Loader Commands

```bash
# Manual context load
python vault_context_loader.py pre \
  --session-id my-session \
  --query "knowledge graph" \
  --limit 10

# Save results
python vault_context_loader.py post \
  --session-id my-session \
  --input output.md \
  --operation research

# List active sessions
python vault_context_loader.py list-sessions
```

### Cross-Platform Configuration

**Unified config in each AI's directory:**
- `~/.claude/vault-context.json`
- `~/.opencode/vault-context.json`
- `~/.gemini/vault-context.json`

**Key settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | true | Enable/disable hooks |
| `vault_path` | auto | Path to Obsidian vault |
| `auto_load` | true | Load context before prompt |
| `auto_save` | true | Save results after response |
| `context_limit` | 10 | Max notes to load |
| `default_tags` | [] | Filter by tags |

---

**Related:** [[Autonomous-Context-Hooks-Guide]], [[agentic-ai]], [[agent-architecture]]
- [[2026-02-11-vault-first-knowledge-architecture|Vault-First Knowledge Architecture]] — the architectural decision that established the vault-first approach these best practices serve
