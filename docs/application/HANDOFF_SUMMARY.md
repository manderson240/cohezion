# Cohezion — Application Package Summary

**Date:** 2026-03-29
**Target:** Research Engineer, Universes — Anthropic
**Application Link:** https://job-boards.greenhouse.io/anthropic/jobs/5061517008

---

## Live Links

| Page | URL |
|------|-----|
| **Cohezion Dashboard** | https://frameworkdesktop.tail54eb71.ts.net/ |
| **Genesis Engine** (physics visualizations) | https://frameworkdesktop.tail54eb71.ts.net/genesis |
| **Portfolio** | https://frameworkdesktop.tail54eb71.ts.net/portfolio |
| **FLUME Portfolio** | https://frameworkdesktop.tail54eb71.ts.net/portfolio/flume |
| **GitHub Repo** | https://github.com/manderson240/cohezion |

**Pending:** `https://cohezion.duckdns.org` — Caddy + Let's Encrypt configured, waiting on Duck DNS nameserver stability. To activate:
```bash
sudo tailscale funnel --https=443 off && sudo systemctl start caddy
```

---

## What Was Built (This Session)

### Phase 0: Genesis Engine Merge
- Merged `spec/genesis-engine` branch (2,367 files) into `main`
- Physics modules: SU(2) spinors, Riemannian metric, Lagrangian dynamics, fiber bundles, Yang-Mills gauge theory, Fisher information metric, cosmogony
- Gymnasium RL environments: ManifoldEnv (19D obs, 12D action), SwarmEnv (multi-agent)
- JEPA World Model (~86K params, causal masking)
- Genesis webapp (Next.js + Three.js + Tone.js)
- Research paper: "FLUME and the Genesis Engine" (27 citations)

### Phase 1: Demo Quickstart
- `demo/quickstart.py` — trains agent for 50 episodes (67s CPU)
- `demo/evaluate.py` — 6 FLUME metrics with bootstrap 95% CIs + radar chart
- `demo/export_dataset.py` — exports DPO pairs, rewards, judgments (4,950 records)

### Phase 2: Application Materials
- `docs/application/resume.md` — 2-page resume, every JD bullet mapped
- `docs/application/cover-letter.md` — 1 page, direct technical tone
- `docs/application/technical-summary.md` — 2-page FLUME overview with architecture diagram
- `docs/application/interview-prep.md` — code walkthrough, technical/behavioral answers, questions

### Phase 3: Infrastructure
- Security audit: no tokens exposed, .env properly gitignored
- Duck DNS: `cohezion.duckdns.org` → 68.175.143.201 (verified)
- UPnP port forwarding: ports 80 + 443 → 192.168.86.25
- Caddy systemd service: auto-HTTPS, reverse proxy to Next.js
- Next.js systemd service: `cohezion-genesis.service` (survives reboots)
- Tailscale Funnel: working fallback link
- Git: pushed to origin/main

### Demo Verification Results
```
Coherence Amplitude:  0.8994  [0.8877, 0.9115]
Phase Locking Rate:   0.5596  [0.4278, 0.6872]
Exotic Charge Life:   95.5    [90.5, 99.0] steps
Orbit Quality:        0.9986  [0.9986, 0.9986]
TRIUNE Balance:       0.8497  [0.8283, 0.8704]
Recovery Basin:       0.1467  [0.1373, 0.1556]
```

---

## Key Repository Paths

| Path | What |
|------|------|
| `src/cohezion/physics/` | SU(2) spinors, gauge theory, cosmogony, Lagrangian |
| `src/cohezion/environments/` | ManifoldEnv, SwarmEnv (Gymnasium) |
| `src/cohezion/universe/` | 12D engine, LLM Training Bridge |
| `src/cohezion/world_model/` | JEPA, bioelectric, EVO model |
| `src/web/anima_dashboard/` | Genesis webapp (Next.js + Three.js) |
| `docs/papers/genesis-engine-paper.md` | Research paper (27 citations) |
| `docs/application/` | Resume, cover letter, tech summary, interview prep |
| `demo/` | 3-command quickstart (train, eval, export) |

---

## Action Items for Mike

1. **Fill in Education** in `docs/application/resume.md` (placeholder marked `[To be filled in by Mike]`)
2. **Submit** at https://job-boards.greenhouse.io/anthropic/jobs/5061517008
3. **Check `cohezion.duckdns.org`** periodically — it will go live once Duck DNS nameservers stabilize
4. **Rotate tokens** if making repo public (HF tokens in .env are gitignored but rotate as a precaution)
