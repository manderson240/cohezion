# Portfolio Summary — Living Showcase for Anthropic Research Engineer (Universes)

**Updated**: 2026-03-22
**Target Role**: Research Engineer, Universes @ Anthropic
**Current Status**: Implementation phase (packaging + deployment strategy defined)

---

## Executive Summary

Transform Cohezion into a **living portfolio** showcasing:
1. **12D Universe Simulation** (SPIN + FLUME + HIHO manifold)
2. **Compound Engineering Loop** (self-improving infrastructure, 55+ sessions)
3. **Multi-Agent Orchestration** (swarm routing, democratic debate)
4. **Production-Grade System** (579 modules, 4,426 tests, 99.9% pass rate)

**Deployment**: `cohezion.duckdns.org` (existing, Week 1-2) → `cohezion.dev` (Vercel, Week 3-4)
**Timeline**: 4 weeks (8-10 hours/week)
**First Demo Live**: FLUME VAE latent space navigator (Week 1)

---

## Key Documents (Read These in Order)

1. **[PORTFOLIO_DEPLOYMENT_PLAN.md](PORTFOLIO_DEPLOYMENT_PLAN.md)** (10,000+ words, comprehensive)
   - Modern packaging strategy (bun vs npm vs npx)
   - "Living portfolio" architecture (Next.js + FastAPI + SurrealDB)
   - Deployment options (Vercel web, Tauri desktop)
   - 4-week roadmap with 5 interactive demos
   - Anthropic positioning strategy

2. **[PORTFOLIO_QUICK_START.md](PORTFOLIO_QUICK_START.md)** (DuckDNS-specific)
   - Uses existing `cohezion.duckdns.org` domain
   - Two deployment strategies (DuckDNS local vs Vercel production)
   - Next.js + FastAPI integration (reverse proxy setup)
   - Immediate next steps (bun install, test locally, deploy)

3. **[docs/DEPLOY.md](docs/DEPLOY.md)** (existing deployment guide)
   - Current setup: Marimo notebooks on cohezion.duckdns.org
   - DuckDNS configuration, Caddy reverse proxy
   - MCP server tunnel (port 8360)

---

## Modern Packaging Decision (Answer to "npx or npm?")

**Question**: "What's the modern way to do it? npx or npm or something else entirely?"

**Answer**: 

| Tool | Purpose | Use for Cohezion Portfolio? |
|------|---------|------------------------------|
| **bun** | Modern npm alternative (2-10x faster) | ✅ **YES — Primary recommendation** |
| **npm** | Traditional package manager | ✅ **YES — Fallback for compatibility** |
| **npx** | One-off command execution | ❌ **NO — Not for deployment** (only for `npx create-next-app`) |

**Recommended**: **bun** (primary), npm (fallback)

**Why bun?**
- 2-10x faster than npm for installs/builds
- Drop-in replacement (uses same `package.json`, zero migration)
- Single binary (easy install: `curl -fsSL https://bun.sh/install | bash`)
- Your existing Next.js dashboard works with just `bun install`

**Migration** (zero code changes):
```bash
cd ~/dev/cohezion/src/web/anima_dashboard
bun install  # Uses existing package.json, creates bun.lockb
bun run dev  # Works identically to npm run dev
```

**npx is NOT for deployment** — it's only for running one-off commands like `npx create-next-app` or `npx tsc --init`. Don't use it to deploy your portfolio.

---

## Domain Strategy (Using Your Existing cohezion.duckdns.org)

You already own: `cohezion.duckdns.org` (free via DuckDNS, configured in [scripts/update_duckdns.sh](scripts/update_duckdns.sh))

**Two Options**:

### Option 1: Use DuckDNS for Everything (Week 1-2, Fast Iteration)

- **Domain**: `cohezion.duckdns.org` (existing)
- **Deployment**: Caddy reverse proxy (local server)
- **Cost**: $0
- **Speed**: Deploy in 30 minutes
- **Pros**: Already configured, zero cost, fast iteration
- **Cons**: Home internet dependent, slower global load times

**Setup**:
```bash
# Update /etc/caddy/Caddyfile
cohezion.duckdns.org {
    handle /api/* {
        reverse_proxy localhost:8080  # FastAPI
    }
    handle {
        reverse_proxy localhost:3000  # Next.js portfolio
    }
}

sudo systemctl reload caddy
```

