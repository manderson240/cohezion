---
tags: [obsidian, hooks, ai-agents, context-awareness, automation]
created: 2026-03-04
updated: 2026-03-04
related: [[Obsidian-Best-Practices-for-AI-Agents]], [[context-management]], [[agentic-ai]]
aliases: ["AI Context Hooks", "Vault Auto-Sync", "Claude Code Obsidian Integration"]
status: complete
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 7
  synapse_out: 21
title: "Autonomous Context Hooks for AI Agents"
date: 2026-03-04
---

# Autonomous Context Hooks for AI Agents

## 🎯 Overview

Autonomous context hooks automatically **load relevant Obsidian vault knowledge** before AI agents (Claude Code, OpenCode, Gemini CLI) respond, and **save conversation results** back to the vault after completion.

**Result:** AI agents operate with full knowledge graph awareness and continuously enrich the vault.

---

## 🏗️ Architecture

### Two-Phase Hook System:

#### Phase 1: Pre-Operation (Load Context)
```
User Prompt → Hook Intercepts → Extract Query → Search Vault
→ Load 5-10 Relevant Notes → Inject Context → AI Responds
```

**Example Context Injection:**
```markdown
[User's Original Prompt]

---
📚 **Obsidian Vault Context** (Auto-loaded)

## Anthropic-Portfolio-Plan
**Tags:** #anthropic, #portfolio
**Related:** [[12D-Manifold]], [[FLUME-Architecture]]

Our portfolio strategy has 3 phases...

## 12D-Manifold-Demo
**Tags:** #demo, #manifold
**Related:** [[FLUME-Architecture]], [[Ouroboros-Loop]]

The 12D projection uses VAE compression...

---
**Instructions:** Reference context with [[Note Name]], link new concepts
```

#### Phase 2: Post-Operation (Save Results)
```
AI Response → Hook Intercepts → Save to Session Cache
→ Extract Permanent Notes → Update Daily Note → Create Backlinks
```

**Example Daily Note Update:**
```markdown
## AI Sessions

### Session: claude-12345
- **Time:** 2026-03-04 10:30-10:32
- **Type:** Portfolio planning
- **Duration:** 125.3 seconds
- **Context loaded:** 8 notes
- **Permanent notes created:** 3
- **Files:** [[Portfolio-Synthesis]], [[Demo-Timeline]], [[Asset-List]]
```

---

## 📦 Installation

### Step 1: Copy Hook Files

```bash
# Claude Code
cp /home/mike-anderson/dev/cohezion/.claude/hooks/vault-context-*.py \
   ~/.claude/hooks/

# OpenCode
cp /home/mike-anderson/dev/cohezion/.opencode/hooks/*.sh \
   ~/.opencode/hooks/

# Gemini CLI
cp /home/mike-anderson/dev/cohezion/.gemini/hooks/*.py \
   ~/.gemini/hooks/

# Make executable
chmod +x ~/.claude/hooks/*.py \
         ~/.opencode/hooks/*.sh \
         ~/.gemini/hooks/*.py
```

### Step 2: Create Configuration

**Claude Code:** `~/.claude/vault-context.json`
```json
{
  "enabled": true,
  "vault_path": "/home/mike-anderson/vaults/cohezion-vault",
  "auto_load": true,
  "auto_save": true,
  "context_limit": 10,
  "default_tags": ["#anthropic-portfolio"]
}
```

**OpenCode:** `~/.opencode/vault-context.json`
```json
{
  "enabled": true,
  "vault_path": "$HOME/vaults/cohezion-vault",
  "auto_save": true
}
```

**Gemini CLI:** `~/.gemini/vault-context.json`
```json
{
  "enabled": true,
  "vault_path": "$HOME/vaults/cohezion-vault"
}
```

### Step 3: Test Context Loader

```bash
# Test manual load
python /home/mike-anderson/dev/cohezion/src/cohezion/hooks/vault_context_loader.py \
  pre \
  --session-id test-123 \
  --query "anthropic portfolio" \
  --limit 5

# Expected output: Markdown-formatted context from 5 relevant notes
```

---

## 🔧 Configuration Options

### Core Settings:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable all hooks |
| `vault_path` | string | auto-detect | Absolute path to Obsidian vault |
| `auto_load` | boolean | `true` | Load context before every prompt |
| `auto_save` | boolean | `true` | Save results after every response |
| `context_limit` | integer | `10` | Maximum notes to load |
| `default_tags` | array | `[]` | Filter notes by tags |

