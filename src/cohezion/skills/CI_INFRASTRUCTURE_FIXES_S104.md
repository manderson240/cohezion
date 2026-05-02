---
id: skill-ci-infrastructure-fixes
name: CI Infrastructure Fixes and Telemetry
domain: DevOps
version: v1.0
tier: PRIME
coherence: 0.95
parent: compound-engineering
related:
  - skill-telemetry-observability
  - [[skill-pytest-markers]]
  - [[skill-uv-lock-management]]
aliases:
  - CI Test Infrastructure
  - uv Troubleshooting
created: 2026-04-20
source: Session 104
---

# Skill: CI Infrastructure Fixes and Telemetry

## Context
Session 104 encountered critical CI failures blocking all development.

## Problem
- `uv.lock` changes forced 6+ hour torch/triton source compiles
- `cloud-vault-mcp` missing directory caused immediate failures
- No fast test targets for CI gating
- No skill validation in CI pipeline

## Solution Applied

### 1. Dependency Resolution Fix
```toml
# Removed from pyproject.toml dependencies:
- "cloud-vault-mcp",

# Changed to optional path source:
# cloud-vault-mcp = { path = "cloud-vault-mcp", editable = true }
```

### 2. uv.lock Regeneration
```bash
# Before: 724KB (broken - source compiles)
# After: 437KB (fixed - cached wheels)
uv lock --upgrade
```

### 3. Test Infrastructure
```makefile
test-fast:
	uv run pytest tests/ -m fast --tb=short -q

test-smoke:
	@# Quick validation

test-integration:
	@# Live services
```

## Key Insights
1. **uv sources must map to actual paths** - Missing paths fail immediately
2. **torch wheels exist on pytorch-rocm index** - Not PyPI for ROCm
3. **pytest markers enable CI stratification** - Fast vs integration
4. **CI must fail fast** - 6h compiles block all other work

## Telemetry Integration
Added `make telemetry-dashboard` to view compound loop metrics.

## Validation
- Fast tests: ⚡ <1s each
- Full suite: ~90s
- Root cause: [[learning-uv-fork-markers]]

## Backlinks
- [[Session 104]]
- [[PR #68 Fix]]
- [[Learning: ImportError as optional dependency]]

## References
- [[pyproject.toml]]
- [[Makefile]]
- [[uv.lock]]

---
canonical: true
coherence_verified: 2026-04-20