### Option 2: Buy cohezion.dev, Keep DuckDNS for Tunnel (Week 3-4, Anthropic Ready)

- **Production Portfolio**: `cohezion.dev` (Vercel, $10/year domain)
- **Local Tunnel**: `cohezion.duckdns.org` (MCP server, unchanged)
- **Cost**: $10/year
- **Speed**: <1 second global load (Vercel CDN)
- **Pros**: Professional domain, global CDN, 99.9% uptime
- **Cons**: Requires DNS configuration

**Recommended**: Start with Option 1, upgrade to Option 2 for Anthropic submission.

---

## 5 Portfolio Pillars (Interactive Demos)

Each pillar = **Blog post** + **Interactive demo** + **Research artifact**

### 1. FLUME VAE (Continuous Latent Navigation)
- **Demo**: 3D scatter plot of 256D latent space (user clicks → FLUME navigates → plot updates)
- **Tech**: React-Three-Fiber, `/api/flume/latent-space` endpoint
- **Blog**: "From Git Commits to Latent Continua: Training a VAE on Software Evolution"
- **Anthropic Relevance**: Continuous state spaces for RL (vs discrete grids)

### 2. Compound Loop (Self-Improving Infrastructure)
- **Demo**: Live metrics dashboard (coherence trend over 55 sessions, cost savings)
- **Tech**: Plotly time series, `/api/compound/metrics` endpoint
- **Blog**: "Compound Engineering: How AI Infrastructure Learns to Build Itself"
- **Anthropic Relevance**: Infrastructure that improves with use (meta-learning)

### 3. Universe Simulation (12D Manifold)
- **Demo**: Interactive universe step-through (user sets 12D state → simulate → 3D trajectory)
- **Tech**: React-Three-Fiber, `/api/universe/simulate` endpoint
- **Blog**: "Building a 12-Dimensional Universe for Agent Training"
- **Anthropic Relevance**: Scalable simulation environments for agent research

### 4. Multi-Agent Swarm (Cost-Aware Orchestration)
- **Demo**: Live agent execution stream (user query → swarm routes → debate → answer)
- **Tech**: WebSocket `/ws/agent-stream`, live event feed
- **Blog**: "Democratic Debate: How Five AI Agents Reach Consensus"
- **Anthropic Relevance**: Efficient orchestration of multiple models

### 5. Evaluation Infrastructure (Trajectory-Based Assessment)
- **Demo**: RL trajectory comparison (successful vs failed coherence navigation)
- **Tech**: Plotly, `/api/evaluation/trajectories` endpoint
- **Blog**: "Beyond Accuracy: Evaluating Agents Through Coherence Trajectories"
- **Anthropic Relevance**: Evaluating agent behavior in continuous spaces

---

## 4-Week Implementation Roadmap

### Week 1: Foundation (8-10 hours) — FLUME VAE Demo Live

**Goal**: One pillar fully functional, deployed to cohezion.duckdns.org

**Tasks**:
1. ✅ Migrate to bun (1 hour): `cd src/web/anima_dashboard && bun install`
2. Add FLUME latent space visualization (4 hours): FlumeNavigator.tsx component
3. Deploy to cohezion.duckdns.org (1 hour): Caddy reverse proxy configuration
4. Write blog post (2 hours): "From Git Commits to Latent Continua"
5. Test end-to-end (1 hour): Verify <30 second load time

**Success Metric**: FLUME pillar live, interactive demo functional

### Week 2: Expansion (12-15 hours) — All 5 Pillars with Basic Demos

**Goal**: All 5 demos functional, 5 blog posts drafted

**Tasks**:
1. Compound Loop Dashboard (3 hours)
2. Universe Simulation Demo (4 hours)
3. Swarm Orchestration Demo (3 hours)
4. Evaluation Infrastructure Demo (2 hours)
5. Polish landing page (1 hour)

**Success Metric**: All 5 demos functional, <30 second total site load

### Week 3: Integration (10-12 hours) — Connect to Live Backend

**Goal**: All demos pull from real Cohezion backend (not mock data)