### Advanced Settings:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `extract_permanent_notes` | boolean | `true` | Auto-create notes from ## headings |
| `update_daily_note` | boolean | `true` | Append session summary to daily |
| `create_backlinks` | boolean | `true` | Link new notes to source context |
| `min_section_length` | integer | `100` | Minimum words to extract section |
| `context_cache_dir` | string | `/tmp/cohezion-context-cache` | Session cache location |

---

## 📊 Usage Examples

### Example 1: Automatic Portfolio Planning

**User:** "What's our Anthropic portfolio timeline?"

**Automatic Flow:**
1. Pre-hook loads: [[cohezion]], [[agent-architecture]], [[tool-use]]
2. Claude responds with full context
3. Post-hook saves:
   - Full conversation to cache
   - Extracts "Timeline" section as permanent note
   - Updates daily note with summary
   - Creates backlinks to all 3 source notes

**Result:** Vault enriched with new timeline knowledge, linked to existing portfolio notes.

---

### Example 2: Multi-Turn Session Continuity

**Turn 1:**
- User: "Explain FLUME architecture"
- Context loads: [[transformer-architecture]], [[neural-network-architecture]], [[semantic-search]]
- Claude explains
- Saves to session `claude-12345`

**Turn 2:**
- User: "How does it connect to Ouroboros?"
- Same session continues, adds Ouroboros context
- Claude connects concepts
- Saves both to same session cache

**Turn 3:**
- User: "Create synthesis note"
- Post-hook creates: `FLUME-Ouroboros-Integration.md`
- Links to all source notes from both turns

---

### Example 3: Project-Specific Isolation

**Switch contexts via tags:**

```bash
# Anthropic work
export VAULT_DEFAULT_TAGS='["#anthropic-portfolio"]'
# Loads only Anthropic-related notes

# FLUME development
export VAULT_DEFAULT_TAGS='["#flume", "#vae"]'
# Loads only FLUME/VAE notes

# Reset to all
unset VAULT_DEFAULT_TAGS
# Loads from all projects
```

---

## 🔍 Debugging & Monitoring

### Check Active Sessions:
```bash
python vault_context_loader.py list-sessions

# Output:
Active sessions (3):
  - claude-12345: 8 notes, started 2026-03-04T10:30:00
  - opencode-67890: 5 notes, started 2026-03-04T11:15:00
  - gemini-54321: 12 notes, started 2026-03-04T11:45:00
```

### View Session Details:
```bash
cat /tmp/cohezion-context-cache/claude-12345.json | jq

# Output:
{
  "session_id": "claude-12345",
  "start_time": "2026-03-04T10:30:00",
  "end_time": "2026-03-04T10:32:05",
  "duration_seconds": 125.3,
  "notes_loaded": 8,
  "notes_created": 3,
  "operation_type": "portfolio-planning"
}
```

### Manual Context Load Test:
```bash
python vault_context_loader.py pre \
  --session-id manual-test \
  --query "12D manifold projection" \
  --tags "#concept,#physics" \
  --limit 5 \
  --format json
```

### Enable Verbose Logging:
```bash
export VAULT_CONTEXT_DEBUG=1
export VAULT_CONTEXT_LOG_FILE=~/.local/share/cohezion/vault-context.log

# Then run AI agent
claude

# Check logs
tail -f ~/.local/share/cohezion/vault-context.log
```

---

## ⚠️ Troubleshooting

### Problem: Context Not Loading

**Checklist:**
1. ✅ Hook enabled in config? `"enabled": true`
2. ✅ Hook file executable? `chmod +x ~/.claude/hooks/*.py`
3. ✅ Vault path exists? `ls ~/vaults/cohezion-vault`
4. ✅ Obsidian helpers installed? `python -c "from skills.obsidian_helpers import ObsidianVault"`
5. ✅ Logs show errors? `tail ~/.local/share/cohezion/vault-context.log`

**Solution:** Most often permissions or wrong vault path.

---

### Problem: Notes Not Saving

**Checklist:**
1. ✅ `auto_save` enabled? `"auto_save": true`
2. ✅ Output is valid markdown? No binary content
3. ✅ Vault writable? `touch ~/vaults/cohezion-vault/test.md`
4. ✅ Session ID matches pre/post? Same `<agent>-<pid>` format

**Solution:** Check session ID consistency between pre and post hooks.

---

### Problem: Wrong Notes Loading

