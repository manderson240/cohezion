# Portfolio Deployment & Packaging Plan

**Target Role**: Research Engineer, Universes @ Anthropic
**Goal**: "Living portfolio" showcasing Cohezion's universe simulation, compound engineering, and multi-agent orchestration capabilities
**Date**: 2026-03-22

---

## Executive Summary

Transform existing `src/web/anima_dashboard/` into a production-ready **living portfolio** that:

1. **Showcases 5 portfolio pillars** (FLUME, Compound Loop, RL Environment, Swarm, Evaluation) in integrated webapp
2. **Deploys in <30 seconds** via modern packaging (recommended: **bun** for speed, **npm** for compatibility)
3. **Integrates with live Cohezion backend** (FastAPI + SurrealDB) for real-time demonstrations
4. **Positions for Anthropic Universes team** with interactive universe simulation visualization

**Recommended Stack**:

- **Frontend**: Next.js 16 (existing) + React 19 + Three.js (3D universe viz)
- **Backend**: FastAPI (existing, port 8080) + SurrealDB 3.0
- **Packaging**: **bun** (primary), npm (fallback) — **NOT npx** (npx is for one-off commands, not deployment)
- **Deployment**: **Vercel** (web) + **Tauri** (optional desktop app)
- **CI/CD**: GitHub Actions (lint → test → deploy on push)

---

## Part 1: Modern Packaging Strategy

### npm vs npx vs bun — What to Use When

| Tool    | Purpose                         | When to Use                                                 | Cohezion Usage             |
| ------- | ------------------------------- | ----------------------------------------------------------- | -------------------------- |
| **npm** | Package manager (traditional)   | Installing dependencies, running scripts                    | ✅ Current (fallback)      |
| **npx** | One-off command execution       | Running tools without install (e.g., `npx create-next-app`) | ❌ Not for deployment      |
| **bun** | Modern npm alternative (faster) | Development + production builds (2-10x faster than npm)     | ✅ **Recommended primary** |
| **uv**  | Python package manager          | Backend Python dependencies only                            | ✅ Already used            |

### Recommendation: **bun as Primary, npm as Fallback**

**Why bun?**

- **2-10x faster** than npm for installs/builds (critical for "launch in <30 seconds" goal)
- **Drop-in replacement** for npm (uses same `package.json`, no migration needed)
- **Built-in test runner** (could replace Playwright setup in future)
- **Single binary** (easy to install: `curl -fsSL https://bun.sh/install | bash`)

**Why keep npm?**

- **Compatibility fallback** (bun not available on all systems)
- **Lock file compatibility** (`package-lock.json` already exists)
- **CI/CD standardization** (GitHub Actions runners have npm pre-installed)

**Migration Path**:

```bash
# Install bun (one-time)
curl -fsSL https://bun.sh/install | bash

# Test existing dashboard with bun (zero code changes)
cd src/web/anima_dashboard
bun install  # Uses existing package.json, creates bun.lockb
bun run dev  # Should work identically to npm run dev

# Benchmark speed improvement
time npm install  # Baseline
time bun install  # Compare (expect 2-10x faster)
```

**package.json scripts stay identical** (bun reads npm scripts):

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

**Deployment scripts** (dual support):

```bash
# Try bun first, fallback to npm
command -v bun >/dev/null 2>&1 && bun install || npm install
command -v bun >/dev/null 2>&1 && bun run build || npm run build
```

---

## Part 2: "Living Portfolio" Architecture

### What Makes a Portfolio "Living"?

**Static Portfolio** (what NOT to build):

- PDF resume
- Screenshots of dashboards
- Pre-recorded demo videos
- Dead links to old projects

**Living Portfolio** (what TO build):

- **Interactive demos** user can explore in real-time
- **Live metrics** from actual Cohezion backend (not mocked data)
- **3D universe visualization** showing current simulation state
- **Real-time updates** (WebSocket for agent execution streams)
- **One-click deployment** to try full system locally

