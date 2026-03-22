# Deploying the Cohezion Demo

This guide explains how to deploy the Cohezion showcase to `cohezion.duckdns.org`.

## Prerequisites

1. **DuckDNS Account**: Register at https://www.duckdns.org with Google OAuth
2. **DuckDNS Token**: Get from dashboard after login
3. **Domain Registered**: `cohezion.duckdns.org` (already done)

## Setup

### 1. Add DuckDNS Token

Add to `.env`:
```bash
DUCKDNS_TOKEN=your-token-here
```

### 2. Enable DuckDNS Updater

```bash
chmod +x scripts/update_duckdns.sh

# Add to crontab (updates every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh") | crontab -
```

### 3. Deploy Demo Server

**Option A: Marimo (Interactive Notebooks)**
```bash
# Serve Marimo notebooks on port 8080
uv run marimo run notebooks/marimo/flume_showcase.py --host 0.0.0.0 --port 8080
```

**Option B: FastAPI + Marimo (Full Demo)**
```bash
# Start the Cohezion API server
uv run uvicorn cohezion.api.main:app --host 0.0.0.0 --port 8080
```

### 4. Reverse Proxy with Caddy (HTTPS)

Install Caddy and create `/etc/caddy/Caddyfile`:
```
cohezion.duckdns.org {
    reverse_proxy localhost:8080
}
```

```bash
sudo systemctl enable --now caddy
```

Caddy will automatically provision Let's Encrypt SSL certificates.

## Verify Deployment

1. Visit https://cohezion.duckdns.org
2. Check Marimo notebooks are accessible
3. Verify SurrealDB queries work

## Showcase Contents

| Demo | Path | Description |
|------|------|-------------|
| FLUME Showcase | `/notebooks/flume_showcase` | 12D physics, trajectories |
| Swarm Experience | `/notebooks/swarm_experience` | Multi-agent debate |
| API Endpoints | `/docs` | FastAPI Swagger UI |

## Troubleshooting

- **DNS not resolving**: Check `scripts/update_duckdns.sh` log in `logs/duckdns.log`
- **HTTPS issues**: Run `sudo caddy reload`
- **Port blocked**: Check firewall: `sudo ufw allow 80,443/tcp`
