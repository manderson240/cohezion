# Data Directory

**Status:** Ephemeral Cache - NOT in version control

## Lifecycle Policy

This directory contains **generated data only**. All contents are regenerable from source code and configuration.

### What Goes Here

| Directory | Purpose | Regenerable By |
|-----------|---------|----------------|
| `journeys_25m/` | 25M journey simulation | `make run-simulation` |
| `surrealdb/` | SurrealDB database | `make db-init` |
| `overnight/` | Overnight session data | Re-run session |
| `ouroboros/` | Healing logs | Re-run healing |
| `flume/checkpoints/` | FLUME model weights | `make train-flume` |
| `compound/` | Compound metrics | `make compound-cycle` |
| `cache/` | Semantic cache | Auto-generated |

### Regeneration

```bash
# Clean all generated data
make clean-data

# Regenerate from source
make onboard

# Full reset
make reset-data
```

### Why This Matters

1. **Repository Size**: Prevents 15GB+ data bloat
2. **Onboarding**: Fresh clone = clean start
3. **CI/CD**: Predictable build environments
4. **Collaboration**: No merge conflicts on generated files

### Current Size (2026-03-04)

~15GB total, largest: `journeys_25m/` (7.5GB)

---

_See `docs/architecture.md` for full Data Directory Lifecycle Policy._