### Architecture: Frontend + Backend Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    LIVING PORTFOLIO WEBAPP                   │
│                  (src/web/anima_dashboard/)                  │
├─────────────────────────────────────────────────────────────┤
│  Next.js 16 Frontend (Port 3000)                            │
│  ├─ Landing Page: 5 Portfolio Pillars (cards)               │
│  ├─ FLUME Navigator: Interactive latent space (Three.js)    │
│  ├─ Compound Loop Dashboard: Real-time metrics (Plotly)     │
│  ├─ Universe Simulator: 12D manifold viz (React-Three)      │
│  ├─ Swarm Orchestrator: Agent execution live stream         │
│  └─ Evaluation Suite: Trajectory plots + coherence gates    │
├─────────────────────────────────────────────────────────────┤
│  Integration Layer (WebSocket + REST)                       │
│  ├─ WebSocket: /ws/agent-stream (live execution updates)    │
│  ├─ REST API: /api/flume/* (latent space queries)           │
│  ├─ REST API: /api/universe/* (simulation state)            │
│  └─ REST API: /api/metrics/* (compound loop stats)          │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8080) — EXISTING                     │
│  ├─ 72 endpoints (already implemented)                      │
│  ├─ FLUME VAE trainer (256D latent space)                   │
│  ├─ Compound executor (11-step pipeline)                    │
│  ├─ Swarm orchestrator (5 specialist agents)                │
│  └─ Universe engine (12D manifold + RL environment)         │
├─────────────────────────────────────────────────────────────┤
│  SurrealDB 3.0 (Port 8000) — EXISTING                       │
│  ├─ Journey tracking (agent execution logs)                 │
│  ├─ Metrics aggregation (cost, coherence, cache hits)       │
│  └─ Artifact metadata (checkpoints, experiments)            │
└─────────────────────────────────────────────────────────────┘
```

### Key Technical Decisions

**1. Frontend-Backend Communication**:

- **REST API for queries** (`fetch('/api/flume/latent-space')`)
- **WebSocket for live streams** (agent execution, metrics updates)
- **Server-Sent Events (SSE) alternative** if WebSocket too complex initially

**2. Data Freshness**:

- **Real-time**: Agent execution streams (WebSocket)
- **5-second polling**: Metrics dashboard (REST API + `setInterval`)
- **On-demand**: FLUME latent space navigation (user-triggered REST calls)
- **Static**: Blog posts, research artifacts (Markdown → HTML at build time)

**3. 3D Visualization Strategy**:

- **Three.js + React-Three-Fiber** (already in dependencies)
- **12D → 3D projection**: PCA/t-SNE to collapse dimensions for browser rendering
- **Interactive controls**: OrbitControls for camera, dat.GUI for parameter tweaks
- **Performance**: Throttle updates to 30 FPS, limit particles to 10K max

---

## Part 3: Deployment Strategy

### Web Deployment: **Vercel** (Recommended)

**Why Vercel?**

- **Next.js creators** (zero-config deployment)
- **Edge network** (global CDN, <100ms latency)
- **Free tier**: Sufficient for portfolio (100 GB bandwidth/month)
- **GitHub integration**: Auto-deploy on push to main
- **Environment variables**: Secure API key management
- **Custom domain**: Free HTTPS + domain support

**Setup** (5 minutes):

```bash
# 1. Install Vercel CLI
npm i -g vercel  # or: bun add -g vercel

# 2. Deploy from dashboard directory
cd src/web/anima_dashboard
vercel  # Follow prompts (link to GitHub repo)

# 3. Configure environment variables
vercel env add BACKEND_API_URL production  # https://api.cohezion.dev
vercel env add SURREALDB_URL production    # wss://db.cohezion.dev

# 4. Deploy
vercel --prod  # Deploys to cohezion-portfolio.vercel.app
```

**Custom Domain** (optional, $10/year):

```bash
# Buy domain (e.g., cohezion.dev via Namecheap)
# Add domain in Vercel dashboard → DNS auto-configured
# Portfolio lives at: https://cohezion.dev
```

**Alternatives**:

- **Netlify**: Similar to Vercel, slightly slower Next.js builds
- **GitHub Pages**: Static only (no SSR), would need to eject from Next.js
- **Cloudflare Pages**: Fast edge, but Next.js support in beta

### Desktop App: **Tauri** (Optional, Recommended if Needed)

**Why Tauri?**

- **Rust-based** (50x smaller than Electron, 4 MB vs 200 MB)
- **System webview** (uses OS browser, not bundled Chromium)
- **Security-first** (no Node.js backend, all IPC sandboxed)
- **Cross-platform**: macOS, Windows, Linux from single codebase

**When to Use Desktop App?**

- User wants **offline demo** (e.g., on laptop at conference)
- Backend integration requires **local SurrealDB** (not web-accessible)
- Showcase requires **filesystem access** (e.g., loading checkpoint files)

**Setup** (if needed, 30 minutes):

```bash
# 1. Install Tauri CLI
cargo install tauri-cli  # Requires Rust (already on Strix Halo)

# 2. Initialize Tauri in dashboard
cd src/web/anima_dashboard
cargo tauri init
# Follow prompts:
# - App name: Cohezion Portfolio
# - Window title: Cohezion — Research Engineer Portfolio
# - Dev server: http://localhost:3000
# - Build command: bun run build
# - Dist dir: .next

# 3. Build desktop app
cargo tauri build  # Produces .dmg (macOS), .exe (Windows), .AppImage (Linux)
```

**Tauri vs Electron Comparison**:

| Feature      | Tauri          | Electron                         | Recommendation          |
| ------------ | -------------- | -------------------------------- | ----------------------- |
| Bundle size  | 4-10 MB        | 150-300 MB                       | ✅ Tauri (50x smaller)  |
| Memory usage | 50-100 MB      | 200-500 MB                       | ✅ Tauri (4x lower)     |
| Security     | Sandboxed IPC  | Node.js backend (attack surface) | ✅ Tauri                |
| Ecosystem    | Rust (smaller) | Node.js (larger)                 | ⚖️ Depends on expertise |
| Startup time | <1 sec         | 2-5 sec                          | ✅ Tauri                |

**Verdict**: Use Tauri IF desktop app needed. Otherwise, web-only (Vercel) is simpler.

---

## Part 4: Integration with Cohezion Backend

### Connecting Next.js Frontend to FastAPI Backend

**Challenge**: Next.js runs on port 3000 (dev) or static (prod), FastAPI on port 8080. How to connect?

**Solution 1: Reverse Proxy (Development)**

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8080/:path*", // Proxy to FastAPI
      },
    ];
  },
};
```

**Solution 2: Environment Variables (Production)**

```javascript
// src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function getFlumeLatentSpace() {
  const res = await fetch(`${API_BASE}/flume/latent-space`);
  return res.json();
}
```

**Solution 3: WebSocket for Live Streams**

```javascript
// src/hooks/useAgentStream.ts
import { useEffect, useState } from 'react'

export function useAgentStream(agentId: string) {
  const [events, setEvents] = useState([])

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8080/ws/agent-stream/${agentId}`)
    ws.onmessage = (event) => {
      setEvents((prev) => [...prev, JSON.parse(event.data)])
    }
    return () => ws.close()
  }, [agentId])

  return events
}
```

### Backend API Endpoints to Expose

**Required for Portfolio**:

| Endpoint                   | Method    | Purpose                                           | Portfolio Pillar          |
| -------------------------- | --------- | ------------------------------------------------- | ------------------------- |
| `/flume/latent-space`      | GET       | 256D embedding space (PCA → 3D)                   | FLUME VAE                 |
| `/flume/navigate`          | POST      | Navigate latent space (direction vector)          | FLUME VAE                 |
| `/compound/metrics`        | GET       | Compound loop stats (executions, coherence, cost) | Compound Loop             |
| `/universe/simulate`       | POST      | Run universe step, return 12D state               | Universe Simulation       |
| `/universe/state`          | GET       | Current simulation state (trajectory plot)        | Universe Simulation       |
| `/swarm/execute`           | POST      | Trigger multi-agent execution                     | Swarm Orchestration       |
| `/swarm/status`            | GET       | Agent execution status (live updates)             | Swarm Orchestration       |
| `/evaluation/trajectories` | GET       | RL trajectories (coherence gates)                 | Evaluation Infrastructure |
| `/ws/agent-stream/{id}`    | WebSocket | Live agent execution events                       | All pillars               |

**Example FastAPI WebSocket** (add to `src/cohezion/api/__init__.py`):

```python
from fastapi import WebSocket

@app.websocket("/ws/agent-stream/{agent_id}")
async def agent_stream(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    # Stream agent execution events in real-time
    async for event in execution_orchestrator.stream_events(agent_id):
        await websocket.send_json({
            "timestamp": event.timestamp,
            "phase": event.phase,
            "coherence": event.coherence,
            "message": event.message
        })
```

---

## Part 5: Anthropic Alignment Strategy

### Positioning for Research Engineer, Universes Team

**Anthropic's Universes Team Focus** (from job description inference):

- Universe simulation for agent training/evaluation
- Emergent behavior in multi-agent systems
- Scalable RL environments
- Safety research through simulated worlds

**Cohezion's Unique Alignment**:

| Anthropic Need              | Cohezion Demonstration                       | Portfolio Showcase                              |
| --------------------------- | -------------------------------------------- | ----------------------------------------------- |
| **Universe simulation**     | 12D manifold engine (SPIN + FLUME + HIHO)    | Interactive 3D projection of 12D space          |
| **Agent training**          | RL environment (Gymnasium-compatible)        | Live trajectory plots with coherence gates      |
| **Multi-agent systems**     | Swarm orchestration (5 specialists + debate) | Real-time agent execution stream                |
| **Scalable infrastructure** | Compound engineering loop (self-improving)   | Metrics dashboard (cost, cache hits, coherence) |
| **Safety research**         | Constitution-governed agent behavior         | Audit trail of all agent decisions              |

### Portfolio Narrative Arc

**Landing Page** (30-second pitch):

1. **Hook**: "Self-improving AI infrastructure that learns from every execution"
2. **Problem**: "Current AI systems don't compound — each task starts from scratch"
3. **Solution**: "Cohezion's compound loop: execute → reflect → refine → repeat"
4. **Proof**: "579 modules, 4,426 tests, 99.9% pass rate — all refined through 55+ compound cycles"
5. **CTA**: "Explore 5 interactive demos below ↓"

**5 Portfolio Pillars** (each with interactive demo):

**Pillar 1: FLUME VAE** (Continuous Latent Navigation)

- **Demo**: 3D scatter plot of 256D latent space (PCA-reduced)
  - User clicks direction → FLUME navigates → plot updates in real-time
  - Shows smooth interpolation between discrete states
- **Anthropic Relevance**: Continuous state spaces for RL (vs discrete observation grids)
- **Blog Post**: "From Git Commits to Latent Continua: Training a VAE on Software Evolution"

**Pillar 2: Compound Loop** (Self-Improving Infrastructure)

- **Demo**: Live dashboard with metrics from actual Cohezion execution
  - Coherence trend line (55 sessions)
  - Cost savings over time (semantic cache impact)
  - Skill refinement count (how many times PRIME skills auto-updated)
- **Anthropic Relevance**: Infrastructure that improves with use (meta-learning)
- **Blog Post**: "Compound Engineering: How AI Infrastructure Learns to Build Itself"

**Pillar 3: Universe Simulation** (12D Manifold)

- **Demo**: Interactive universe step-through
  - User sets initial 12D state (sliders for each dimension)
  - Click "Simulate" → backend runs physics engine → plot updates
  - Shows trajectory through 12D space (projected to 3D)
- **Anthropic Relevance**: Scalable simulation environments for agent research
- **Blog Post**: "Building a 12-Dimensional Universe for Agent Training"

**Pillar 4: Multi-Agent Swarm** (Cost-Aware Orchestration)

- **Demo**: Live agent execution stream
  - User submits query → swarm routes to specialist agents
  - WebSocket shows real-time agent communication
  - Final answer synthesized from debate
- **Anthropic Relevance**: Orchestrating multiple models/agents efficiently
- **Blog Post**: "Democratic Debate: How Five AI Agents Reach Consensus"

**Pillar 5: Evaluation Infrastructure** (Trajectory-Based Assessment)

- **Demo**: RL trajectory comparison
  - Show successful vs failed coherence navigation
  - Coherence gates visualization (HIHO threshold at 50%)
  - Reward shaping impact on learning curves
- **Anthropic Relevance**: Evaluating agent behavior in continuous spaces
- **Blog Post**: "Beyond Accuracy: Evaluating Agents Through Coherence Trajectories"

### Technical Highlights to Emphasize

**For Research Engineer Role**:

- **Novel Architecture**: SPIN information theory → 12D manifold design
- **Production-Ready Code**: 99.9% test pass rate, type-hinted, CI/CD
- **Scalability**: Handled 510 K-Search cycles in 4-hour session (128 GB RAM, Ollama local models)
- **Research Rigor**: Jupyter notebooks for experiments, arXiv paper searches integrated
- **Open Source**: Full codebase available, reproducible from git clone

---

## Part 6: Implementation Roadmap

### Week 1: Foundation (8-10 hours)

**Goal**: One pillar fully functional (FLUME VAE demo)

**Tasks**:

1. ✅ **Migrate to bun** (1 hour):

   ```bash
   cd src/web/anima_dashboard
   bun install  # Creates bun.lockb
   bun run dev  # Verify works
   ```

2. **Add FLUME latent space visualization** (4 hours):
   - Create `/api/flume/latent-space` endpoint in FastAPI (return PCA-reduced embeddings)
   - Build `FlumeNavigator.tsx` component (Three.js scatter plot)
   - Add interactive controls (click direction → navigate → update)

3. **Deploy to Vercel** (1 hour):

   ```bash
   vercel --prod
   # Configure environment variables (BACKEND_API_URL)
   ```

4. **Write blog post** (2 hours):
   - "From Git Commits to Latent Continua: Training a VAE on Software Evolution"
   - Include Marimo notebook as embedded demo

5. **Test end-to-end** (1 hour):
   - User flow: Landing page → FLUME pillar → interactive demo → blog post
   - Verify <30 second load time

**Success Metric**: FLUME pillar live at cohezion-portfolio.vercel.app, interactive demo functional

### Week 2: Expansion (12-15 hours)

**Goal**: All 5 pillars with basic demos

**Tasks**:

1. **Compound Loop Dashboard** (3 hours):
   - `/api/compound/metrics` endpoint (query SurrealDB for aggregated stats)
   - Plotly time series charts (coherence trend, cost savings)
   - Blog post: "Compound Engineering: How AI Infrastructure Learns to Build Itself"

2. **Universe Simulation Demo** (4 hours):
   - `/api/universe/simulate` + `/api/universe/state` endpoints
   - React-Three-Fiber 3D trajectory visualization
   - Interactive sliders for 12D initial state
   - Blog post: "Building a 12-Dimensional Universe for Agent Training"

3. **Swarm Orchestration Demo** (3 hours):
   - WebSocket `/ws/agent-stream` endpoint
   - `useAgentStream` React hook
   - Live event feed UI (agent messages scrolling)
   - Blog post: "Democratic Debate: How Five AI Agents Reach Consensus"

4. **Evaluation Infrastructure Demo** (2 hours):
   - `/api/evaluation/trajectories` endpoint (query RL checkpoint data)
   - Plotly trajectory comparison (successful vs failed)
   - Blog post: "Beyond Accuracy: Evaluating Agents Through Coherence Trajectories"

5. **Polish landing page** (1 hour):
   - Hero section with 30-second pitch
   - 5 pillar cards (links to demos)
   - Footer: GitHub repo, contact info

**Success Metric**: All 5 demos functional, 5 blog posts drafted, <30 second total site load

### Week 3: Integration (10-12 hours)

**Goal**: Connect all demos to live Cohezion backend

**Tasks**:

1. **Backend API implementation** (6 hours):
   - Implement 9 REST endpoints listed in Part 4
   - Add WebSocket agent stream
   - Test with Postman/curl

2. **Frontend integration** (4 hours):
   - Replace mock data with real API calls
   - Add error handling (backend offline fallback)
   - Add loading states (Suspense + skeletons)

3. **Performance optimization** (2 hours):
   - Enable Next.js caching (ISR for static content)
   - Throttle WebSocket updates to 30 FPS
   - Lazy load Three.js components (reduce initial bundle)

**Success Metric**: All demos pull from live backend, graceful degradation if backend offline

### Week 4: Polish & Launch (8-10 hours)

**Goal**: Production-ready portfolio, ready to share with Anthropic

**Tasks**:

1. **Visual polish** (3 hours):
   - Consistent Tailwind theme (dark mode default)
   - Smooth transitions between pillars
   - Responsive design (mobile-friendly)
   - Accessibility audit (WCAG AA compliance)

2. **Content finalization** (2 hours):
   - Edit all 5 blog posts (technical rigor + readability)
   - Add code snippets to blog posts
   - Proofread landing page copy

3. **CI/CD setup** (2 hours):
   - GitHub Actions: lint → test → deploy on push to main
   - Playwright E2E tests for critical paths
   - Deploy preview for pull requests

4. **Custom domain** (1 hour):
   - Buy `cohezion.dev` (or similar)
   - Configure Vercel DNS
   - HTTPS auto-enabled

5. **Launch checklist** (1 hour):
   - [ ] All 5 demos load in <30 seconds
   - [ ] No console errors
   - [ ] Mobile-responsive
   - [ ] Backend integration works
   - [ ] Blog posts proofread
   - [ ] GitHub repo public (with README)
   - [ ] Custom domain live

6. **Share with Anthropic** (1 hour):
   - Email to recruiter with portfolio link
   - LinkedIn post showcasing portfolio
   - Twitter thread (if desired)

**Success Metric**: Portfolio live at cohezion.dev, ready to share with Anthropic hiring team

---

## Part 7: Success Metrics & Monitoring

### Portfolio Performance Targets

| Metric             | Target                         | Measurement                                      |
| ------------------ | ------------------------------ | ------------------------------------------------ |
| **Load time**      | <30 seconds (all 5 demos)      | Lighthouse performance score >90                 |
| **Interactivity**  | <100 ms response to user input | Chrome DevTools Performance tab                  |
| **Availability**   | 99.9% uptime                   | Vercel analytics (built-in)                      |
| **Mobile support** | Fully responsive               | Test on 3 screen sizes (mobile, tablet, desktop) |
| **Accessibility**  | WCAG AA compliance             | axe DevTools audit                               |

### Backend Integration Health

| Metric               | Target                         | Measurement                          |
| -------------------- | ------------------------------ | ------------------------------------ |
| **API latency**      | <200 ms (p95)                  | FastAPI middleware logging           |
| **WebSocket uptime** | >95% (during demo)             | Connection duration tracking         |
| **Error rate**       | <1%                            | Sentry or custom error tracking      |
| **Data freshness**   | <5 seconds (metrics dashboard) | Timestamp comparison (UI vs backend) |

### Anthropic Application Impact

**Qualitative Goals**:

- ✅ Demonstrates universe simulation expertise (12D manifold)
- ✅ Shows production engineering rigor (99.9% test pass rate)
- ✅ Proves research capability (novel SPIN architecture)
- ✅ Highlights multi-agent orchestration (swarm demos)
- ✅ Showcases compound learning (self-improving infrastructure)

**Quantitative Goals**:

- Portfolio shared with Anthropic recruiter (measurable: email sent)
- Recruiter click-through >50% (track unique visitors via Vercel analytics)
- Technical interview invitation (ultimate success metric)

---

## Part 8: Maintenance & Iteration

### Post-Launch Updates

**Monthly Updates** (2-4 hours/month):

- Add new blog post from latest research (e.g., K-Search optimization findings)
- Update metrics dashboard with latest Cohezion execution stats
- Refresh screenshots if UI changes

**Continuous Improvements**:

- Add more interactive demos as Cohezion features mature
- Integrate new pillars (e.g., if BMAD workflows become standalone pillar)
- A/B test landing page copy for clarity

### Monitoring & Alerts

**Vercel Analytics** (built-in, free):

- Track unique visitors
- Monitor page load times
- Identify bottleneck pages

**Backend Monitoring** (add to FastAPI):

```python
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    if process_time > 0.5:  # Slow request alert
        logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}s")
    return response
```

---

## Part 9: Deployment Commands Cheatsheet

### Development Workflow

```bash
# Start local development (frontend + backend)
cd ~/dev/cohezion

# Terminal 1: Backend (FastAPI + SurrealDB)
uv run uvicorn cohezion.api:app --reload --port 8080

# Terminal 2: Frontend (Next.js dashboard)
cd src/web/anima_dashboard
bun run dev  # Runs on http://localhost:3000

# Terminal 3: SurrealDB (if not running)
surreal start --log trace --user root --pass root memory
```

### Production Deployment

```bash
# Deploy to Vercel (web)
cd src/web/anima_dashboard
vercel --prod  # Deploys to cohezion-portfolio.vercel.app

# Build desktop app (if needed)
cargo tauri build  # Produces platform-specific binary

# Deploy backend (example: Fly.io for FastAPI)
fly deploy  # Requires fly.toml configuration (see Fly.io docs)
```

### Testing Before Deploy

```bash
# Run all checks (lint + test + type-check)
cd ~/dev/cohezion
make all  # Runs format, lint, type-check, test suite

# Test Next.js production build locally
cd src/web/anima_dashboard
bun run build  # Verifies production build works
bun run start  # Serves production build on http://localhost:3000
```

---

## Part 10: Next Actions (Immediate)

**Recommended First Steps** (prioritized):

1. **Verify bun installation** (5 minutes):

   ```bash
   curl -fsSL https://bun.sh/install | bash
   cd ~/dev/cohezion/src/web/anima_dashboard
   bun install  # Should complete in <10 seconds vs ~60 seconds with npm
   bun run dev  # Verify dashboard still works
   ```

2. **Audit existing anima_dashboard** (15 minutes):
   - Read `src/web/anima_dashboard/src/app/page.tsx` (landing page)
   - Check if 5 portfolio pillars already have UI skeletons
   - Identify gaps (what's missing for each pillar?)

3. **Set up Vercel deployment** (10 minutes):

   ```bash
   npm i -g vercel  # Install Vercel CLI
   cd src/web/anima_dashboard
   vercel  # Follow prompts, link to GitHub repo
   # Save URL (e.g., cohezion-portfolio.vercel.app)
   ```

4. **Implement FLUME latent space endpoint** (30 minutes):
   - Add to `src/cohezion/api/__init__.py`:

   ```python
   @app.get("/flume/latent-space")
   async def get_flume_latent_space():
       from cohezion.flume.vae import get_latent_embeddings
       embeddings = get_latent_embeddings()  # 256D vectors
       # TODO: Reduce to 3D via PCA for visualization
       from sklearn.decomposition import PCA
       pca = PCA(n_components=3)
       embeddings_3d = pca.fit_transform(embeddings)
       return {"embeddings": embeddings_3d.tolist()}
   ```

5. **Build FLUME navigator component** (1-2 hours):
   - Create `src/web/anima_dashboard/src/components/FlumeNavigator.tsx`
   - Use React-Three-Fiber for 3D scatter plot
   - Fetch from `/api/flume/latent-space` on mount

6. **Write first blog post** (2 hours):
   - Title: "From Git Commits to Latent Continua: Training a VAE on Software Evolution"
   - Sections: Problem, FLUME architecture, Training process, Results, Interactive demo
   - Save as Markdown in `src/web/anima_dashboard/src/content/blog/flume-vae.md`

**By End of Week**: FLUME pillar fully functional (demo + blog post), deployed to Vercel, <30 second load time.

---

## Appendix A: Key Files to Create/Modify

### New Files

| File                                                                | Purpose                       | Estimated Lines |
| ------------------------------------------------------------------- | ----------------------------- | --------------- |
| `src/web/anima_dashboard/src/components/FlumeNavigator.tsx`         | 3D latent space visualization | 150-200         |
| `src/web/anima_dashboard/src/components/CompoundDashboard.tsx`      | Metrics charts (Plotly)       | 100-150         |
| `src/web/anima_dashboard/src/components/UniverseSimulator.tsx`      | 12D → 3D trajectory plot      | 200-250         |
| `src/web/anima_dashboard/src/components/SwarmStream.tsx`            | Live agent execution feed     | 100-120         |
| `src/web/anima_dashboard/src/components/EvaluationTrajectories.tsx` | RL trajectory comparison      | 120-150         |
| `src/web/anima_dashboard/src/hooks/useAgentStream.ts`               | WebSocket hook                | 40-60           |
| `src/web/anima_dashboard/src/lib/api.ts`                            | API client (fetch wrappers)   | 80-100          |
| `src/web/anima_dashboard/src/content/blog/*.md`                     | 5 blog posts (Markdown)       | 500-800 each    |

### Modified Files

| File                                       | Changes                              | Impact     |
| ------------------------------------------ | ------------------------------------ | ---------- |
| `src/cohezion/api/__init__.py`             | Add 9 REST endpoints + 1 WebSocket   | +200 lines |
| `src/web/anima_dashboard/next.config.js`   | Add API proxy rewrites               | +10 lines  |
| `src/web/anima_dashboard/package.json`     | (No changes, bun uses same file)     | 0 lines    |
| `src/web/anima_dashboard/src/app/page.tsx` | Update landing page (5 pillar cards) | +50 lines  |

---

## Appendix B: Anthropic Research Engineer — Portfolio Checklist

**Before Submitting Application**:

- [ ] **Portfolio live at custom domain** (e.g., cohezion.dev)
- [ ] **All 5 demos functional** (FLUME, Compound, Universe, Swarm, Evaluation)
- [ ] **Each pillar has blog post** (technical depth + readability)
- [ ] **Mobile-responsive** (test on phone + tablet)
- [ ] **<30 second load time** (Lighthouse score >90)
- [ ] **GitHub repo public** with README explaining project
- [ ] **Contact info visible** (email, LinkedIn, GitHub)
- [ ] **No broken links** (all demos, blog posts, external links work)
- [ ] **Accessibility audit passed** (axe DevTools, no critical issues)
- [ ] **Backend integration working** (not just mock data)

**Application Materials**:

- [ ] **Cover letter** mentions portfolio URL in first paragraph
- [ ] **Resume** includes portfolio link prominently
- [ ] **LinkedIn profile** updated with portfolio link
- [ ] **Email to recruiter** highlights 3 key demos (FLUME, Universe, Swarm)

**Technical Interview Prep**:

- [ ] **Can explain SPIN architecture** (information theory → 12D manifold)
- [ ] **Can walk through compound loop** (execute → reflect → refine)
- [ ] **Can demo live** (run locally during interview if needed)
- [ ] **Can discuss trade-offs** (why FLUME VAE over autoencoder? why 12D?)
- [ ] **Can show code quality** (tests, type hints, CI/CD)

---

## Summary

**Key Takeaways**:

1. **Packaging**: Use **bun** (primary) + **npm** (fallback) — **NOT npx** (npx is for one-off commands)
2. **Deployment**: **Vercel** for web (zero-config Next.js), **Tauri** if desktop app needed
3. **Architecture**: Next.js frontend → FastAPI backend → SurrealDB (WebSocket for live streams)
4. **Timeline**: 4 weeks (8-10 hours/week) to production-ready portfolio
5. **Success Metric**: All 5 demos live, <30 second load, ready to share with Anthropic

**Immediate Next Step**: Install bun, deploy existing dashboard to Vercel, implement FLUME latent space demo (Week 1 goal).

**Long-Term Goal**: "Living portfolio" at cohezion.dev showcasing universe simulation expertise, positioning for Research Engineer (Universes) role at Anthropic.
