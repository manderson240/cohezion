# Cohezion API Endpoint Summary

## Documentation Created

- **docs/COHEZION_API.md** - Comprehensive API reference (600+ lines)
- **docs/API_QUICKSTART.md** - Getting started guide with examples

---

## Endpoint Statistics

### Total Endpoints: 72+

| Category | Count | Endpoints |
|----------|-------|-----------|
| **Health & Monitoring** | 8 | `/health`, `/metrics/*` (7) |
| **Universe Operations** | 4 | `/universe/nodes`, `/wallet`, `/simulate/step`, WS `/pulse` |
| **MCP & Knowledge** | 5 | `/mcp/*` (2), `/knowledge/*` (3) |
| **Swarm Operations** | 4 | `/swarm/*` |
| **Journey Tracking** | 7 | `/journeys/*` (6), `/compare/calm-vs-llm/*` |
| **FLUME VAE** | 5 | `/flume/*` |
| **RL Policy** | 5 | `/rl/*` |
| **Skills** | 3 | `/skills/*`, `/query/*`, `/templates/*` |
| **Observability** | 9 | `/metrics/*` (dashboard, trends, reset, etc.) |
| **Compound Engineering** | 5 | `/compound/*` |
| **Streaming** | 6 | `/inference/*` |
| **Anima** | 3 | `/anima/*` |
| **Vault** | 3 | `/vault/*` |
| **Static/Root** | 2 | `/`, `/static/*` |

---

## HTTP Methods Distribution

| Method | Count | Example Endpoints |
|--------|-------|-------------------|
| **GET** | 42 | `/health`, `/metrics/*`, `/journeys/{id}` |
| **POST** | 25 | `/compound/execute`, `/swarm/debate`, `/flume/train` |
| **DELETE** | 2 | `/inference/cancel/{id}` |
| **WebSocket** | 1 | `/pulse` |
| **SSE** | 2 | `/inference/stream`, `/inference/resume/*` |

---

## Key Features Documented

### Authentication
- Bearer token required for Vault endpoints
- Open access for most endpoints

### Rate Limiting
- Per-IP rate limiting via middleware
- Headers: `X-RateLimit-*`, `Retry-After`

### Data Models
- PhysicsState (12D coordinates)
- Journey / JourneyStep
- HealthStatus enumeration

### WebSocket
- Real-time pulse streaming at 500ms intervals
- 8-dimensional brane vector

### Streaming (SSE)
- Long-running inference with checkpoint support
- Session management (create, resume, cancel, close)

### Error Codes
- Standard HTTP status codes
- Consistent JSON error format

---

## Vector Dimensions

| Endpoint | Dimension | Notes |
|----------|-----------|-------|
| `/flume/encode` | 256D | Input vector |
| `/flume/decode` | 256D | Output reconstruction |
| `/flume/interpolate` | 256D | Both input vectors |
| `/rl/step` | 256D | State and action vectors |
| `/rl/episode` | 256D | Trajectory states |

---

## 12D Physics Model

The API uses a 12-dimensional physics model for agent trajectories:

| Dimension | Description | Range |
|-----------|-------------|-------|
| x | Spatial X | -1 to 1 |
| y | Spatial Y | -1 to 1 |
| z | Synthesis progress | 0 to 1 |
| time | Temporal | 0 to 1 |
| mass | Information density | 0 to 1 |
| sentiment | Emotional valence | 0 to 1 |
| complexity | Cognitive load | 0 to 1 |
| factuality | Groundedness | 0 to 1 |
| connectivity | Network links | 0 to 1 |
| stability | System stability | 0 to 1 |
| novelty | Innovation | 0 to 1 |
| coherence | Overall coherence | 0 to 1 |

---

## Source Files

| File | Endpoints | Description |
|------|-----------|-------------|
| `src/cohezion/api/__init__.py` | 55 | Main API routes |
| `src/cohezion/api/routes_universe.py` | 4 | Universe simulation |
| `src/cohezion/api/routes_anima.py` | 3 | Narration generation |
| `src/cohezion/api/routes_vault.py` | 3 | Semantic search |
| `src/cohezion/api/observability_endpoints.py` | 10 | Metrics & dashboard |
| `src/cohezion/api/streaming.py` | 6 | SSE inference |

---

## Links

- Full Reference: [COHEZION_API.md](./COHEZION_API.md)
- Quickstart: [API_QUICKSTART.md](./API_QUICKSTART.md)
- OpenAPI: `/docs` (development mode)
- Source: `src/cohezion/api/`
