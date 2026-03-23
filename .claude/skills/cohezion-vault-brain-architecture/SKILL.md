---
name: cohezion-vault-brain-architecture
description: |
  Directory map for ~/vaults/cohezion-vault/ — brain-arch migration IS COMPLETE
  as of 2026-03-23. cortex/ (255 files) and cerebellum/ (95 files) exist at the
  monorepo root. Obsidian points to ~/vaults/cohezion-vault/. SurrealDB has 343
  neurons on port 8001. Use when: (1) writing vault files, (2) investigating vault
  structure, (3) running vault-keeper or reimport, (4) getting path errors on
  cortex/cerebellum. Key insight: monorepo IS the Obsidian vault; cloud-vault-mcp
  has copies but the monorepo is the source of truth.
author: Claude Code
version: 3.0.0
---

# Cohezion Vault — Actual Directory Geography

## Brain-Architecture Status (as of 2026-03-23)

**MIGRATION IS COMPLETE.** `cortex/` and `cerebellum/` exist at the monorepo root.

```bash
ls ~/vaults/cohezion-vault/cortex/ | wc -l      # → 255
ls ~/vaults/cohezion-vault/cerebellum/ | wc -l   # → 95
```

Obsidian is configured to open `~/vaults/cohezion-vault` (the monorepo root).

## Vault Geography

```
~/vaults/cohezion-vault/                  ← Obsidian vault + monorepo root
├── cortex/           (255 .md files)     ← Knowledge neurons: physics, ML, cosmologies, MOCs
├── cerebellum/       (95 .md files)      ← Operational neurons: coordination, protocols
├── tools/
│   ├── vault-keeper-cycle.py             ← VAULT_PATH = ~/vaults/cohezion-vault
│   ├── vault-backup.py                   ← Daily backup to ~/.cohezion-backups/vault/
│   └── git-hooks/pre-commit              ← Protects cortex/ and cerebellum/ from deletion
├── cloud-vault-mcp/                      ← Subdirectory copy (secondary, for MCP context)
└── ...codebase...

~/dev/cohezion/cloud-vault-mcp/           ← Separate git repo for MCP server
├── vault/cortex/     (255 files, copy)
├── vault/cerebellum/ (95 files, copy)
├── run_mcp.py                            ← VAULT_PATH = ~/vaults/cohezion-vault
└── scripts/reimport_vault.py             ← VAULT_PATH = ~/vaults/cohezion-vault, port 8001
```

## Source of Truth

The **monorepo** (`~/vaults/cohezion-vault/`) is the canonical vault:
- Obsidian opens it directly
- `vault-keeper-cycle.py` scans it
- `reimport_vault.py` reads from it
- Backups come from it

`cloud-vault-mcp/vault/` holds copies that were synced but are not the primary.

## SurrealDB Graph (port 8001)

```bash
# Current counts
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -H "Content-Type: text/plain" -u root:root \
  -d "SELECT type, count() FROM vault_memory GROUP BY type; SELECT count() FROM informed_by GROUP ALL;"
# → 343 neurons, 3399 edges
```

## Brain-Region Directory Contents

| Directory | Files | Content |
|-----------|-------|---------|
| `cortex/` | 255 | Physics (FLUME, 12D-Manifold, AdS/CFT, Bose-Einstein), ML (federated learning, cellular automata), MOC indices, dashboards |
| `cerebellum/` | 95 | Operational coordination: scheduler patterns, mobile terminal, parallel session, vault-first protocol |

Key MOC hub files in `cortex/`: `MOC-agentic-ai.md` (45 links), `MOC-astrophysics.md`
(68 links), `MOC-machine-learning.md` (54 links), `MOC-new-science-toe.md` (67 links).

## Guardrails (installed 2026-03-23)

**Pre-commit hook**: `~/vaults/cohezion-vault/.git/hooks/pre-commit`
- Blocks commits that stage 3+ deletions from `cortex/` or `cerebellum/`
- Override: `VAULT_DELETION_OK=1 git commit` or `git commit --no-verify`

**Daily backup timer**: `vault-backup.timer` (systemd --user)
- Backs up cortex/ + cerebellum/ to `~/.cohezion-backups/vault/YYYY-MM-DD/`
- 14-day retention

## Recovery Procedure

If cortex/cerebellum are accidentally deleted again:

```bash
# 1. Find the deletion commit
cd ~/vaults/cohezion-vault
git log --all --oneline --full-history -- "cortex/" | head -5

# 2. Restore from git (parent of deletion commit)
git checkout <deletion-commit>^ -- cortex/ cerebellum/
git restore --staged cortex/ cerebellum/  # unstage (don't recommit to monorepo)

# 3. Or restore from backup (faster, no git needed)
cp -r ~/.cohezion-backups/vault/YYYY-MM-DD/cortex ~/vaults/cohezion-vault/
cp -r ~/.cohezion-backups/vault/YYYY-MM-DD/cerebellum ~/vaults/cohezion-vault/

# 4. Re-import to SurrealDB
cd ~/dev/cohezion/cloud-vault-mcp
.venv/bin/python scripts/reimport_vault.py

# 5. Restart MCP
pkill -f run_mcp.py
cd ~/dev/cohezion/cloud-vault-mcp && .venv/bin/python run_mcp.py &
```

## Config Summary

| Script | VAULT_PATH | SurrealDB |
|--------|-----------|-----------|
| `tools/vault-keeper-cycle.py` | `~/vaults/cohezion-vault` | `http://localhost:8001` (env) |
| `run_mcp.py` | `~/vaults/cohezion-vault` | `http://localhost:8001` (env) |
| `scripts/reimport_vault.py` | `~/vaults/cohezion-vault` | `http://localhost:8001` (hardcoded) |

## Known Issues

- `execute_surreal_async` in `graphrag_helpers.py` previously had hardcoded `:8000` —
  fixed 2026-03-23. See `graphrag-execute-surreal-hardcoded-url` skill.
- `papers/`, `decisions/`, `patterns/`, `experiments/` do NOT exist in the monorepo root
  (they were never migrated there). `reimport_vault.py` shows "Directory not found"
  warnings for these — expected, not an error.
