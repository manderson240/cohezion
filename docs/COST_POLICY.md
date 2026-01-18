# Cohezion Cost Policy

## Core Principle: FREE FIRST

All integrations, APIs, and services MUST be free or have generous free tiers.
Do NOT implement paid services without explicit user approval.

## Approved Free Services

### APIs
| Service | Free Tier | Our Usage |
|---------|-----------|-----------|
| Gmail API | 1B units/day | ~100/day |
| Google Cloud (OAuth only) | Free | Free |
| Ollama (local) | 100% free | Unlimited |
| GitHub API | 5000 req/hr | Minimal |

### Infrastructure
| Resource | Status | Notes |
|----------|--------|-------|
| Local SLM swarm | FREE | Ollama on local hardware |
| Local storage | FREE | ZFS on local drives |
| MCP servers | FREE | Self-hosted |

## Rejected/Deferred (Cost Money)
- OpenAI API (pay-per-token)
- Anthropic API (pay-per-token) 
- AWS/GCP compute (per-hour)
- Paid blockchain staking (requires capital)

## Monetization vs Spending
- We EARN money from idle compute
- We do NOT SPEND money on services
- Any paid service requires ROI justification

## Before Adding Any Service
1. Verify free tier exists
2. Document free tier limits
3. Estimate our usage
4. Confirm usage << free tier limit
5. Get user approval if borderline
