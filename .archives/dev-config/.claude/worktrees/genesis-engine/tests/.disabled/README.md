# Disabled Test Files — Phase 5B.2 Dependencies

These test files have been temporarily disabled because they depend on modules that will be implemented in Phase 5B.2. They are NOT broken tests; they are tests for future functionality.

## Files in This Directory

### 1. `test_phase4_production_integration.py`
- **Depends on**: `cohezion.deployment.deployment_config`
- **Status**: Will be implemented in Phase 5B.2
- **Action**: Re-enable after deployment module is complete

### 2. `test_model_registry.py` & `test_model_info.py`
- **Depend on**: `cohezion.models.model_info`
- **Status**: Will be implemented in Phase 5B.2
- **Action**: Re-enable after model registry is complete

### 3. `test_adaptive_router_adapter.py`
- **Depends on**: `cohezion.swarm.adaptive_router_adapter`
- **Status**: Will be implemented in Phase 5B.2
- **Action**: Re-enable after adaptive router is complete

### 4. `test_deployment_priority4.py`
- **Depends on**: Deployment module infrastructure
- **Status**: Will be implemented in Phase 5B.2
- **Action**: Re-enable after deployment system is complete

## Re-enabling Instructions

In Phase 5B.2, once the dependent modules are implemented:

```bash
# Move test files back to main test directory
mv tests/.disabled/test_*.py tests/<appropriate-directory>/

# Verify imports resolve
uv run pytest <moved-file> --collect-only

# Run tests
uv run pytest tests/ -v
```

## Phase 5B Status

- **Phase 5B.1 (Current)**: 4 core components, 814 tests verified ✅
- **Phase 5B.2 (Next)**: SessionPersistence, 5 module implementations, security audit ✅

---

Generated: 2026-02-09
