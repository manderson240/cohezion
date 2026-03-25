# Portfolio Quick Start — Using Existing cohezion.duckdns.org

**Date**: 2026-03-22
**Context**: You already have `cohezion.duckdns.org` configured (see [docs/DEPLOY.md](docs/DEPLOY.md)). This guide shows how to deploy your Next.js portfolio to this domain.

---

## Your Existing Setup

From the codebase, you already have:

✅ **Domain**: `cohezion.duckdns.org` (registered, free via DuckDNS)
✅ **DuckDNS updater**: [scripts/update_duckdns.sh](scripts/update_duckdns.sh) (updates IP every 5 minutes)
✅ **Cloudflare tunnel**: [scripts/deploy_tunnel.sh](scripts/deploy_tunnel.sh) (routes HTTPS to local port)
✅ **Deployment docs**: [docs/DEPLOY.md](docs/DEPLOY.md)

Currently used for:
- Marimo notebooks (FLUME showcase, HIHO explorer, R0 dashboard)
- MCP server (vault access via tunnel on port 8360)
- FastAPI backend (port 8080)

---

## Two Deployment Strategies

### Strategy 1: Use DuckDNS for Everything (Simplest)

**Pros**:
- No additional cost (DuckDNS is free)
- Already configured and working
- Single domain for all demos

**Cons**:
- Mixing production portfolio with local tunnel
- DuckDNS can be slow to propagate DNS changes
- Limited to one subdomain (can't do `api.cohezion.duckdns.org`)

**How to Deploy Next.js to cohezion.duckdns.org**:

See full deployment commands in Strategy 1 section.

---

### Strategy 2: Separate Domains (Recommended for Anthropic)

**Domain Allocation**:

| Domain | Purpose | Deployment |
|--------|---------|------------|
| `cohezion.dev` | Production portfolio (for Anthropic) | Vercel (Next.js + global CDN) |
| `cohezion.duckdns.org` | Local tunnel (MCP server, dev testing) | Cloudflare tunnel → localhost |

---

## Recommendation

**Week 1-2**: Deploy to `cohezion.duckdns.org` using existing setup (fast iteration, zero cost)
**Week 3-4**: Buy `cohezion.dev` and migrate to Vercel (professional domain for Anthropic)

See PORTFOLIO_DEPLOYMENT_PLAN.md for detailed 4-week roadmap.