**Symptoms:** Irrelevant context loaded.

**Fixes:**
1. Narrow query (use more specific terms)
2. Add tag filters in config
3. Reduce `context_limit` (try 5 instead of 10)
4. Check note frontmatter tags match query

---

## 📈 Metrics & Optimization

### Performance Targets:

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Context load time | <500ms | 500-1000ms | >1000ms |
| Notes loaded | 5-10 | <3 or >15 | <2 or >20 |
| Context relevance | >80% | 50-80% | <50% |
| Notes created/session | 1-3 | 0 or >5 | 0 for 10+ sessions |

### Daily Report:
```bash
# Generate report
python vault_context_loader.py report --date $(date +%Y-%m-%d)

# Example output:
## Vault Context Report: 2026-03-04
- Total sessions: 15
- Avg load time: 342ms ✅
- Avg notes loaded: 7.2 ✅
- Permanent notes created: 23
- Most used tags: #anthropic-portfolio (12), #flume (8)
- Top queries: "portfolio timeline", "FLUME architecture", "demo script"
```

---

## 🔗 Integration Patterns

### Pattern 1: **Daily Standup Automation**
```bash
# Morning ritual script
#!/bin/bash
echo "Loading today's context..."
python vault_context_loader.py pre \
  --session-id "morning-$(date +%H%M)" \
  --project "anthropic-portfolio" \
  --tags "#daily,#todo"

# After standup, save notes
python vault_context_loader.py post \
  --session-id "morning-$(date +%H%M)" \
  --input standup-notes.md \
  --operation "daily-standup"
```

### Pattern 2: **Research Synthesis**
```bash
# Multi-session research
for topic in "FLUME" "Ouroboros" "Topology"; do
  python vault_context_loader.py pre \
    --session-id "research-$topic" \
    --query "$topic architecture" \
    --tags "#research"
  # ... AI conversation ...
  python vault_context_loader.py post \
    --session-id "research-$topic" \
    --input "$topic-synthesis.md"
done

# Create master synthesis
cat research-*-synthesis.md > master-synthesis.md
```

### Pattern 3: **Code Review Context**
```bash
# Before code review
python vault_context_loader.py pre \
  --session-id "review-$(git rev-parse --short HEAD)" \
  --query "$(git diff --stat HEAD~1)" \
  --tags "#code-review,#anthropic-portfolio"

# After review (save feedback)
python vault_context_loader.py post \
  --session-id "review-$(git rev-parse --short HEAD)" \
  --input review-feedback.md \
  --operation "code-review"
```

---

## 🚀 Advanced Customization

### Custom Hook Logic:
```python
# Extend vault_context_loader.py

class CustomContextLoader(SessionContext):
    def load_context(self, query, tags=None, limit=10):
        # Add custom filtering logic
        notes = super().load_context(query, tags, limit)
        
        # Boost recently updated notes
        notes.sort(key=lambda n: n.stat().st_mtime, reverse=True)
        
        # Exclude draft notes
        notes = [n for n in notes if '#draft' not in n.read_text()]
        
        return notes[:limit]
```

### Custom Extraction Rules:
```json
{
  "extraction": {
    "enabled": true,
    "patterns": [
      "^## (.*):",  # Extract all ## headings
      "^KEY_INSIGHT: (.*)$",  # Custom marker
      "CONCLUSION:\\s+(.*)"  # Conclusion sections
    ],
    "folder_template": "ai-generated/{operation_type}/{date}",
    "naming_pattern": "{topic}-ai-{timestamp}"
  }
}
```

---

## 📚 Related Concepts

- [[Obsidian-Best-Practices-for-AI-Agents]]
- [[cloud-vault-mcp]]
- [[agent-context]]
- [[knowledge-graph-systems]]
- [[non-blocking-observability]]
- [[agent-context]] — the agent context data that hooks automatically load before each prompt
- [[context-management]] — the broader discipline of optimizing information payloads that hooks automate
- [[cloud-vault-mcp]] — the MCP server providing vault search and write tools that hooks invoke
- [[agentic-ai]] — the AI agent paradigm these context hooks serve
- [[tool-use]] — hooks orchestrate tool calls (vault search, write) as part of the agent lifecycle

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations
- VAULT_MANIFEST — the agent orientation map that hooks should reference for directory routing and conventions

---

**Status:** ✅ Production Ready
**Version:** 1.0 (2026-03-04)
**Maintainer:** AI Agent Collective
**Review Date:** 2026-04-04