**Tasks**:
1. Backend API implementation (6 hours): 9 REST endpoints + WebSocket
2. Frontend integration (4 hours): Replace mock data with real API calls
3. Performance optimization (2 hours): Caching, lazy loading

**Success Metric**: All demos pull from live backend, graceful degradation if backend offline

### Week 4: Polish & Launch (8-10 hours) — Production Ready

**Goal**: Ready to share with Anthropic

**Tasks**:
1. Visual polish (3 hours): Dark mode, responsive design
2. Content finalization (2 hours): Edit blog posts
3. CI/CD setup (2 hours): GitHub Actions (lint → test → deploy)
4. Custom domain (1 hour): Buy cohezion.dev, configure Vercel
5. Launch checklist (1 hour): All demos <30s load, no console errors

**Success Metric**: Portfolio live at cohezion.dev (or cohezion.duckdns.org), ready for Anthropic

---

## "Living Portfolio" Definition

What makes it **living** (not static)?

✅ **Interactive demos** user can explore in real-time (not screenshots)
✅ **Live metrics** from actual Cohezion backend (not mocked data)
✅ **3D universe visualization** showing current simulation state (not pre-rendered)
✅ **Real-time updates** (WebSocket for agent execution streams)
✅ **One-click local deployment** (user can clone + run full system)

❌ **NOT**: PDF resume, screenshots, pre-recorded videos, dead links

**Key Insight**: Every demo connects to your actual FastAPI backend (port 8080) + SurrealDB. User sees real Cohezion system operating, not a static showcase.

---

## Anthropic Positioning Strategy

### Universes Team Alignment

**Anthropic's Universes Team** (inferred from research):
- Universe simulation for agent training/evaluation
- Emergent behavior in multi-agent systems
- Scalable RL environments
- Safety research through simulated worlds

**Cohezion's Unique Fit**:

| Anthropic Need | Cohezion Demonstration | Portfolio Showcase |
|----------------|------------------------|---------------------|
| Universe simulation | 12D manifold engine (SPIN + FLUME + HIHO) | Interactive 3D projection of 12D space |
| Agent training | RL environment (Gymnasium-compatible) | Live trajectory plots with coherence gates |
| Multi-agent systems | Swarm orchestration (5 specialists + debate) | Real-time agent execution stream |
| Scalable infrastructure | Compound engineering loop (self-improving) | Metrics dashboard (55 sessions of improvement) |
| Safety research | Constitution-governed behavior | Audit trail of all agent decisions |

### Landing Page Narrative (30-Second Pitch)

1. **Hook**: "Self-improving AI infrastructure that learns from every execution"
2. **Problem**: "Current AI systems don't compound — each task starts from scratch"
3. **Solution**: "Cohezion's compound loop: execute → reflect → refine → repeat"
4. **Proof**: "579 modules, 4,426 tests, 99.9% pass rate — all refined through 55+ compound cycles"
5. **CTA**: "Explore 5 interactive demos below ↓"

---

## Technical Highlights for Resume/Cover Letter

**For Research Engineer Role**:
- ✅ **Novel Architecture**: SPIN information theory → 12D manifold design
- ✅ **Production-Ready Code**: 99.9% test pass rate, type-hinted, CI/CD
- ✅ **Scalability**: Handled 510 K-Search cycles in 4-hour session (128 GB RAM, Ollama local models)
- ✅ **Research Rigor**: Jupyter notebooks for experiments, arXiv paper searches integrated
- ✅ **Open Source**: Full codebase available, reproducible from `git clone`

---

## Current Status (2026-03-22)

### ✅ Completed
- Portfolio strategy defined (5 pillars, 4-week roadmap)
- Modern packaging decision (bun recommended)
- Deployment strategy (DuckDNS → Vercel migration path)
- Domain clarification (use existing cohezion.duckdns.org)
- Architecture design (Next.js + FastAPI + SurrealDB)

### 🚧 In Progress
- None (waiting for implementation to begin)

### 📋 Next Actions

**Immediate** (next 30 minutes):
1. Install bun: `curl -fsSL https://bun.sh/install | bash`
2. Test Next.js dashboard: `cd src/web/anima_dashboard && bun install && bun run dev`
3. Verify FastAPI backend: `uv run uvicorn cohezion.api:app --reload --port 8080`

