# Portfolio Transformation Plan — Compound Engineering Approach

**Target**: Research Engineer, Universes @ Anthropic
**Strategy**: Compound engineering with TDD + multi-agent adversarial review + graph traceability
**Timeline**: 4 weeks (8-10 hours/week)
**Date**: 2026-03-22

---

## Executive Summary

Transform Cohezion into a living portfolio using **compound engineering principles**:

1. **TDD-First**: Write failing tests → implement → pass tests → refactor
2. **Multi-Agent Review**: Every component reviewed by swarm (5 specialist perspectives)
3. **Graph Traceability**: All decisions, experiments, patterns logged to SurrealDB vault
4. **Compound Loop Integration**: Each implementation improves future implementations

**Key Insight**: Don't just build a portfolio—demonstrate **how** you build (compound engineering in action).

---

## Phase 1: Foundation (Week 1) — FLUME VAE Demo

### Goal: One Interactive Demo Live on cohezion.duckdns.org

**Deliverable**: 3D latent space navigator (user clicks → FLUME navigates → real-time visualization)

### Implementation Strategy (Compound Engineering)

#### Step 1: TDD-First API Endpoint (2-3 hours)

**Test-Driven Development Cycle**:

```python
# tests/api/test_flume_endpoints.py
import pytest
from cohezion.api import app
from fastapi.testclient import client

def test_flume_latent_space_endpoint_exists():
    """Test that /flume/latent-space endpoint exists"""
    response = client.get("/flume/latent-space")
    assert response.status_code in [200, 500]  # Exists but may fail

def test_flume_latent_space_returns_embeddings():
    """Test that endpoint returns 3D embeddings"""
    response = client.get("/flume/latent-space")
    assert response.status_code == 200
    data = response.json()
    assert "embeddings" in data
    assert isinstance(data["embeddings"], list)
    assert len(data["embeddings"]) > 0

def test_flume_latent_space_embeddings_are_3d():
    """Test that embeddings are 3D (PCA-reduced from 256D)"""
    response = client.get("/flume/latent-space")
    data = response.json()
    for point in data["embeddings"][:10]:  # Check first 10
        assert len(point) == 3  # [x, y, z]
        assert all(isinstance(coord, (int, float)) for coord in point)

def test_flume_navigate_endpoint():
    """Test that /flume/navigate accepts direction vector"""
    response = client.post("/flume/navigate", json={
        "direction": [0.1, -0.2, 0.05],
        "step_size": 0.01
    })
    assert response.status_code == 200
    data = response.json()
    assert "new_position" in data
    assert len(data["new_position"]) == 256  # Full 256D latent vector
```

**TDD Cycle**:
```bash
# 1. Write tests first (all fail)
uv run pytest tests/api/test_flume_endpoints.py -v
# EXPECTED: 4 failures (endpoints don't exist yet)

# 2. Implement minimal code to pass test 1
# src/cohezion/api/__init__.py
@app.get("/flume/latent-space")
async def get_flume_latent_space():
    return {"embeddings": []}  # Minimal pass

# 3. Run tests again
uv run pytest tests/api/test_flume_endpoints.py::test_flume_latent_space_endpoint_exists -v
# EXPECTED: 1 pass, 3 failures

# 4. Implement full logic to pass all tests
# (See implementation below)

# 5. Verify all tests pass
uv run pytest tests/api/test_flume_endpoints.py -v
# EXPECTED: 4 passes
```

**Implementation** (after tests written):

```python
# src/cohezion/api/__init__.py
from cohezion.flume.vae import get_flume_vae_trainer
from sklearn.decomposition import PCA
import numpy as np

@app.get("/flume/latent-space")
async def get_flume_latent_space():
    """Get 3D projection of FLUME 256D latent space (PCA-reduced)"""
    try:
        vae = get_flume_vae_trainer()

        # Get all latent embeddings (256D)
        embeddings_256d = vae.get_all_embeddings()  # Shape: (N, 256)

        # Reduce to 3D via PCA for visualization
        pca = PCA(n_components=3)
        embeddings_3d = pca.fit_transform(embeddings_256d)

        # Convert to list for JSON serialization
        embeddings_list = embeddings_3d.tolist()

        return {
            "embeddings": embeddings_list,
            "variance_explained": pca.explained_variance_ratio_.tolist(),
            "total_points": len(embeddings_list)
        }
    except Exception as e:
        logger.error(f"FLUME latent space error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flume/navigate")
async def flume_navigate(request: dict):
    """Navigate FLUME latent space in specified direction"""
    try:
        direction = np.array(request["direction"])  # 3D direction vector
        step_size = request.get("step_size", 0.01)

        vae = get_flume_vae_trainer()

        # Get current position (last embedding)
        current_pos = vae.get_current_position()  # 256D

        # Project direction from 3D to 256D (inverse PCA)
        # For now, simple interpolation (TODO: proper inverse PCA)
        new_pos = current_pos + (direction * step_size)

        # Decode to verify valid latent space position
        decoded = vae.decode(new_pos)

        return {
            "new_position": new_pos.tolist(),
            "decoded_sample": decoded[:100]  # First 100 chars for preview
        }
    except Exception as e:
        logger.error(f"FLUME navigate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Step 2: Frontend Component with React Testing Library (2-3 hours)

**TDD for React Component**:

```typescript
// src/web/anima_dashboard/src/components/__tests__/FlumeNavigator.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FlumeNavigator } from '../FlumeNavigator'
import { vi } from 'vitest'

