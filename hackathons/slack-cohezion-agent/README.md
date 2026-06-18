# Cohezion Intelligence Agent for Slack — Compound AI at $0/query

**Slack Agent Builder Challenge — New Slack Agent Track (MCP Server Integration)**  
Built by [@manderson240](https://github.com/manderson240) | Deadline: July 13, 2026

---

## What It Does

Cohezion Intelligence brings **enterprise compound AI** directly into Slack, backed by AMD silicon running locally at **$0 per query**. Three capabilities:

- **`/cohezion ask`** — Q&A routed through NPU→iGPU→CPU inference tiers in real time
- **`/cohezion review`** — 3-agent code review pipeline posting incremental updates to your thread
- **`/cohezion search`** — Semantic vault search via FLUME VAE 256D embeddings

Every capability connects through an **MCP server** — the qualifying technology for this track.

---

## Architecture

```
Slack Workspace
  │
  ├── /cohezion ask "how do I add rate limiting?"
  ├── /cohezion review "PR: Add OAuth PKCE to auth service"
  └── /cohezion search "Redis caching patterns"
        │
        ▼ Slack Bolt SDK
  Cohezion Slack Bot (app.py)
        │
        ▼ MCP protocol (HTTP JSON-RPC)
  CohezionMCPClient ◄─── THIS IS THE MCP INTEGRATION
        │
        ▼
  Cohezion MCP Server (mcp_server.py)
  ├── cohezion_ask          → ask_handler.py
  ├── cohezion_code_review  → review_handler.py
  ├── cohezion_search       → search_handler.py
  └── cohezion_get_status   → status_handler.py
        │
        ▼
  Cohezion Compound AI (AMD Strix Halo)
  ├── NPU  (port 13306): llama3.2-1b-FLM  — 42 TPS, $0
  ├── iGPU (port 13307): deepseek-r1-8b   — ~200ms, $0
  └── CPU  (port 13309): Gemma-4-31B      — ~800ms, $0
       │
       └── SemanticCache (FLUME VAE 256D, 95%+ hit rate)
```

---

## Why MCP Integration

MCP is the natural bridge between Slack's event-driven model and Cohezion's compound AI. The MCP server runs locally alongside the Slack bot, exposing Cohezion's capabilities as discoverable, typed tools:

| MCP Tool | What It Does |
|---|---|
| `cohezion_ask` | Compound Q&A with tier routing |
| `cohezion_code_review` | 3-agent code review pipeline |
| `cohezion_search` | FLUME VAE semantic search |
| `cohezion_get_status` | AMD silicon health dashboard |

Any MCP-compatible client (Slack, Claude Desktop, other agents) can discover and call these tools — the integration works beyond just this Slack agent.

---

## AMD Silicon — $0/Query

| Tier | Port | Model | Speed | Cost |
|---|---|---|---|---|
| NPU | 13306 | llama3.2-1b-FLM | 42 TPS | **$0** |
| iGPU | 13307 | deepseek-r1-0528-8b | ~200ms | **$0** |
| CPU | 13309 | Gemma-4-31B-it-GGUF | ~800ms | **$0** |

10,000 Slack queries/month on local silicon: **$0.00**  
Same on Anthropic Sonnet: **$180.00**

The task classifier (NPU, sub-500µs) routes each question to the right tier automatically — short answers to NPU, generation to iGPU, reasoning to CPU. Cloud (claude-haiku-4-5) activates only when local silicon is offline.

---

## The 3-Agent Code Review Pipeline

When a developer types `/cohezion review Add OAuth2 PKCE to auth service`, Slack sees a live thread:

```
⚙ Orchestrator: Classifying task — complexity: HIGH, 4 phases
🔬 Analyst: Semantic enrichment — 2 high risks, 3 similar patterns found
🔨 Engineer: Implementation — 5 patches, 87% confidence

Cohezion Code Review Complete (4.2s)
• Complexity: HIGH
• High risks: 2
• Code patches: 5
• Confidence: 87%
• Cost: $0.0000
```

Each agent posts to the Slack thread in real time via the `progress_callback` pattern — the user sees the pipeline thinking, not just a final answer.

---

## Setup

### Prerequisites
- Python 3.11+
- Slack workspace with admin access
- Anthropic API key (optional — works without it when AMD silicon is online)

### 1. Create Slack App

Go to [api.slack.com/apps](https://api.slack.com/apps) → Create App → From Scratch

Enable these features:
- **Slash Commands**: Add `/cohezion` pointing to your server
- **Bot Token Scopes**: `chat:write`, `commands`, `app_mentions:read`
- **Socket Mode**: Enable (simplest for development)
- **Event Subscriptions**: `app_mention`

### 2. Install Dependencies

```bash
cd ~/cohezion-labs/slack-cohezion-agent
pip install -r requirements.txt
# Or with uv:
uv pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your Slack credentials and Anthropic API key
```

### 4. Start Services

```bash
# Terminal 1: MCP server (the qualifying integration)
python mcp_server.py

# Terminal 2: Slack bot
python app.py
```

### 5. Try It in Slack

```
/cohezion status
/cohezion ask How do I implement JWT refresh token rotation?
/cohezion review Add rate limiting middleware to FastAPI
/cohezion search Redis caching patterns
```

### Local Demo (no Slack credentials)

```bash
python demo/slack_demo.py all
python demo/slack_demo.py ask "How do I add rate limiting?"
python demo/slack_demo.py review "Add OAuth2 PKCE to auth service"
python demo/slack_demo.py search "Redis caching"
python demo/slack_demo.py status
```

---

## Sample Interactions

### `/cohezion ask`

```
Developer: /cohezion ask How do I implement rate limiting in FastAPI with Redis?

Cohezion: To implement rate limiting in FastAPI with Redis:

1. Install dependencies: pip install fastapi-limiter redis

2. Initialize on startup:
   @app.on_event("startup")
   async def startup():
       redis = aioredis.from_url("redis://localhost")
       await FastAPILimiter.init(redis)

3. Apply to routes:
   @app.get("/api/data")
   @limiter.limit("100/minute")
   async def get_data(request: Request): ...

⚡ IGPU · 187ms · $0.0000
```

### `/cohezion review`

```
Developer: /cohezion review Add OAuth2 PKCE flow — 847 lines changed

Cohezion (thread):
  ⚙ Orchestrator: Plan ready — complexity HIGH, 4 phases
  🔬 Analyst: 2 high risks: token leakage, CSRF. 3 vault patterns found.
  🔨 Engineer: 5 patches, 91% confidence

  *Cohezion Code Review Complete* (4.8s)
  • Complexity: HIGH  • High risks: 2  • Patches: 5  • Cost: $0.0000

  Top Patch: src/auth/pkce.py
  Generate and store PKCE verifier securely...
```

### `/cohezion status`

```
🔵 Cohezion AMD Silicon Status

✅ NPU  :13306  llama3.2-1b-FLM  · 42 TPS
✅ iGPU :13307  deepseek-r1-8b   · ~200ms
✅ CPU  :13309  Gemma-4-31B      · ~800ms

SemanticCache (FLUME VAE 256D): 94% hit rate
Cohezion Package: ✅ available

🚀 All tiers online — $0.00/query
```

---

## File Structure

```
slack-cohezion-agent/
├── app.py                    # Slack Bolt app — slash commands + @mention
├── mcp_server.py             # MCP server — the qualifying integration
├── requirements.txt
├── .env.example
├── pyrightconfig.json
├── shared/
│   ├── cohezion_bridge.py    # AMD silicon + SemanticCache bridge
│   └── cohezion_mcp_client.py  # MCP tool protocol client
├── handlers/
│   ├── ask_handler.py        # Q&A (NPU→iGPU→CPU routing)
│   ├── review_handler.py     # 3-agent code review pipeline
│   ├── search_handler.py     # FLUME VAE semantic search
│   └── status_handler.py     # AMD silicon health (Block Kit)
└── demo/
    └── slack_demo.py         # Run without Slack credentials
```

---

## Judging Criteria Alignment

| Criterion | Implementation |
|---|---|
| **Technological Implementation** | MCP server + Slack Bolt SDK + AMD silicon routing + Block Kit UI |
| **Design (UX)** | Incremental thread updates, Block Kit formatting, typing indicators |
| **Potential Impact** | $0 enterprise AI for any Slack workspace — removes cost barrier for AI adoption |
| **Quality of Idea** | MCP as protocol bridge enables multi-agent compound loops inside Slack; novel beyond simple chatbot |

---

## Track: New Slack Agent

This submission uses **MCP server integration** as the qualifying technology:

- `mcp_server.py` runs as a standalone HTTP service exposing 4 Cohezion tools
- `shared/cohezion_mcp_client.py` implements the MCP client protocol
- The Slack bot calls tools via MCP — fully decoupled, discoverable by any MCP host
- Graceful fallback: when MCP server is offline, client dispatches directly (no service dependency)
