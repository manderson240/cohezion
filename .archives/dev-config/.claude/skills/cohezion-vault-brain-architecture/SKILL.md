---
name: cohezion-vault-brain-architecture
description: |
  Directory map for ~/vaults/cohezion-vault/ after brain-inspired reorganization.
  Use when: (1) writing vault files (patterns/, concepts/, decisions/ no longer exist),
  (2) getting "No such file or directory" on vault paths, (3) any session that needs
  to locate vault knowledge by category.
  Key insight: vault reorganized from flat Obsidian to brain-region metaphor structure.
author: Claude Code
version: 1.0.0
---

# Cohezion Vault Brain Architecture Directory Map

## Problem

The vault reorganized from a flat structure to a brain-inspired architecture.
Old paths (patterns/, concepts/, decisions/) no longer exist. Files written
there disappear silently (Write tool succeeds but files are gone on next access).

## Directory Mapping (Old to New)

| Old Path | New Path | Metaphor |
|----------|----------|----------|
| `patterns/` | `cerebellum/` | Procedural patterns, skills |
| `concepts/` | `cortex/` | Knowledge, concepts, theory |
| `decisions/` | `prefrontal/` | Decision records, plans |
| `memories/sessions/` | `hippocampus/` | Session logs, retrospectives |
| (new) | `thalamus/` | Routing, indexing |
| (new) | `subconscious/` | Background processes |
| (new) | `dreaming/` | Synthesis, ideation |
| (new) | `sensory/` | External input processing |
| (new) | `motor/` | Action patterns |
| (new) | `genome/` | Core architecture/DNA |
| `skills_index/` | `skills_index/` | Unchanged |
| `learnings/` | `learnings/` | Unchanged |
| `research/` | `research/` | Unchanged |

## Write Files To

- **Pattern/how-to**: `cerebellum/my-pattern.md`
- **Concept/knowledge**: `cortex/my-concept.md`
- **Decision record**: `prefrontal/YYYY-MM-DD-decision-name.md`
- **Session retrospective**: `hippocampus/YYYY-MM-DD-session.md`
- **Routing/indexing**: `thalamus/index-name.md`
- **Synthesis/ideation**: `dreaming/idea-name.md`
- **Action patterns**: `motor/action-name.md`
- **Core architecture**: `genome/component-name.md`

## Verification

```bash
ls ~/vaults/cohezion-vault/cortex/ | head -5   # Should show concept files
ls ~/vaults/cohezion-vault/cerebellum/ | head -5  # Should show pattern files
ls ~/vaults/cohezion-vault/prefrontal/ | head -5  # Should show decision files
```

## Known Issues

- `store_node` MCP tool has a bug: `UniverseNode.__init__() missing 1 required positional argument: 'id'` -- the `id` param is required server-side but not in the JSON schema. Workaround: use `store_learning` instead for persistent storage.
- Plugin removal from `~/.claude/plugins/installed_plugins.json` may be reverted by session restarts or marketplace syncs. Always keep a backup and re-apply if reverted.
