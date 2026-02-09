# Phase 5B Quick Start Guide

For team members continuing Phase 5B work after vault/MCP verification sprint.

## Current State

- **Branch**: `feature/token-efficiency-5b`
- **Status**: PRODUCTION READY ✅
- **Tests**: 1097 passing (892 core + 205 Phase 5B)
- **Vault**: All Phase 5B files committed
- **MCP**: Server verified, Claude Code integration ready
- **Security**: Audit clean, no critical issues
- **Git**: Clean merge to develop available

## Essential Files

### Documentation
- `GIT_WORKFLOW_PHASE_5B.md` - How to work with git
- `PHASE_5B_COMMIT_CHECKLIST.md` - Commit strategy per subsystem
- `PHASE_5B_SESSION_40_FINAL_REPORT.md` - Complete status
- `VAULT_MCP_VERIFICATION_SPRINT.md` - Sprint context

### Vault Documents
- All Phase 5B session docs: `cloud-vault-mcp/vault/projects/`
- Decisions: `cloud-vault-mcp/vault/decisions/`
- Patterns: `cloud-vault-mcp/vault/patterns/`

## Quick Commands

### Check Status
```bash
# Current branch
git branch -v

# Test status
uv run pytest tests/ -q --tb=no

# Vault status
cd cloud-vault-mcp/vault && git log --oneline -5
```

### MCP Server
```bash
# Start server (from cloud-vault-mcp directory)
source .venv/bin/activate
source .env
python -m mcp_server.main

# Check health
curl http://localhost:8360/health
```

### Claude Code Integration
```bash
# MCP tools available in Claude Code:
# - vault_read
# - vault_write
# - vault_search
# - vault_list
```

### Git Workflow
```bash
# Pull latest from develop
git fetch origin develop

# Check merge readiness
git merge --no-commit --no-ff origin/develop

# Abort merge (no changes yet)
git merge --abort

# When ready to merge
git merge origin/develop

# Create PR
gh pr create --base main --title "Phase 5B Complete: ..."
```

## Phase 5B Subsystems

All production-ready, fully tested:

1. **Redis Semantic Cache** (5B.1)
   - L1/L2 local + Redis L3
   - File: `src/cohezion/cache/redis_semantic_cache.py`

2. **Skill Consensus Voter** (5B.2)
   - Multi-agent voting with 3 strategies
   - File: `src/cohezion/compound/skill_consensus_voter.py`

3. **Global Metrics Aggregator** (5B.3)
   - Cross-instance distributed metrics
   - File: `src/cohezion/compound/global_metrics_aggregator.py`

4. **Session Persistence** (5B.4)
   - Vault-backed session storage
   - File: `src/cohezion/compound/session_manager_persistence.py`

5. **Cost-Aware Router** (5B.5)
   - Query complexity routing
   - File: `src/cohezion/swarm/cost_aware_router.py`

6. **Integration Testing** (5B.6)
   - 46 comprehensive integration tests
   - File: `tests/compound/test_phase_5b_integration.py`

## Key Architecture

### 11-Step CompoundExecutor Pipeline
1. Query vault
2. Parse request
3. Guardrails check
4. Execute
5. Detect anomalies
6. Analyze alignment
7. Extract patterns + refine skills
7.5. Check degradation
7.7. Record model quality
8. Record metrics
9. Track journey (12D FLUME)

### Team Execution (DAG-aware)
- TeamOrchestrator: Plan agents + tasks from intent
- ExecutionOrchestrator: Wave-based parallel execution
- TeamCompoundExecutor: Bridge orchestrator to executor per task
- SkillSelector: Vault-driven skill ranking

### Multi-Tier Caching
- L1: Hash-based (in-memory, instant)
- L2: Cosine similarity (semantic, 25-30% improvement)
- L3: Vault + Redis (distributed, team-wide)

## Test Suite

Run full tests:
```bash
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q
```

Expected: 1097 passing

By component:
```bash
# Phase 5B specific tests
uv run pytest tests/compound/test_skill_consensus_voter.py -v
uv run pytest tests/compound/test_global_metrics_aggregator.py -v
uv run pytest tests/compound/test_session_manager_persistence.py -v
```

## Common Tasks

### Access Vault Knowledge
```bash
# From Claude Code CLI
# (MCP server must be running)

# List decisions
vault_list directory="decisions"

# Search for pattern
vault_search query="compound engineering"

# Read decision
vault_read path="decisions/2026-02-09-session-40-phase-5b-qa-verification-complete.md"
```

### Add New Decision
```python
# From Python code with vault access
from cohezion.core.mcp_client import MCP_CLIENT

result = MCP_CLIENT.call_tool(
    'vault_log_decision',
    project='cohezion',
    title='My Phase 5B Decision',
    context='...',
    decision='...',
    rationale='...'
)
```

### Update MEMORY
```bash
# Edit project memory
vim /home/mike-anderson/.claude/projects/-home-mike-anderson-dev-cohezion/memory/MEMORY.md
```

## Troubleshooting

### MCP Server Not Starting
```bash
# Check dependencies
source .venv/bin/activate
pip install -e .

# Check .env
cat cloud-vault-mcp/.env | grep -E "VAULT_PATH|MCP_PORT"

# Check port
lsof -i :8360
```

### Vault Access Issues
```bash
# Verify vault git
cd cloud-vault-mcp/vault
git status
git log --oneline -3

# Check file permissions
ls -la cloud-vault-mcp/vault/
```

### Test Failures
```bash
# Run with verbose output
uv run pytest tests/compound/test_phase_5b_integration.py -v

# Run single test
uv run pytest tests/compound/test_phase_5b_integration.py::TestName -v

# Check recent changes
git diff origin/develop src/
```

## Next Phase (Phase 5C)

After Phase 5B rollout:
- Long-term vault scalability
- MCP server performance optimization
- Redis cluster deployment
- Advanced monitoring and alerting
- Team scaling to 10+ agents

## Support

### Documentation
- Full specs: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/QUICKSTART.md`
- Architecture: See vault `/projects/`
- Patterns: See vault `/patterns/`

### Team Coordination
- Vault decisions: Ground truth for decisions
- Memory file: Project-level knowledge
- Task tracking: Sprint coordination
- Slack/Messages: Real-time coordination

## Key Contacts

- **Vault/Knowledge**: vault-specialist or vault-integrity-checker
- **Git/CI**: devops-specialist or git-conflict-analyst
- **MCP/Integration**: mcp-backend or integration-engineer
- **QA/Verification**: qa-lead
- **Security/Risk**: security-auditor or risk-synthesizer

---

**Last Updated**: 2026-02-09
**Status**: Phase 5B Ready for Execution ✅
**Production Ready**: YES ✅
