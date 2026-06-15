# Sample Task: Add Rate Limiting to FastAPI Application

## Task Description

Add production-grade rate limiting to our FastAPI application to prevent API abuse.

### Requirements

1. **Per-endpoint rate limits**: Different limits for `/api/users` (100/min), `/api/search` (20/min), and `/api/admin/*` (500/min admin bypass)
2. **Redis backend**: Use Redis for distributed rate limit state (multiple instances)
3. **In-memory fallback**: Gracefully degrade to in-memory limiter if Redis is unavailable
4. **Rate limit headers**: Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
5. **429 responses**: Proper `Retry-After` header on rate limit exceeded
6. **Health endpoint exclusion**: `/health` and `/metrics` must bypass rate limiting

### Technical Context

- FastAPI 0.115.x
- Python 3.11
- Redis 7.x (via redis-py asyncio client)
- Existing middleware: CORS, request logging, JWT auth
- Test suite: pytest-asyncio with httpx AsyncClient

### Acceptance Criteria

- All existing tests continue to pass
- Rate limiting middleware tested with: happy path, burst (10x limit), distributed (two instances)
- No cold-start latency regression > 5ms on `/health` endpoint
- Deployed to staging within same PR

### Files Likely Affected

- `app/middleware/rate_limit.py` (create)
- `app/core/redis_client.py` (create or extend)
- `app/main.py` (register middleware)
- `app/api/deps.py` (optional: per-route dependency)
- `tests/middleware/test_rate_limit.py` (create)
- `tests/conftest.py` (add Redis test fixture)
- `requirements.txt` (add slowapi, limits, redis[asyncio])
- `docker-compose.yml` (add Redis service)
