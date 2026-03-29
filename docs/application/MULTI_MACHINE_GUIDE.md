# Continuing Development From Another Machine

## Quick Clone & Setup (5 minutes)

```bash
# 1. Clone the repo
git clone git@github.com:manderson240/cohezion.git
cd cohezion

# 2. Set up Python environment
uv venv && source .venv/bin/activate
uv pip install -e .

# 3. Copy your .env (from this machine or create fresh)
cp /path/to/.env .env
# Required vars: HF_TOKEN, KAGGLE_USERNAME, KAGGLE_KEY
# Optional: DUCKDNS_TOKEN, MCP_API_KEY

# 4. Verify it works
uv run pytest tests/ -q --co | tail -5  # Count tests (should be ~5,000+)
uv run python demo/quickstart.py         # Run 50-episode training demo
```

## If You Want the Webapp

```bash
# 5. Install Node.js dependencies and build
cd src/web/anima_dashboard
npm install
npm run build

# 6. Run locally
npm run start
# Visit http://localhost:3000/genesis
```

## Key Tools & Versions

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | System or pyenv |
| uv | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 25+ | `nvm install 25` or Linuxbrew |
| Git | 2.40+ | System |
| Ollama | Latest | `curl -fsSL https://ollama.ai/install.sh \| sh` (optional, for local models) |

## Branch Structure

```
main                              ← All Genesis Engine work merged here (current)
challenge/nvidia-nemotron-reasoning ← Nemotron competition (stashed changes)
spec/genesis-engine               ← Origin branch (now merged to main)
spec/luma-amd-speedrun            ← AMD GPU kernel work
```

## Stashed Work Recovery

The nemotron-reasoning work was stashed before the Genesis merge:

```bash
git stash list
# stash@{0}: On challenge/nvidia-nemotron-reasoning: nemotron-reasoning-wip-before-genesis-merge

# To recover:
git checkout challenge/nvidia-nemotron-reasoning
git stash pop
```

## Running the Full System

### Minimal (demo only)
```bash
uv run python demo/quickstart.py   # Train
uv run python demo/evaluate.py     # Evaluate
uv run python demo/export_dataset.py  # Export DPO data
```

### Full API server
```bash
uv run uvicorn cohezion.api:app --reload --port 8080
# API at http://localhost:8080
# Docs at http://localhost:8080/docs
```

### Full system (API + DB + Webapp)
```bash
# Terminal 1: SurrealDB
surreal start --log info file:data/surreal.db

# Terminal 2: API
uv run uvicorn cohezion.api:app --reload --port 8080

# Terminal 3: Webapp
cd src/web/anima_dashboard && npm run dev

# Terminal 4: Local models (optional)
ollama serve
```

## Tests

```bash
# Full suite (~5,000+ tests, ~7 min)
uv run pytest tests/ -q

# Quick smoke test (~30 sec)
uv run pytest tests/unit/ -q

# Specific module
uv run pytest tests/physics/ -v
uv run pytest tests/universe/ -v
uv run pytest tests/compound/ -v

# With coverage
uv run pytest tests/ -q --cov=src/cohezion --cov-report=html
```

## Hosting (From the New Machine)

If you want to host the webapp from a different machine:

### Option A: Tailscale Funnel (easiest)
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Build and start webapp
cd src/web/anima_dashboard && npm run build && npm run start &

# Expose to internet
sudo tailscale funnel --bg 3000
# URL will be: https://<machine-name>.<tailnet>.ts.net/
```

### Option B: Caddy + Your Domain
```bash
# Install Caddy
sudo apt install -y caddy  # or download from caddyserver.com

# Configure (edit /etc/caddy/Caddyfile)
cohezion.duckdns.org {
    reverse_proxy localhost:3000
    encode gzip zstd
}

# Update Duck DNS to point to new machine's IP
curl "https://www.duckdns.org/update?domains=cohezion&token=$DUCKDNS_TOKEN&ip="

# Start
sudo systemctl enable --now caddy
```

## Framework Desktop Services (Current Host)

These systemd services are running on your Framework Desktop:

```bash
# Check status
systemctl status cohezion-genesis  # Next.js on port 3000
systemctl status caddy             # Reverse proxy (currently stopped, Funnel active)

# Restart after changes
cd src/web/anima_dashboard && npm run build
sudo systemctl restart cohezion-genesis

# View logs
journalctl -u cohezion-genesis -f
journalctl -u caddy -f

# Tailscale Funnel status
tailscale funnel status
```

## Claude Code Development

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Start a session in the repo
cd ~/dev/cohezion
claude

# The repo has extensive CLAUDE.md instructions that guide Claude automatically
# Key skills available: /spec, /learn, /deploy, /heal, /audit, /scout
```

## Key Contacts & Links

| Resource | URL |
|----------|-----|
| GitHub repo | https://github.com/manderson240/cohezion |
| Live webapp | https://frameworkdesktop.tail54eb71.ts.net/ |
| Genesis Engine | https://frameworkdesktop.tail54eb71.ts.net/genesis |
| Anthropic application | https://job-boards.greenhouse.io/anthropic/jobs/5061517008 |
| Duck DNS dashboard | https://www.duckdns.org |
| Kaggle profile | https://www.kaggle.com/manderson240 |