describe('FlumeNavigator', () => {
  beforeEach(() => {
    // Mock fetch for API calls
    global.fetch = vi.fn()
  })

  test('renders 3D canvas', () => {
    render(<FlumeNavigator />)
    const canvas = screen.getByRole('figure') // Canvas wrapped in figure
    expect(canvas).toBeInTheDocument()
  })

  test('fetches latent space embeddings on mount', async () => {
    const mockEmbeddings = {
      embeddings: [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
      variance_explained: [0.6, 0.3, 0.1],
      total_points: 2
    }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockEmbeddings
    })

    render(<FlumeNavigator />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/flume/latent-space')
    })
  })

  test('renders point cloud from embeddings', async () => {
    const mockEmbeddings = {
      embeddings: [[0, 0, 0], [1, 1, 1]],
      variance_explained: [0.6, 0.3, 0.1],
      total_points: 2
    }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockEmbeddings
    })

    render(<FlumeNavigator />)

    await waitFor(() => {
      // Check that Three.js points rendered (via snapshot or data-testid)
      const sceneInfo = screen.getByTestId('scene-info')
      expect(sceneInfo).toHaveTextContent('2 points')
    })
  })

  test('navigates on click', async () => {
    // Mock initial embeddings
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ embeddings: [[0, 0, 0]], total_points: 1 })
    })

    // Mock navigate response
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ new_position: [0.1, 0.1, 0.1] })
    })

    render(<FlumeNavigator />)

    const canvas = screen.getByRole('figure')
    fireEvent.click(canvas, { clientX: 100, clientY: 100 })

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/flume/navigate',
        expect.objectContaining({ method: 'POST' })
      )
    })
  })
})
```

**Implementation** (after tests):

```typescript
// src/web/anima_dashboard/src/components/FlumeNavigator.tsx
import { useEffect, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

interface Embedding {
  embeddings: number[][]
  variance_explained: number[]
  total_points: number
}

function PointCloud({ positions }: { positions: Float32Array }) {
  const pointsRef = useRef<THREE.Points>(null)

  useFrame(() => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += 0.001 // Slow rotation
    }
  })

  return (
    <Points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <PointMaterial
        size={0.05}
        color="#00ffff"
        sizeAttenuation
        transparent
        opacity={0.8}
      />
    </Points>
  )
}

export function FlumeNavigator() {
  const [embeddings, setEmbeddings] = useState<number[][]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchEmbeddings() {
      try {
        const res = await fetch('/api/flume/latent-space')
        if (!res.ok) throw new Error('Failed to fetch embeddings')
        const data: Embedding = await res.json()
        setEmbeddings(data.embeddings)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchEmbeddings()
  }, [])

  const handleNavigate = async (direction: number[]) => {
    try {
      const res = await fetch('/api/flume/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, step_size: 0.01 })
      })
      const data = await res.json()
      console.log('Navigated to:', data.new_position)
      // TODO: Update visualization with new position
    } catch (err) {
      console.error('Navigate failed:', err)
    }
  }

  if (loading) return <div>Loading FLUME latent space...</div>
  if (error) return <div>Error: {error}</div>
  if (embeddings.length === 0) return <div>No embeddings found</div>

  // Convert embeddings to Float32Array for Three.js
  const positions = new Float32Array(embeddings.flat())

  return (
    <div className="w-full h-screen">
      <div data-testid="scene-info" className="absolute top-4 left-4 text-white z-10">
        {embeddings.length} points in 256D latent space (PCA → 3D)
      </div>

      <Canvas camera={{ position: [5, 5, 5], fov: 75 }} role="figure">
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <PointCloud positions={positions} />
        <OrbitControls />
      </Canvas>
    </div>
  )
}
```

#### Step 3: Multi-Agent Adversarial Review (1 hour)

**Use Cohezion's Existing Tools**:

```bash
# Run adversarial code review with multi-agent swarm
/bmad-bmm-code-review --files src/cohezion/api/__init__.py,src/web/anima_dashboard/src/components/FlumeNavigator.tsx

