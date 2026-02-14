# Session 57: Ready to Execute

## Pre-Session Checklist (5 min)
- [ ] SurrealDB running: `curl http://localhost:8000/health`
- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Vault intact: `ls ~/vaults/cohezion-vault/decisions | wc -l`
- [ ] Review: SESSION_56_COMPACT_RETROSPECTIVE.md

## Execution Plan (2-3 hours)

### Step 1: Debug SQL (30 min)
**File**: `cloud-vault-mcp/src/mcp_server/graphrag_import.py:86-112`
**Fix**: Add full error logging, test minimal query, fix array/escaping
**Validation**: Import 1 doc successfully

### Step 2: Complete Phase 1 (30 min)  
**Action**: Import 10 vault docs with embeddings + graph edges
**Validation**: Query shows docs with embeddings and edges

### Step 3: Phase 2 Hybrid Query (1h)
**File**: `cloud-vault-mcp/src/mcp_server/graphrag_query.py` (new)
**Feature**: Semantic search + graph ancestry with caching
**Validation**: Query "test isolation" → returns pattern + ancestry

### Step 4: Phase 3-4 Integration (30 min)
**Files**: Extend VaultFileWatcher + compile_memory_from_vault.py
**Features**: Auto-sync + graph-aware MEMORY compiler
**Validation**: Edit vault file → SurrealDB updates → MEMORY.md shows graph

## Success Criteria
- [ ] SQL bug fixed (minimal query works)
- [ ] 10+ docs imported with embeddings
- [ ] Graph edges created and traversable
- [ ] Hybrid query working
- [ ] Auto-sync operational
- [ ] Token cost ≤10K

## Files to Modify
1. `cloud-vault-mcp/src/mcp_server/graphrag_import.py` (debug SQL)
2. `cloud-vault-mcp/src/mcp_server/graphrag_query.py` (create new)
3. `cloud-vault-mcp/src/mcp_server/vault_watcher.py` (add auto-sync)
4. `scripts/compile_memory_from_vault.py` (add graph queries)

## Expected Outcome
**Full GraphRAG operational**: 10× context for 0 additional tokens
**ROI**: Infinite (semantic search cost + free graph traversal)
**Time**: 2-3 hours
**Confidence**: 95%

---
**Status**: READY TO EXECUTE
**Next**: Load this file, execute plan, ship GraphRAG 🚀