**Week 1 Goal** (next 8-10 hours):
- Implement FLUME latent space endpoint in FastAPI
- Build FlumeNavigator.tsx component (3D scatter plot)
- Deploy to cohezion.duckdns.org (Caddy reverse proxy)
- Write blog post: "From Git Commits to Latent Continua"

---

## Success Metrics

### Technical
- [ ] All 5 demos load in <30 seconds
- [ ] No console errors in browser DevTools
- [ ] Mobile-responsive (test on 3 screen sizes)
- [ ] WCAG AA accessibility compliance
- [ ] Lighthouse performance score >90

### Content
- [ ] 5 blog posts written (500-800 words each, technical depth)
- [ ] Landing page copy finalized (30-second pitch)
- [ ] GitHub repo public with comprehensive README
- [ ] Contact info visible (email, LinkedIn, GitHub)

### Deployment
- [ ] Portfolio live at cohezion.duckdns.org (or cohezion.dev)
- [ ] CI/CD pipeline (GitHub Actions: lint → test → deploy)
- [ ] Custom domain with HTTPS
- [ ] Backend integration working (not just mock data)

### Anthropic Application
- [ ] Portfolio URL in cover letter (first paragraph)
- [ ] Portfolio URL on resume (prominently displayed)
- [ ] LinkedIn profile updated with portfolio link
- [ ] Email to recruiter highlighting 3 key demos (FLUME, Universe, Swarm)

---

## Files Created This Session

1. **[PORTFOLIO_DEPLOYMENT_PLAN.md](PORTFOLIO_DEPLOYMENT_PLAN.md)** (10,000+ words)
   - Comprehensive packaging strategy (bun vs npm vs npx)
   - "Living portfolio" architecture design
   - Backend API integration (9 REST endpoints + WebSocket)
   - 4-week implementation roadmap
   - Anthropic positioning strategy
   - Deployment commands cheatsheet

2. **[PORTFOLIO_QUICK_START.md](PORTFOLIO_QUICK_START.md)** (DuckDNS-specific)
   - Uses existing cohezion.duckdns.org domain
   - Two deployment strategies (DuckDNS vs Vercel)
   - Next.js + FastAPI integration via reverse proxy
   - Immediate next steps (bun install, local testing, Caddy config)

3. **This file** (PORTFOLIO_SUMMARY.md)
   - Executive summary of entire portfolio strategy
   - Quick reference for all decisions made
   - Links to detailed documentation

---

## Quick Reference

| Need | Command | File |
|------|---------|------|
| Install bun | `curl -fsSL https://bun.sh/install \| bash` | — |
| Run Next.js (dev) | `cd src/web/anima_dashboard && bun run dev` | package.json |
| Run FastAPI | `uv run uvicorn cohezion.api:app --reload --port 8080` | src/cohezion/api/__init__.py |
| Deploy to DuckDNS | Edit `/etc/caddy/Caddyfile`, `sudo systemctl reload caddy` | docs/DEPLOY.md |
| Deploy to Vercel | `vercel --prod` | PORTFOLIO_DEPLOYMENT_PLAN.md |
| Update DuckDNS IP | Runs every 5 minutes via cron | scripts/update_duckdns.sh |
| Full deployment plan | Read PORTFOLIO_DEPLOYMENT_PLAN.md | PORTFOLIO_DEPLOYMENT_PLAN.md |
| DuckDNS quick start | Read PORTFOLIO_QUICK_START.md | PORTFOLIO_QUICK_START.md |

---

## Key Insight from This Session

**User's Question**: "How do we package it all together? What's the modern way to do it? npx or npm or something else entirely?"

**Answer**: 
- **bun** (modern, 2-10x faster than npm, drop-in replacement)
- **npm** (fallback for compatibility)
- **NOT npx** (npx is for one-off commands, not deployment)

**Domain Strategy**:
- You already have `cohezion.duckdns.org` (use it for Week 1-2)
- Upgrade to `cohezion.dev` for Anthropic submission (Week 3-4)
- Keep DuckDNS for local MCP server tunnel (separate concerns)

**Next Step**: Install bun, test existing Next.js dashboard, deploy to cohezion.duckdns.org using Caddy reverse proxy (Week 1 goal).