# Expected output:
# - Architect perspective: API design, separation of concerns
# - Engineer perspective: Performance, error handling, edge cases
# - QA perspective: Test coverage, integration testing gaps
# - Security perspective: Input validation, rate limiting
# - Biologist perspective: (may skip for non-domain code)
```

**Review Findings Example**:

```yaml
# Stored in SurrealDB via graph tracer
review:
  component: "FLUME latent space API"
  reviewers: [architect, engineer, qa, security]
  findings:
    - severity: medium
      reviewer: architect
      issue: "PCA computed on every request (expensive)"
      recommendation: "Cache PCA model, recompute only when embeddings change"
    - severity: high
      reviewer: security
      issue: "No rate limiting on /flume/navigate endpoint"
      recommendation: "Add rate limiting (10 requests/minute per IP)"
    - severity: low
      reviewer: qa
      issue: "No integration test for PCA dimensionality reduction"
      recommendation: "Add test: verify 256D → 3D preserves relative distances"
  resolution:
    - Applied PCA caching (see commit abc123)
    - Added rate limiting middleware (see commit def456)
    - Added integration test (see tests/api/test_flume_pca.py)
```

#### Step 4: Graph Traceability (30 minutes)

**Log All Decisions to SurrealDB**:

```python
# After implementation complete, log to knowledge graph
from cohezion.persistence.surreal_logger import log_implementation

log_implementation(
    component="flume-latent-space-api",
    description="3D latent space visualization API endpoint",
    decisions=[
        {
            "question": "How to reduce 256D to 3D for browser rendering?",
            "options": ["PCA", "t-SNE", "UMAP"],
            "chosen": "PCA",
            "rationale": "Deterministic, fast (<100ms), preserves global structure"
        },
        {
            "question": "Cache PCA model or compute on-demand?",
            "options": ["cache", "on-demand"],
            "chosen": "cache",
            "rationale": "Adversarial review (Architect) flagged performance issue"
        }
    ],
    tests=[
        "tests/api/test_flume_endpoints.py::test_flume_latent_space_returns_embeddings",
        "tests/api/test_flume_endpoints.py::test_flume_latent_space_embeddings_are_3d",
        "tests/api/test_flume_pca.py::test_pca_preserves_relative_distances"
    ],
    review_findings=[
        "Medium: Cache PCA model (resolved)",
        "High: Add rate limiting (resolved)",
        "Low: Add integration test (resolved)"
    ],
    deployment_status="deployed to cohezion.duckdns.org",
    links={
        "blog_post": "BLOG_POST_FLUME_VAE.md",
        "demo_url": "https://cohezion.duckdns.org/demos/flume",
        "tests": "tests/api/test_flume_endpoints.py"
    }
)
```

**Queryable Traceability**:

```python
# Later: Query why decision was made
from cohezion.persistence.surreal_logger import query_decision

result = query_decision("Why did we use PCA instead of t-SNE?")
# Returns: "Deterministic, fast (<100ms), preserves global structure.
#          Decision made during flume-latent-space-api implementation,
#          reviewed by Architect agent."
```

#### Step 5: Deploy to cohezion.duckdns.org (1 hour)

**Update Caddy Configuration**:

```bash
# Edit /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile

