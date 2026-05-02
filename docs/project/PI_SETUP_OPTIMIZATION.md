# Pi 0.66 Setup Optimization

**Date**: 2026-04-08  
**Commit**: `82374da`  
**Feature Activation**: 2 → 15 (650% improvement)

## What Was Done

### 1. Extensions Auto-Loading (was broken)
**Before**: `cohezion-kg.ts` was in `.pi/extensions/` but NOT registered in settings — had to be loaded manually with `-e` flag  
**After**: Both extensions auto-load from `.pi/settings.json`

| Extension | Purpose | Auto-load |
|-----------|---------|-----------|
| `cohezion-kg.ts` | KG search, history, stats, `/retro` | ✅ Now |
| `cohezion-bridge-v3.ts` | Journey tracking, pattern extraction, `/cohezion` | ✅ New |

### 2. New: cohezion-bridge-v3.ts
Replaces the disabled `cohezion-bridge.ts.disabled` (v2) which relied on fragile MCP subprocess calls.

| Feature | v2 (disabled) | v3 (active) |
|---------|---------------|-------------|
| Alignment engine | MCP subprocess → coherence_server.py | Running success ratio |
| Pattern extraction | FLUME-encoded MCP calls | Append-only pattern buffer |
| Journey tracking | MCP + separate trajectory | Local JSONL trajectory |
| Skill search | MCP coherence.query | File system + fuzzy match |
| `/cohezion` command | Full MCP stack | Lightweight local operations |
| Failure mode | Server crash = total failure | Graceful degradation |
| Token overhead | Heavy MCP wire format | Minimal |

### 3. Project Skills (.pi/skills/)
Zero → 3 project-level Pi skills that surface Cohezion knowledge:

| Skill | Trigger | Use Case |
|-------|---------|----------|
| `cohezion-patterns` | "compound patterns", "how does X work" | Search 212 PRIME skills via KG |
| `cohezion-test` | "run tests", "check coverage" | Correct test patterns + isolation |
| `cohezion-kaggle` | "kaggle", "competition", "notebook" | Blackwell handshake + workflow |

### 4. Prompt Templates (.pi/prompts/)
Zero → 6 reusable slash commands:

| Template | Usage | Key Feature |
|----------|-------|-------------|
| `/review` | `/review focus=security` | Variable substitution |
| `/debug` | `/debug description=auth timeout` | KG search integration |
| `/implement` | `/implement description=add caching` | Compound loop workflow |
| `/optimize` | `/optimize target=step_µs` | Autoresearch integration |
| `/research` | `/research topic=HIHO stability` | Web + KG search |
| `/retro` | `/retro` | Session retrospective |

### 5. System Prompt Customization
**Before**: Pi used its generic 1000-token system prompt  
**After**: Two augmentation layers:

- **`.pi/SYSTEM.md`** — Replaces default prompt with Cohezion-specific 32-line prompt (tool descriptions, project rules, key directories)
- **`.pi/APPEND_SYSTEM.md`** — Adds project identity, critical rules, architecture quick ref, extension guide, model reference, session tips

### 6. Read-Only Tools Enabled
**Before**: Only `read, bash, edit, write` (default)  
**After**: `read, bash, edit, write, grep, find, ls`

These 3 additional read-only tools let the agent safely explore the codebase without risk:
- `grep` — Search file contents
- `find` — Find files by glob pattern
- `ls` — List directory contents

### 7. Model Cycling (Ctrl+P)
**Before**: No model cycling configured  
**After**: 5 Ollama cloud models for quick switching:

| Model | Context | Vision | Reasoning |
|-------|---------|--------|-----------|
| `glm-5.1:cloud` (default) | 202K | ❌ | ✅ |
| `kimi-k2.5:cloud` | 262K | ✅ | ✅ |
| `gemma4:31b-cloud` | 262K | ✅ | ✅ |
| `minimax-m2.7:cloud` | 204K | ❌ | ✅ |
| `glm-5:cloud` | 202K | ❌ | ✅ |

### 8. Thinking Level
**Before**: `medium`  
**After**: `high` — more reasoning depth for complex Cohezion tasks

### 9. Proactive Compaction
**Before**: Not configured  
**After**: `{ enabled: true, proactive: true }` — auto-compacts when context approaches limit, preserving session continuity

### 10. Feature Comparison Summary

| Feature | Before | After | Status |
|---------|--------|-------|--------|
| Extensions auto-loaded | 0 | 2 | ✅ Fixed |
| Project skills | 0 | 3 | ✅ New |
| Prompt templates | 0 | 6 | ✅ New |
| System prompt | Generic | Cohezion-aware | ✅ Upgraded |
| Read-only tools | 0 | 3 | ✅ New |
| Model cycling | Not configured | 5 models | ✅ New |
| Thinking level | medium | high | ✅ Upgraded |
| Compaction | Default | Proactive | ✅ Configured |
| Coherence bridge | Disabled (v2) | Active (v3) | ✅ Rebuilt |
| Global model cycling | Not configured | 5 models | ✅ New |

## How to Use

### Start Pi with full setup:
```bash
pi
# All extensions, skills, prompts, and tools auto-load from .pi/settings.json
```

### Key commands:
```
/cohezion skills          # List PRIME skills
/cohezion skill HIHO_STABILITY_PRIME  # Materialize a skill
/cohezion trajectory      # Session stats
/cohezion patterns        # Recent pattern extractions
/retro                    # Session retrospective (via KG extension)
/autoresearch             # Autoresearch mode (via package)
/review                   # Code review prompt template
/debug                    # Debug workflow prompt
/implement                # Feature implementation prompt
/optimize                 # Optimization prompt (uses autoresearch)
/research                 # Research prompt (KG + web search)
Ctrl+P                    # Cycle through 5 cloud models
Ctrl+X                    # Toggle autoresearch dashboard
Shift+Tab                 # Cycle thinking level
/compact                  Manual context compaction
/tree                     Session branching
```

### Switch models mid-session:
Type `/model` or press `Ctrl+L` for model selector, `Ctrl+P` to cycle through configured models.

### Using skills:
```
/skill:cohezion-patterns  # Search 212 PRIME skills
/skill:cohezion-test      # Run tests correctly
/skill:cohezion-kaggle     # Kaggle/Blackwell workflows
```

## Files Created/Modified

| File | Action |
|------|--------|
| `.pi/settings.json` | Updated: extensions, tools, models, thinking |
| `.pi/SYSTEM.md` | New: Cohezion-specific system prompt |
| `.pi/APPEND_SYSTEM.md` | New: Project context augmentation |
| `.pi/extensions/cohezion-bridge-v3.ts` | New: Lightweight bridge extension |
| `.pi/skills/cohezion-patterns/SKILL.md` | New: PRIME skills search skill |
| `.pi/skills/cohezion-test/SKILL.md` | New: Test runner skill |
| `.pi/skills/cohezion-kaggle/SKILL.md` | New: Kaggle workflow skill |
| `.pi/prompts/review.md` | New: Code review template |
| `.pi/prompts/debug.md` | New: Debug workflow template |
| `.pi/prompts/implement.md` | New: Feature implementation template |
| `.pi/prompts/optimize.md` | New: Optimization template |
| `.pi/prompts/research.md` | New: Research template |
| `.pi/prompts/retro.md` | New: Retrospective template |
| `~/.pi/agent/settings.json` | Updated: model cycling, compaction |

## Deprecated/Disabled

| File | Status | Reason |
|------|--------|--------|
| `.pi/extensions/cohezion-bridge.ts.disabled` | Still disabled | Replaced by v3,kept for reference |