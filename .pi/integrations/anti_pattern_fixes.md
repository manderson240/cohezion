# Anti-Pattern Fixes - 2026-04-02

## Critical: Blocking I/O in Async Functions

### Fixed Files

#### 1. `src/cohezion/flume/embedding_provider.py`
**Issue:** Used `requests.post()` in embedding methods
**Fix:** Added `AsyncOllamaEmbeddingProvider` class using `httpx.AsyncClient`
**Status:** ✅ Fixed - Added async provider alongside sync version
**Archive:** Old version at `.pi/archive/src/cohezion/flume/embedding_provider.py.*.bak`

**Migration Path:**
```python
# Old (blocking in async context)
from cohezion.flume.embedding_provider import OllamaEmbeddingProvider
provider = OllamaEmbeddingProvider()
vec = provider.embed(text)  # Blocks if called from async

# New (async-compatible)
from cohezion.flume.embedding_provider import AsyncOllamaEmbeddingProvider
provider = AsyncOllamaEmbeddingProvider()
vec = await provider.embed(text)  # Proper async
```

#### 2. `src/cohezion/swarm/token_client.py`
**Issue:** TBD - requests.post in async context
**Fix:** TBD
**Status:** ⏳ Pending

#### 3. `src/cohezion/gateway/ngrok_adapter.py`
**Issue:** TBD - requests.post in async context
**Fix:** TBD
**Status:** ⏳ Pending

#### 4. `src/cohezion/mcp/research_server.py`
**Issue:** TBD - requests.get in async context
**Fix:** TBD
**Status:** ⏳ Pending

---

## High: Bare Exception Handlers (178 instances)

**Files Affected:** Compound core, reliability, security modules

**Pattern:**
```python
# Bad
try:
    something()
except:  # Catches everything including KeyboardInterrupt
    pass

# Good
try:
    something()
except SpecificError as e:
    logger.error("Context: %s", e)
    circuit_breaker.record_failure()
```

**Status:** ⏳ Not yet fixed - Requires careful per-file analysis

---

## Medium: Bare pip in Documentation

**Files:** DEPLOYMENT_GUIDE.md, SECURITY.md, etc.

**Fix:** Replace `pip install` with `uv pip install`
**Status:** ⏳ Low priority - Documentation only

---

## Verification

Re-run scanner to verify fixes:
```bash
python3 .pi/integrations/anti_pattern_scanner.py
```

Expected: `embedding_provider.py` should show 0 blocking I/O instances.
