# Phase 5B Team Handbook

**Status**: Production Ready ✅
**Branch**: `feature/token-efficiency-5b`
**Tests**: 1599 passing
**Last Updated**: 2026-02-09

---

## What is Phase 5B?

Phase 5B delivers multi-agent coordination and cost optimization for the Cohezion framework:

- **Redis Semantic Cache** (5B.1): Distributed L1/L2/L3 caching across team
- **Skill Consensus Voter** (5B.2): Multi-agent voting for skill selection
- **Global Metrics Aggregator** (5B.3): Cross-instance performance tracking
- **Session Persistence** (5B.4): Vault-backed session storage with hot-loading
- **Cost-Aware Router** (5B.5): Query complexity → model routing optimization
- **Integration Testing** (5B.6): 46 comprehensive team execution tests

All backward compatible, fully tested, production-grade.

---

## Current State

| Aspect | Status |
|--------|--------|
| Code Implementation | ✅ Complete |
| Testing (1599 tests) | ✅ Passing |
| Vault Integration | ✅ Verified |
| MCP Server | ✅ Running |
| Security Audit | ✅ Passed |
| Risk Assessment | ✅ Green |
| Documentation | ✅ Complete |
| Git Merge Path | ✅ Clean |

---

## Quick Start

### Check Everything Works
```bash
# Status
git branch -v
uv run pytest tests/ -q --tb=no

# Vault + MCP
cd cloud-vault-mcp/vault && git status
curl http://localhost:8360/health
```

### Run Phase 5B Tests
```bash
# All Phase 5B tests
uv run pytest tests/compound/test_phase_5b_integration.py -v

# By component
uv run pytest tests/compound/test_skill_consensus_voter.py -v
uv run pytest tests/compound/test_global_metrics_aggregator.py -v
```

### Start MCP Server
```bash
cd cloud-vault-mcp
source .venv/bin/activate
source .env
python -m mcp_server.main
```

---

## Core Architecture

### 11-Step Executor Pipeline
1. Query vault
2. Parse request
3. Guardrails check
4. Execute
5. Detect anomalies
6. Analyze alignment
7. Extract patterns + refine skills
8. Record metrics
9. Track journey

### Team Execution
- **TeamOrchestrator** → Plans agents + tasks
- **ExecutionOrchestrator** → Wave-based parallel execution
- **SkillSelector** → Vault-driven ranking
- **SkillConsensusVoter** → Multi-agent voting (majority/weighted/unanimous)

### Caching Hierarchy
- **L1**: Hash-based (in-memory, <1ms)
- **L2**: Cosine similarity (semantic)
- **L3**: Vault + Redis (distributed)

---

## Essential Files

### In Codebase
- `GIT_WORKFLOW.md` → Git procedures and merge strategy
- `RISK_ASSESSMENT.md` → Risk matrix and mitigations
- `SECURITY_PROCEDURES.md` → Credentials and security management
- `PHASE_5B_ARCHITECTURE.md` → System diagrams and integration points

### In Vault
- `vault/decisions/` → All Phase 5B decisions
- `vault/patterns/` → Reusable patterns from implementation
- `vault/projects/` → Session-level documentation

---

## Team Roles

| Role | Responsibility |
|------|-----------------|
| devops-specialist | Git workflows, merge strategy, CI/CD |
| mcp-backend | MCP server operations, health checks |
| vault-specialist | Vault operations, decision logging |
| qa-lead | Testing, verification, sign-offs |
| security-auditor | Security review, credential management |
| architect | Design decisions, trade-offs |

---

## Common Tasks

### Add a New Skill
1. Implement in skill file
2. Add tests
3. Register in SkillRegistry (vault)
4. Log decision to vault
5. Update MEMORY.md

### Deploy Phase 5B
```bash
# 1. Final test run
uv run pytest tests/ -q

# 2. Create PR
gh pr create --base main --title "Phase 5B Complete: Multi-agent coordination"

# 3. Merge when approved
git switch main
git pull
git merge feature/token-efficiency-5b

# 4. Tag release
git tag -a v5b-complete -m "Phase 5B complete and merged"
```

### Update Project Memory
```bash
vim /home/mike-anderson/.claude/projects/-home-mike-anderson-dev-cohezion/memory/MEMORY.md
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tests fail | `git diff origin/develop src/` to see changes |
| MCP won't start | Check `.env`, verify vault path exists |
| Vault access fails | `cd cloud-vault-mcp/vault && git status` |
| Redis unavailable | L1/L2 cache falls back automatically |

---

## Key Metrics

- **Tests Passing**: 1599/1599 (100%)
- **Test Coverage**: >95% of new code
- **Regressions**: 0
- **Critical Issues**: 0
- **Security Issues**: 0
- **Backward Compatibility**: 100%

---

## Next Steps

1. ✅ **Phase 5B Code**: Production-ready
2. ⏳ **Merge to main**: When team approves
3. 📋 **Phase 5C Planning**: Scalability + performance

---

**Questions?** Check vault decisions or contact team lead.
