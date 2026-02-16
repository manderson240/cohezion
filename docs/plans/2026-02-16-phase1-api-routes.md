# Phase 1: API Route Modularization - Implementation Plan

**Status**: READY FOR IMPLEMENTATION
**Branch**: `spec/routes-consolidation`
**Token Budget**: 1,500-2,000
**Estimated Effort**: 1 session

## Current State (Baseline)

**File**: `src/cohezion/api/__init__.py`
**Size**: 2,074 lines (monolithic)
**Endpoints**: 40+ registered
**Models**: 15+ Pydantic classes
**Last Commit**: da461071 - fix: resolve test suite failures and apply codebase quality sweep

## Target State

- **__init__.py**: ~100 lines (app setup only)
- **models.py**: NEW - Shared Pydantic models
- **routes/**: 12 modular route files
  - Each module: Single APIRouter + related endpoints
  - Models extracted to shared module
  - Import pattern: `include_router()` in __init__

## Implementation Steps

### Step 1: Create Baseline Tests (Write BEFORE refactoring)

```python
# tests/api/test_route_modularization.py
- test_app_has_routes()
- test_health_endpoint_exists()
- test_count_endpoints() → Should be 40+
- test_endpoint_prefixes_exist() → ["/health", "/mcp", "/knowledge", "/swarm", "/journeys"]
- test_flume_endpoints_exist()
- test_rl_endpoints_exist()
- test_metrics_endpoints_exist()
- test_all_pydantic_models_defined() → Should have 30+ schemas in OpenAPI
- test_all_endpoint_methods() → GET, POST, etc.
```

### Step 2: Extract Shared Models

**Target**: `src/cohezion/api/models.py`

Models to extract (from __init__.py):
- `DebateRequest`, `DebateResponse`
- `SearchRequest`
- `FlumeTrainRequest`, `FlumeTrainResponse`, `FlumeStatusResponse`
- `FlumeEncodeRequest`, `FlumeEncodeResponse`
- `FlumeDecodeRequest`, `FlumeDecodeResponse`
- `FlumeInterpolateRequest`, `FlumeInterpolateResponse`
- `RLTrainRequest`, `RLTrainResponse`, `RLPolicyResponse`
- `TemplateParseRequest`, `TemplateParseResponse`
- `RlStepRequest`, `RlStepResponse`, `RlEpisodeResponse`, `RlPolicyInfoResponse`
- `SkillExecuteRequest`, `SkillExecuteResponse`, `PlanStepOut`
- `CapabilityQueryRequest`, `CapabilityQueryResponse`
- `AgentMetrics`, `AgentMetricsResponse`, `TrainingMetricsResponse`
- `PipelineStageStatus`, `PipelineStatusResponse`
- `SystemMetricsResponse`
- `KnowledgeQueryRequest`, `KnowledgeQueryResponse`
- `TokenMetricsResponse`
- `SwarmExecuteRequest`, `SwarmTaskResult`, `SwarmExecuteResponse`
- `CompoundMetricsResponse`, `CompoundExecuteRequest`, `CompoundStepOut`, `CompoundExecuteResponse`
- `CompoundFeedbackRequest`, `CompoundFeedbackResponse`
- `CompoundHealthResponse`, `CompoundHistoryResponse`

### Step 3: Create Route Modules

**Target**: `src/cohezion/api/routes/`

```
routes/__init__.py → Re-export all routers
routes/core.py → health, mcp endpoints
routes/knowledge.py → knowledge search, skills
routes/swarm.py → swarm debate, perspectives, metrics
routes/notebooks.py → notebook CRUD
routes/simulations.py → simulation CRUD
routes/journeys.py → journey visualization (250 lines ⭐)
routes/flume.py → VAE training (200 lines)
routes/templates.py → template parsing
routes/rl.py → RL training, inference (250 lines ⭐)
routes/skills.py → skill execution, capabilities
routes/metrics.py → observability (300 lines ⭐)
routes/compound.py → compound execution, feedback
```

**Pattern for each module**:
```python
from fastapi import APIRouter, HTTPException
from cohezion.api.models import DebateRequest, DebateResponse
from cohezion.mcp.swarm_server import get_server as get_swarm_server

router = APIRouter(prefix="/swarm", tags=["swarm"])

@router.post("/debate", response_model=DebateResponse)
async def run_debate(request: DebateRequest):
    # ...

# Export
__all__ = ["router"]
```

### Step 4: Refactor __init__.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import all routers
from cohezion.api.routes import (
    core_router,
    knowledge_router,
    swarm_router,
    notebooks_router,
    simulations_router,
    journeys_router,
    flume_router,
    templates_router,
    rl_router,
    skills_router,
    metrics_router,
    compound_router,
)

app = FastAPI(
    title="Cohezion API",
    description="AI Research Lab API",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, ...)
app.mount("/static", ...)

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# Include all routers
app.include_router(core_router)
app.include_router(knowledge_router)
# ... include all routers

__all__ = ["app"]
```

### Step 5: Verify Tests Pass

```bash
uv run pytest tests/api/test_route_modularization.py -q --tb=short

Expected: All tests pass ✅
- 40+ endpoints registered
- All prefixes found
- 30+ OpenAPI schemas
- GET, POST methods present
```

### Step 6: Run Full API Sanity Check

```bash
# Start API
uv run uvicorn cohezion.api:app --reload &

# Test key endpoints
curl http://localhost:8000/health
curl http://localhost:8000/flume/status
curl http://localhost:8000/rl/policy-info
```

### Step 7: Commit & Push

```bash
git add -A
git commit -m "refactor: modularize API routes into cohesive route files

Extracts 2,074-line monolithic __init__.py into 12 focused route modules:
- core (health, MCP registry)
- knowledge (search, skills)
- swarm (debate, perspectives)
- notebooks (CRUD)
- simulations (CRUD)
- journeys (visualization, trajectories)
- flume (VAE training, encode/decode)
- templates (template parsing)
- rl (training, inference, episodes)
- skills (execution, capabilities)
- metrics (observability, system metrics)
- compound (execution, feedback, health)

Shared models extracted to api/models.py for reusability.

Benefits:
- __init__.py reduced from 2,074 → ~100 lines
- Clear separation of concerns
- Easier to test and maintain
- Better for future extensions
- No behavioral changes (tests unchanged)

See PHASE_1_PLAN.md for architecture details."

git push origin spec/routes-consolidation
```

## Testing Strategy

### Baseline Tests (Run First)
- Route count (40+)
- Route prefixes
- Pydantic models (30+)
- HTTP methods

### Sanity Tests (Run After)
- Health endpoint works
- FLUME endpoints accessible
- RL endpoints accessible
- Metrics endpoints accessible

## Critical Notes

1. **NO behavioral changes** - Just reorganization
2. **Extract models FIRST** - Prevents import errors
3. **Test FREQUENTLY** - After each route module
4. **Use APIRouter** - Not creating independent apps
5. **Import from models** - All Pydantic classes from api.models

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Import cycles | models.py has NO imports from routes/ |
| Missing endpoints | Baseline test ensures all 40+ present |
| Broken response models | Extract to shared models.py first |
| Missing middleware | Keep middleware in __init__.py |
| Broken static files | Mount in __init__.py after includes |

## Success Criteria

- ✅ Tests pass (test_route_modularization.py)
- ✅ __init__.py < 150 lines
- ✅ 12 route modules created
- ✅ models.py with 15+ classes
- ✅ No endpoints lost
- ✅ API starts without errors
- ✅ Ready for Phase 2 (Executor Formalization)

## Token Accounting

- Models extraction: 100 tokens
- Routes creation (12 files): 700 tokens
- __init__.py refactor: 150 tokens
- Tests & verification: 150 tokens
- **Total: ~1,100 tokens (under 1,500 budget)**

## Next Phase (Phase 2)

After Phase 1 complete:
- Executor Formalization (executor_steps.py integration)
- Formal step typing and journeys tracking
- RetrospectionEngine updates
- Tests: executor behavior, journey tracking

---

**Branch**: spec/routes-consolidation
**Approved**: Yes
**Ready for Implementation**: Yes
**Session**: Next session, run: `git checkout spec/routes-consolidation && git pull`