# Add these routes:
cohezion.duckdns.org {
    # Portfolio landing page
    handle / {
        reverse_proxy localhost:3000
    }

    # Portfolio static assets
    handle /demos/* {
        reverse_proxy localhost:3000
    }

    # API endpoints
    handle /api/* {
        reverse_proxy localhost:8080
    }

    # WebSocket (for future swarm demo)
    handle /ws/* {
        reverse_proxy localhost:8080
    }

    # Existing MCP server (keep on subdomain or different port)
    # (Move MCP to vault.cohezion.duckdns.org if needed)
}

# Reload Caddy
sudo systemctl reload caddy
```

**Start Services**:

```bash
# Terminal 1: FastAPI backend
cd ~/dev/cohezion
uv run uvicorn cohezion.api:app --host 0.0.0.0 --port 8080

# Terminal 2: Next.js frontend
cd ~/dev/cohezion/src/web/anima_dashboard
bun run build
bun run start  # Production mode on port 3000

# Terminal 3: Verify deployment
curl https://cohezion.duckdns.org  # Should show Next.js landing page
curl https://cohezion.duckdns.org/api/flume/latent-space  # Should return embeddings
```

### Week 1 Success Metrics

- [ ] **All tests pass**: `uv run pytest tests/api/test_flume_endpoints.py -v` (4/4 passing)
- [ ] **Frontend tests pass**: `bun test` (4/4 passing)
- [ ] **Adversarial review complete**: 3+ findings resolved
- [ ] **Graph traceability**: All decisions logged to SurrealDB
- [ ] **Deployed**: https://cohezion.duckdns.org/demos/flume loads in <30 seconds
- [ ] **Blog post drafted**: "From Git Commits to Latent Continua" (500-800 words)

---

## Phase 2: Expansion (Week 2) — All 5 Pillars

### Goal: All 5 Interactive Demos with Basic Functionality

**Apply Same Compound Engineering Pattern to Each Pillar**:

#### Pillar 2: Compound Loop Dashboard

**TDD Cycle**:
```python
# tests/api/test_compound_metrics.py
def test_compound_metrics_endpoint():
    response = client.get("/compound/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "coherence_trend" in data
    assert "total_executions" in data
    assert "cache_hit_rate" in data
```

**Adversarial Review Focus**:
- Architect: Metrics aggregation strategy (real-time vs cached?)
- Engineer: Query performance on SurrealDB (index optimization)
- QA: Data accuracy (compare manual count vs API response)

**Graph Traceability**:
```python
log_implementation(
    component="compound-metrics-dashboard",
    decisions=[{
        "question": "Real-time metrics or cached snapshot?",
        "chosen": "5-second cache",
        "rationale": "QA flagged: real-time queries slow for 55 sessions of data"
    }]
)
```

#### Pillar 3: Universe Simulation

**TDD Cycle**:
```python
# tests/api/test_universe_endpoints.py
def test_universe_simulate_endpoint():
    response = client.post("/universe/simulate", json={
        "initial_state": {dim: 0.5 for dim in range(12)}
    })
    assert response.status_code == 200
    data = response.json()
    assert "trajectory" in data
    assert len(data["trajectory"]) > 0
    assert data["trajectory"][0]["coherence"] >= 0.0
```

**Adversarial Review Focus**:
- Architect: 12D → 3D projection algorithm (PCA vs t-SNE for trajectory visualization)
- Engineer: Simulation performance (how many steps per second?)
- Security: Input validation (12D state vector sanitization)

#### Pillar 4: Multi-Agent Swarm

**TDD Cycle**:
```python
# tests/api/test_swarm_endpoints.py
def test_swarm_execute_endpoint():
    response = client.post("/swarm/execute", json={
        "query": "Explain FLUME VAE architecture"
    })
    assert response.status_code == 200
    data = response.json()
    assert "agent_responses" in data
    assert len(data["agent_responses"]) == 5  # 5 specialist agents
```

**WebSocket for Live Stream**:
```python
# tests/api/test_swarm_websocket.py
def test_agent_stream_websocket():
    with client.websocket_connect("/ws/agent-stream/test-123") as ws:
        ws.send_json({"query": "Test query"})
        data = ws.receive_json()
        assert "agent_id" in data
        assert "message" in data
```

**Adversarial Review Focus**:
- Architect: WebSocket connection management (reconnect strategy)
- Engineer: Concurrency (can handle 10 simultaneous debates?)
- Security: Rate limiting on WebSocket (prevent abuse)

#### Pillar 5: Evaluation Infrastructure

**TDD Cycle**:
```python
# tests/api/test_evaluation_endpoints.py
def test_trajectories_endpoint():
    response = client.get("/evaluation/trajectories")
    assert response.status_code == 200
    data = response.json()
    assert "successful" in data
    assert "failed" in data
    assert len(data["successful"]) > 0
```

**Adversarial Review Focus**:
- Architect: Trajectory storage format (JSONL vs Parquet for large datasets)
- QA: Statistical validity (are success/failure gates correctly labeled?)
- Engineer: Query optimization (filtering 1000+ trajectories)

### Week 2 Success Metrics

- [ ] **All 5 pillars have passing tests**: >20 tests total across all endpoints
- [ ] **Each pillar adversarially reviewed**: 15+ findings (3 per pillar) resolved
- [ ] **All decisions logged**: 15+ decision nodes in SurrealDB graph
- [ ] **Landing page live**: 5 pillar cards clickable, routing to demos
- [ ] **Blog posts drafted**: 5 total (500-800 words each)

---

## Phase 3: Integration (Week 3) — Live Backend Connection

### Goal: Real Data, Not Mocks

**Key Integration Points**:

1. **FLUME VAE**: Use actual trained checkpoint (not random embeddings)
2. **Compound Metrics**: Query SurrealDB for real execution history (55 sessions)
3. **Universe Simulation**: Run actual physics engine (not mock state transitions)
4. **Swarm**: Trigger real Ollama models (not hardcoded responses)
5. **Evaluation**: Load real RL trajectories from `data/rl/`

**TDD for Integration Tests**:

```python
# tests/integration/test_live_backend.py
import pytest

@pytest.mark.integration
def test_flume_uses_real_checkpoint():
    """Verify FLUME endpoint uses actual VAE checkpoint, not mock data"""
    response = client.get("/flume/latent-space")
    data = response.json()

    # Real checkpoint should have >100 embeddings (mock had 2)
    assert len(data["embeddings"]) > 100

    # Real PCA should explain >80% variance in first 3 components
    variance = sum(data["variance_explained"])
    assert variance > 0.8

@pytest.mark.integration
def test_compound_metrics_from_surrealdb():
    """Verify metrics come from SurrealDB, not mock data"""
    response = client.get("/compound/metrics")
    data = response.json()

    # Real data: 55 sessions executed
    assert data["total_executions"] >= 55

    # Coherence trend should be ascending (compound improvement)
    coherence_values = [point["coherence"] for point in data["coherence_trend"]]
    assert coherence_values[-1] > coherence_values[0]  # Last > first

@pytest.mark.integration
def test_swarm_calls_ollama():
    """Verify swarm uses real Ollama models, not mock responses"""
    import time
    start = time.time()

    response = client.post("/swarm/execute", json={
        "query": "What is the HIHO threshold?"
    })

    elapsed = time.time() - start

    # Real Ollama call takes >1 second (mock returns instantly)
    assert elapsed > 1.0

    data = response.json()
    # Real response should mention "50%" (HIHO threshold)
    assert "50" in str(data["agent_responses"])
```

**Graceful Degradation Tests**:

```python
# tests/integration/test_backend_offline.py
@pytest.mark.integration
def test_flume_fallback_when_vae_unavailable():
    """If FLUME VAE fails to load, show friendly error (don't crash)"""
    # Simulate VAE unavailable
    with patch("cohezion.flume.vae.get_flume_vae_trainer", side_effect=FileNotFoundError):
        response = client.get("/flume/latent-space")
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert "FLUME VAE checkpoint not found" in data["detail"]

@pytest.mark.integration
def test_surrealdb_offline_fallback():
    """If SurrealDB offline, metrics endpoint returns cached snapshot"""
    # Simulate SurrealDB offline
    with patch("cohezion.persistence.surreal_client.get_client", side_effect=ConnectionError):
        response = client.get("/compound/metrics")
        assert response.status_code == 200  # Still returns data
        data = response.json()
        assert "cached" in data  # Flag indicating fallback mode
```

### Week 3 Success Metrics

- [ ] **All integration tests pass**: >10 tests verifying real backend
- [ ] **Graceful degradation**: 5+ fallback tests pass (backend offline scenarios)
- [ ] **Performance**: All API endpoints <500ms (p95) under real load
- [ ] **Live demo works**: User can interact with real FLUME VAE, swarm, universe
- [ ] **Adversarial integration review**: 5+ findings (cross-component issues)

---

## Phase 4: Polish & Launch (Week 4) — Anthropic Ready

### Goal: Production-Quality Portfolio

**Compound Engineering for Polish**:

#### Visual Quality Review (Multi-Agent)

```bash
# Run design review with swarm
/bmad-editorial-review-structure --files src/web/anima_dashboard/src/app/page.tsx

# Expected perspectives:
# - UX Designer: Navigation clarity, information hierarchy
# - Accessibility Expert: WCAG AA compliance, screen reader support
# - Performance Engineer: Lighthouse score, bundle size
# - Content Editor: Copy clarity, technical jargon reduction
```

**TDD for Accessibility**:

```typescript
// tests/accessibility/test_wcag.test.tsx
import { axe, toHaveNoViolations } from 'jest-axe'
expect.extend(toHaveNoViolations)

test('Landing page has no WCAG violations', async () => {
  const { container } = render(<LandingPage />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})

test('All interactive elements have aria-labels', () => {
  render(<LandingPage />)
  const buttons = screen.getAllByRole('button')
  buttons.forEach(button => {
    expect(button).toHaveAttribute('aria-label')
  })
})
```

#### Content Quality Review

```bash
# Run prose review on blog posts
/bmad-editorial-review-prose --files BLOG_POST_*.md

# Expected output:
# - Clarity issues: 5 flagged (jargon, unclear sentences)
# - Engagement: 3 suggestions (add hooks, examples)
# - Technical accuracy: 2 corrections needed
```

**Graph Traceability for Content Edits**:

```python
log_implementation(
    component="blog-post-flume-vae",
    decisions=[{
        "question": "Explain PCA to general audience or assume ML knowledge?",
        "chosen": "General audience explanation",
        "rationale": "Editorial review (Content Editor): 'Anthropic recruiter may not be ML expert'"
    }]
)
```

#### CI/CD Pipeline (TDD for Deployment)

```yaml
# .github/workflows/portfolio-deploy.yml
name: Portfolio Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Backend tests
      - name: Run Python tests
        run: |
          uv pip install -e .
          uv run pytest tests/ -q

      # Frontend tests
      - name: Run TypeScript tests
        run: |
          cd src/web/anima_dashboard
          bun install
          bun test

      # Accessibility tests
      - name: Run axe accessibility tests
        run: |
          cd src/web/anima_dashboard
          bun test:a11y

      # Lighthouse performance
      - name: Run Lighthouse CI
        run: |
          npm install -g @lhci/cli
          lhci autorun --collect.url=http://localhost:3000

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Vercel
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

**Test the CI/CD**:

```bash
# Run CI locally before pushing
act -j test  # Uses nektos/act to simulate GitHub Actions

# Expected: All tests pass locally before pushing
```

### Week 4 Success Metrics

- [ ] **All CI/CD tests pass**: Lint, test, build, deploy pipeline green
- [ ] **Lighthouse score >90**: Performance, accessibility, best practices, SEO
- [ ] **Zero WCAG violations**: axe DevTools audit passes
- [ ] **Blog posts polished**: 5 posts reviewed, edited, final version published
- [ ] **Domain live**: cohezion.duckdns.org (or cohezion.dev) publicly accessible
- [ ] **Anthropic materials ready**: Resume, cover letter, LinkedIn updated with portfolio URL

---

## Compound Engineering Advantages (Why This Approach?)

### Traditional Portfolio Approach:
```
Build feature → Hope it works → Fix bugs later → No review → Deploy → Move on
```
**Result**: Technical debt, unclear decisions, hard to maintain

### Compound Engineering Approach:
```
Write tests → Implement → Multi-agent review → Log decisions → Deploy → Extract patterns
```
**Result**: Each feature improves the system for next feature

### Concrete Examples:

#### Example 1: PCA Caching Decision

**Without Compound Engineering**:
- Implement PCA on every request (slow)
- User complains → investigate → refactor
- No record of why original approach was chosen
- Same mistake repeated in Universe demo (t-SNE on every request)

**With Compound Engineering**:
1. **TDD**: Performance test fails (>500ms response time)
2. **Adversarial review**: Architect flags caching opportunity
3. **Implementation**: Add PCA caching
4. **Graph log**: Decision recorded ("Why cache PCA?")
5. **Pattern extraction**: "Expensive ML computations should be cached"
6. **Compound benefit**: Universe demo uses same caching pattern (learned from FLUME)

#### Example 2: WebSocket Rate Limiting

**Without Compound Engineering**:
- Implement WebSocket endpoint
- Abuse discovered in production → emergency patch
- No documentation of attack vector

**With Compound Engineering**:
1. **TDD**: Rate limiting test written (10 requests/minute)
2. **Adversarial review**: Security agent flags abuse vector
3. **Implementation**: Add rate limiting middleware
4. **Graph log**: Decision + rationale recorded
5. **Pattern extraction**: "All WebSocket endpoints need rate limiting"
6. **Compound benefit**: Future MCP server uses same rate limiting (no discovery needed)

---

## Graph Traceability Schema

**SurrealDB Schema for Full Traceability**:

```sql
-- Nodes
DEFINE TABLE implementation SCHEMAFULL;
DEFINE FIELD component ON implementation TYPE string;
DEFINE FIELD description ON implementation TYPE string;
DEFINE FIELD timestamp ON implementation TYPE datetime;
DEFINE FIELD developer ON implementation TYPE string;

DEFINE TABLE decision SCHEMAFULL;
DEFINE FIELD question ON decision TYPE string;
DEFINE FIELD options ON decision TYPE array;
DEFINE FIELD chosen ON decision TYPE string;
DEFINE FIELD rationale ON decision TYPE string;

DEFINE TABLE test SCHEMAFULL;
DEFINE FIELD test_path ON test TYPE string;
DEFINE FIELD test_name ON test TYPE string;
DEFINE FIELD status ON test TYPE string; -- passing/failing

DEFINE TABLE review_finding SCHEMAFULL;
DEFINE FIELD severity ON review_finding TYPE string; -- low/medium/high
DEFINE FIELD reviewer ON review_finding TYPE string; -- architect/engineer/qa/security
DEFINE FIELD issue ON review_finding TYPE string;
DEFINE FIELD recommendation ON review_finding TYPE string;
DEFINE FIELD resolved ON review_finding TYPE bool;

-- Edges
DEFINE TABLE made_decision SCHEMAFULL;
DEFINE FIELD in ON made_decision TYPE record(implementation);
DEFINE FIELD out ON made_decision TYPE record(decision);

DEFINE TABLE has_test SCHEMAFULL;
DEFINE FIELD in ON has_test TYPE record(implementation);
DEFINE FIELD out ON has_test TYPE record(test);

DEFINE TABLE received_review SCHEMAFULL;
DEFINE FIELD in ON received_review TYPE record(implementation);
DEFINE FIELD out ON received_review TYPE record(review_finding);

DEFINE TABLE influenced SCHEMAFULL;
DEFINE FIELD in ON influenced TYPE record(implementation);
DEFINE FIELD out ON influenced TYPE record(implementation);
DEFINE FIELD reason ON influenced TYPE string; -- "Used caching pattern from X"
```

**Query Examples**:

```sql
-- Query 1: Why was PCA caching chosen?
SELECT * FROM decision WHERE question CONTAINS 'PCA';

-- Query 2: What tests cover FLUME latent space?
SELECT ->has_test->test.* FROM implementation
WHERE component = 'flume-latent-space-api';

-- Query 3: Which components influenced Universe demo?
SELECT <-influenced<-implementation.* FROM implementation
WHERE component = 'universe-simulation';

-- Query 4: What security findings were resolved?
SELECT * FROM review_finding
WHERE reviewer = 'security' AND resolved = true;

-- Query 5: Implementation timeline (compound progression)
SELECT component, timestamp FROM implementation
ORDER BY timestamp ASC;
```

---

## Success Metrics Dashboard (Queryable via SurrealDB)

```python
# scripts/portfolio_metrics.py
from cohezion.persistence.surreal_logger import query

def get_portfolio_metrics():
    """Query all portfolio implementation metrics"""

    # Total implementations
    total_implementations = query("SELECT count() FROM implementation GROUP ALL")[0]["count"]

    # Total decisions logged
    total_decisions = query("SELECT count() FROM decision GROUP ALL")[0]["count"]

    # Test coverage
    total_tests = query("SELECT count() FROM test WHERE status = 'passing' GROUP ALL")[0]["count"]

    # Review findings resolved
    resolved_findings = query("""
        SELECT count() FROM review_finding
        WHERE resolved = true
        GROUP ALL
    """)[0]["count"]

    # Compound progression (each implementation references prior)
    compound_links = query("SELECT count() FROM influenced GROUP ALL")[0]["count"]

    return {
        "total_implementations": total_implementations,
        "total_decisions": total_decisions,
        "passing_tests": total_tests,
        "resolved_findings": resolved_findings,
        "compound_links": compound_links,
        "compound_score": compound_links / max(total_implementations - 1, 1)  # Ratio
    }

# Example output:
# {
#   "total_implementations": 5,  # 5 pillars
#   "total_decisions": 23,       # 4-5 decisions per pillar
#   "passing_tests": 34,         # >30 tests across all pillars
#   "resolved_findings": 18,     # 3-4 findings per pillar
#   "compound_links": 12,        # Each pillar references 2-3 prior implementations
#   "compound_score": 3.0        # Average 3 links per implementation (strong compounding)
# }
```

**Display on Landing Page**:

```typescript
// src/web/anima_dashboard/src/components/CompoundMetrics.tsx
export function CompoundMetrics() {
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    fetch('/api/portfolio/metrics').then(r => r.json()).then(setMetrics)
  }, [])

  if (!metrics) return <div>Loading metrics...</div>

  return (
    <div className="grid grid-cols-3 gap-4">
      <MetricCard
        title="Implementations"
        value={metrics.total_implementations}
        subtitle="5 portfolio pillars"
      />
      <MetricCard
        title="Tests Passing"
        value={metrics.passing_tests}
        subtitle="TDD coverage"
      />
      <MetricCard
        title="Compound Score"
        value={metrics.compound_score.toFixed(1)}
        subtitle="Avg reuse per feature"
      />
    </div>
  )
}
```

---

## Final Deliverables (Week 4 Complete)

### Code Artifacts

- [ ] **5 interactive demos** (FLUME, Compound, Universe, Swarm, Evaluation)
- [ ] **34+ tests** (TDD coverage across all components)
- [ ] **18+ resolved review findings** (multi-agent adversarial review)
- [ ] **23+ decisions logged** (SurrealDB graph traceability)
- [ ] **CI/CD pipeline** (GitHub Actions: lint → test → deploy)

### Content Artifacts

- [ ] **5 blog posts** (500-800 words each, polished)
- [ ] **Landing page** (30-second pitch, 5 pillar cards)
- [ ] **README.md** (portfolio overview, setup instructions)
- [ ] **Portfolio metrics dashboard** (compound score, test coverage)

### Deployment Artifacts

- [ ] **Live URL**: https://cohezion.duckdns.org (or cohezion.dev)
- [ ] **HTTPS enabled**: Let's Encrypt certificate
- [ ] **<30 second load time**: Lighthouse performance >90
- [ ] **Mobile responsive**: Works on phone, tablet, desktop

### Traceability Artifacts

- [ ] **SurrealDB graph**: 5 implementation nodes + 23 decision nodes + 18 finding nodes
- [ ] **Queryable history**: "Why did we choose X?" → answer in <1 second
- [ ] **Compound links**: Each implementation references 2-3 prior implementations

### Anthropic Application Artifacts

- [ ] **Resume**: Portfolio URL prominently displayed
- [ ] **Cover letter**: Mentions 3 key demos (FLUME, Universe, Swarm)
- [ ] **LinkedIn**: Portfolio link in headline + featured section
- [ ] **Email to recruiter**: Portfolio + 30-second pitch

---

## Why This Approach Positions You for Anthropic

### Traditional Portfolio Shows:
- "I can code"
- Static demos
- Claimed skills (not proven)

### Compound Engineering Portfolio Shows:
- **How you build**: TDD → review → trace → deploy
- **How you improve**: Each feature compounds (learning captured)
- **How you think**: Decisions logged with rationale (queryable)
- **How you collaborate**: Multi-agent review (diverse perspectives)
- **How you ensure quality**: 34+ tests, adversarial review, CI/CD

### Anthropic Universes Team Values (Inferred):
1. **Research rigor**: TDD + integration tests = reproducibility
2. **Scalable systems**: Compound engineering = each feature improves infrastructure
3. **Safety-first**: Adversarial review = find issues before deployment
4. **Transparent AI**: Graph traceability = every decision auditable
5. **Collaborative**: Multi-agent review = diverse perspectives considered

**Your Portfolio Demonstrates All 5 Values** (not just talks about them).

---

## Next Immediate Steps (Start Now)

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Install bun and verify Next.js dashboard works", "status": "in_progress", "activeForm": "Installing bun and verifying Next.js dashboard"}, {"content": "Implement FLUME latent space API endpoint with TDD", "status": "pending", "activeForm": "Implementing FLUME latent space API endpoint with TDD"}, {"content": "Build FlumeNavigator.tsx component (3D visualization)", "status": "pending", "activeForm": "Building FlumeNavigator.tsx component"}, {"content": "Deploy to cohezion.duckdns.org with Caddy reverse proxy", "status": "pending", "activeForm": "Deploying to cohezion.duckdns.org"}, {"content": "Run adversarial review via bmad-bmm-code-review", "status": "pending", "activeForm": "Running adversarial review"}, {"content": "Write blog post: 'From Git Commits to Latent Continua'", "status": "pending", "activeForm": "Writing blog post"}, {"content": "Log implementation to SurrealDB knowledge graph (traceability)", "status": "pending", "activeForm": "Logging implementation to SurrealDB knowledge graph"}]