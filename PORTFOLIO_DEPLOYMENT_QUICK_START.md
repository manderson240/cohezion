# Portfolio Deployment — Quick Start

**Status**: ✅ **Phase 1 Complete** (FLUME Pillar Live, Portfolio Landing Page Ready)

This guide walks you through deploying the Cohezion living portfolio in <10 minutes.

---

## What's Been Built

### ✅ Completed (Session 2026-03-22)

1. **Portfolio Landing Page** ([/portfolio](http://localhost:3000/portfolio))
   - Hero section with 30-second pitch
   - 5 pillar cards (FLUME, Compound, Universe, Swarm, Evaluation)
   - Stats dashboard (3,214 tests, 55+ cycles, 95% cache hit, 27.3% cost savings)
   - Problem/Solution/Proof narrative
   - Technical highlights grid

2. **FLUME VAE Demo** ([/portfolio/flume](http://localhost:3000/portfolio/flume))
   - Backend API endpoint: `POST /flume/latent-space` (returns PCA-reduced 3D coordinates)
   - 3D interactive visualization (Three.js + React-Three-Fiber)
   - Color-mapped coherence scores (blue → green → yellow gradient)
   - Adjustable sample count (50-500 points)
   - Demo/Explanation tabs
   - Anthropic Universes relevance section

3. **Bun Integration**
   - Bun 1.3.11 installed (2-10x faster than npm)
   - Package.json scripts work with both bun and npm (zero migration)
   - Lock file: `bun.lockb` created alongside `package-lock.json`

4. **API Proxy Configuration**
   - Next.js rewrites forward `/api/*` to FastAPI backend (port 8080)
   - Environment variable support: `NEXT_PUBLIC_API_URL`

### 🚧 In Progress (Next 2-3 Sessions)

- Pillar #2: Compound Loop Dashboard
- Pillar #4: Swarm Orchestration Demo
- Pillar #5: Evaluation Infrastructure
- Blog posts for each pillar (Markdown + MDX)
- Vercel deployment + custom domain

### ✨ Already Live (Existing)

- **Pillar #3: Universe Simulation** ([/](http://localhost:3000/))
  - Existing Anima Dashboard (Triune navigation: Knower/Thinker/Doer)
  - SSE stream from backend
  - 12D manifold visualization (TensorBeamVisualizer)
  - Perturbation controls, snapshot gallery, persistence diagram

---

## Local Development (< 2 Minutes)

### Prerequisites

- Python 3.13+ with `uv` installed
- Node.js 20+ (or bun 1.3+)
- SurrealDB 3.0 (optional, for universe simulation features)

### Steps

```bash
# 1. Start Backend (Terminal 1)
cd ~/dev/cohezion
uv run uvicorn cohezion.api:app --reload --port 8080

# 2. Start Frontend (Terminal 2)
cd src/web/anima_dashboard
~/.bun/bin/bun run dev  # Or: npm run dev

# 3. (Optional) Start SurrealDB (Terminal 3)
surreal start --log trace --user root --pass root memory

# 4. Open Browser
# Portfolio: http://localhost:3000/portfolio
# FLUME Demo: http://localhost:3000/portfolio/flume
# Universe Sim: http://localhost:3000/
```

### Environment Variables (Optional)

```bash
# Create .env.local in src/web/anima_dashboard/
cp .env.example .env.local

# Edit if backend is NOT on localhost:8080
NEXT_PUBLIC_API_URL=http://localhost:8080
```

---

## Production Deployment (Vercel)

### One-Time Setup (5 Minutes)

```bash
# 1. Install Vercel CLI
npm i -g vercel  # Or: bun add -g vercel

# 2. Deploy from dashboard directory
cd ~/dev/cohezion/src/web/anima_dashboard
vercel  # Follow prompts, link to GitHub repo

# 3. Configure environment variables
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://api.cohezion.dev (or your backend URL)

# 4. Deploy to production
vercel --prod
```

### Continuous Deployment (Automatic)

Once linked to GitHub:
- Push to `main` → Vercel auto-deploys production
- Push to feature branch → Vercel creates preview deployment

### Custom Domain (Optional, $10/year)

1. Buy domain (e.g., `cohezion.dev` via Namecheap)
2. Add domain in Vercel dashboard → DNS auto-configured
3. Portfolio lives at: `https://cohezion.dev`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    PORTFOLIO WEBAPP                      │
│           (src/web/anima_dashboard/)                     │
├─────────────────────────────────────────────────────────┤
│  Next.js 16 Frontend (Port 3000)                        │
│  ├─ /portfolio                Landing page              │
│  ├─ /portfolio/flume          FLUME VAE demo (3D viz)   │
│  ├─ /portfolio/compound       Compound loop (planned)   │
│  ├─ /portfolio/swarm          Swarm orchestration       │
│  ├─ /portfolio/evaluation     RL trajectories           │
│  └─ /                         Universe sim (existing)   │
├─────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8080)                            │
│  ├─ POST /flume/latent-space  3D latent space samples   │
│  ├─ POST /flume/encode        Encode 256D → latent      │
│  ├─ POST /flume/interpolate   Interpolate between vecs  │
│  ├─ GET  /api/universe/state  12D universe state        │
│  └─ 72+ other endpoints       (compound, swarm, etc.)   │
└─────────────────────────────────────────────────────────┘
```

---

## File Structure (Key Additions)

```
src/web/anima_dashboard/
├── src/
│   ├── app/
│   │   ├── portfolio/
│   │   │   ├── page.tsx                 # NEW: Portfolio landing page
│   │   │   ├── flume/
│   │   │   │   └── page.tsx             # NEW: FLUME demo page
│   │   │   └── [other pillars]/         # PLANNED
│   │   └── page.tsx                     # EXISTING: Anima Dashboard
│   ├── components/
│   │   ├── FlumeNavigator.tsx           # NEW: 3D latent space viz
│   │   ├── TensorBeamVisualizer.tsx     # EXISTING: Universe viz
│   │   └── [others]                     # EXISTING
│   └── hooks/
│       └── useUniverseStream.ts         # EXISTING: SSE hook
├── next.config.ts                       # MODIFIED: Added API proxy
├── .env.example                         # NEW: Environment template
├── package.json                         # EXISTING: Deps (no changes)
└── bun.lockb                            # NEW: Bun lock file

src/cohezion/api/
└── __init__.py                          # MODIFIED: Added /flume/latent-space
```

---

## Testing Checklist

### ✅ Backend API

```bash
# Test FLUME latent space endpoint
curl -X POST http://localhost:8080/flume/latent-space \
  -H "Content-Type: application/json" \
  -d '{"n_samples": 50, "seed": 42}'

# Expected: JSON with latent_dim, samples, samples_3d, variance_explained, coherence_scores
```

### ✅ Frontend Pages

1. **Portfolio Landing** (http://localhost:3000/portfolio)
   - [ ] Hero section loads
   - [ ] 5 pillar cards displayed
   - [ ] Stats grid shows 4 metrics
   - [ ] Problem/Solution/Proof section readable
   - [ ] Links to FLUME demo work

2. **FLUME Demo** (http://localhost:3000/portfolio/flume)
   - [ ] 3D visualization renders (no WebGL errors)
   - [ ] Point cloud appears with colored dots
   - [ ] Sample count slider adjusts points
   - [ ] Resample button triggers new fetch
   - [ ] Demo/Explanation tabs switch content
   - [ ] Back to Portfolio link works

3. **Universe Sim** (http://localhost:3000/)
   - [ ] Existing Anima Dashboard still works
   - [ ] TensorBeamVisualizer renders
   - [ ] Triune navigation (Knower/Thinker/Doer) functional

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Page Load** | <3s (portfolio), <5s (FLUME demo) | Chrome DevTools Network tab |
| **3D FPS** | >30 FPS | Chrome DevTools Performance tab |
| **API Latency** | <200ms (p95) | FastAPI logs |
| **Bundle Size** | <2 MB (initial load) | Next.js build output |

### Optimization Tips

1. **Lazy Load Three.js**: Already implemented with `dynamic(() => import(...), { ssr: false })`
2. **Reduce Sample Count**: Default to 100-200 points (not 500) for faster rendering
3. **Enable Next.js ISR**: For blog posts (once created), use `revalidate: 3600` (1 hour)
4. **Compress Assets**: Vercel auto-compresses, but check bundle analyzer for bloat

---

## Known Issues & Workarounds

### Issue: WebGL Context Lost

**Symptom**: 3D visualization shows black screen after switching tabs.

**Workaround**: Reload page. (TODO: Add context restoration handler)

### Issue: API 404 on First Load

**Symptom**: FLUME demo fails with "Failed to fetch latent space".

**Root Cause**: Backend not running OR CORS blocking request.

**Fix**:
1. Verify backend is running: `curl http://localhost:8080/health`
2. Check CORS origins: `COHEZION_CORS_ORIGINS` must include `http://localhost:3000`
3. Restart backend if needed

### Issue: Bun Install Hangs

**Symptom**: `bun install` never completes.

**Workaround**: Use npm instead: `npm install` (will take longer but works)

---

## Next Steps (Week 2-3)

### High Priority

1. **Compound Loop Dashboard** (Pillar #2)
   - Endpoint: `GET /api/compound/metrics` (query SurrealDB)
   - Component: Plotly time series (coherence trend, cost savings)
   - Page: `/portfolio/compound`

2. **Blog Posts** (5 × 500-800 lines)
   - `/portfolio/blog/flume-vae` (FLUME VAE explanation)
   - `/portfolio/blog/compound-engineering` (Self-improving infra)
   - `/portfolio/blog/universe-simulation` (12D manifold)
   - `/portfolio/blog/swarm-orchestration` (Multi-agent debate)
   - `/portfolio/blog/evaluation-trajectories` (Coherence gates)

3. **Vercel Deployment**
   - Link GitHub repo
   - Configure environment variables
   - Test preview deployment
   - Deploy to production

### Medium Priority

4. **Swarm Orchestration Demo** (Pillar #4)
   - WebSocket: `/ws/agent-stream/{agent_id}`
   - Component: Live event feed
   - Page: `/portfolio/swarm`

5. **Evaluation Infrastructure Demo** (Pillar #5)
   - Endpoint: `GET /api/evaluation/trajectories`
   - Component: Plotly trajectory comparison
   - Page: `/portfolio/evaluation`

### Low Priority

6. **Custom Domain** (`cohezion.dev`)
7. **CI/CD Pipeline** (GitHub Actions: lint → test → deploy)
8. **Analytics** (Vercel Analytics, track unique visitors)
9. **A/B Testing** (Landing page copy optimization)

---

## Success Metrics

### Phase 1 (Current) ✅

- [x] Portfolio landing page live
- [x] FLUME demo functional (3D viz + backend)
- [x] Bun integration working
- [x] API proxy configured
- [x] Load time <5 seconds

### Phase 2 (Week 2-3)

- [ ] All 5 pillars with demos
- [ ] 5 blog posts published
- [ ] Deployed to Vercel (preview URL)
- [ ] Load time <3 seconds (all pages)

### Phase 3 (Week 4)

- [ ] Custom domain live (`cohezion.dev`)
- [ ] No console errors (production build)
- [ ] Mobile-responsive (tested on 3 screen sizes)
- [ ] Shared with Anthropic recruiter

---

## Contact & Support

**GitHub**: [https://github.com/yourusername/cohezion](https://github.com/yourusername/cohezion) (update with real URL)

**Portfolio**: [https://cohezion-portfolio.vercel.app](https://cohezion-portfolio.vercel.app) (preview deployment)

**Issues**: File bugs/suggestions in GitHub Issues

---

## Appendix: Command Cheatsheet

```bash
# Development
bun run dev              # Start Next.js dev server
bun run build            # Build for production
bun run start            # Serve production build
bun run lint             # Run ESLint

# Backend
uv run uvicorn cohezion.api:app --reload --port 8080  # Start FastAPI
uv run pytest tests/ -q                               # Run test suite

# Deployment
vercel                   # Deploy to preview
vercel --prod            # Deploy to production
vercel env ls            # List environment variables

# Utilities
bun install              # Install dependencies
bun --version            # Check bun version (should be 1.3+)
```

---

**Last Updated**: 2026-03-22
**Version**: 1.0.0 (Phase 1 Complete)
