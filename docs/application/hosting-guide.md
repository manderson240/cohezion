# Hosting Guide: Cohezion Genesis Engine at cohezion.duckdns.org

This guide covers hosting the Next.js Genesis Engine webapp so external visitors
(such as Anthropic interviewers) can access it at `https://cohezion.duckdns.org`.

---

## Current State (as of 2026-03-29)

| Component              | Status                                                    |
|------------------------|-----------------------------------------------------------|
| Duck DNS domain        | `cohezion.duckdns.org` registered, resolves to `68.175.143.201` (current public IP) |
| Duck DNS token         | **NOT configured** -- `DUCKDNS_TOKEN` missing from `.env` |
| Duck DNS cron          | **NOT running** -- no crontab entry for `update_duckdns.sh` |
| Duck DNS update script | EXISTS at `scripts/update_duckdns.sh`                     |
| Caddy                  | Installed (v2.11.1 at `~/.local/bin/caddy`), service **inactive** |
| Caddy config           | `/etc/caddy/Caddyfile` exists but is **empty** (autosave.json present) |
| cloudflared            | Installed (v2026.2.0), no credentials or active tunnel    |
| Tailscale Funnel       | Active, proxying port 8360 and 4040 via `frameworkdesktop.tail54eb71.ts.net` |
| Next.js app            | Built (BUILD_ID: `T3s6BliT_UA-j4EDRuQqT`), deps installed |
| Nginx                  | **NOT installed** (containerized config exists at `ops/container/nginx.conf`) |
| certbot                | **NOT installed**                                         |
| UFW firewall           | **Inactive**                                              |
| Node.js                | v25.8.1 (via Linuxbrew)                                   |
| OS                     | Ubuntu 24.04.4 LTS                                        |
| Network                | LAN IP `192.168.86.25` (eth) / `192.168.86.30` (wifi), gateway `192.168.86.1` |

**Bottom line:** The domain is registered and points to the correct IP. The Duck DNS
update script exists but is not wired up. No reverse proxy is actively serving
the webapp. Two approaches are documented below.

---

## Approach A: Caddy + Duck DNS (Recommended)

Caddy is already installed and handles HTTPS certificates automatically via
Let's Encrypt with zero extra tooling. This is the simplest path.

### A.1 -- Configure Duck DNS Token

1. Log in to https://www.duckdns.org (Google OAuth)
2. Copy your token from the dashboard
3. Add to `/home/mike-anderson/dev/cohezion/.env`:

```bash
DUCKDNS_TOKEN=your-actual-token-here
```

### A.2 -- Enable Duck DNS Dynamic IP Updates

The update script already exists at `scripts/update_duckdns.sh`. Make it executable
and add it to crontab:

```bash
chmod +x /home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh

# Add cron job to update IP every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh") | crontab -

# Verify it was added
crontab -l

# Run once manually to test
/home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh
cat /home/mike-anderson/dev/cohezion/logs/duckdns.log
```

The script reads `DUCKDNS_TOKEN` from `.env` and calls the Duck DNS update API.
It logs results to `logs/duckdns.log`.

### A.3 -- Build the Next.js App for Production

```bash
cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard

# Install dependencies (if not already done)
npm install

# Build for production
npm run build

# Test locally -- should start on port 3000
npm run start
# Visit http://localhost:3000/genesis to verify, then Ctrl+C
```

The production build is a standalone Node.js server. Default port is 3000.

### A.4 -- Create a Systemd Service for the Next.js App

```bash
sudo tee /etc/systemd/system/cohezion-genesis.service > /dev/null << 'EOF'
[Unit]
Description=Cohezion Genesis Engine (Next.js)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mike-anderson
WorkingDirectory=/home/mike-anderson/dev/cohezion/src/web/anima_dashboard
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=HOSTNAME=127.0.0.1
ExecStart=/home/linuxbrew/.linuxbrew/bin/node node_modules/.bin/next start --port 3000
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cohezion-genesis

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cohezion-genesis.service
sudo systemctl start cohezion-genesis.service

# Verify it started
systemctl status cohezion-genesis.service
curl -s http://localhost:3000/genesis | head -20
```

### A.5 -- Configure Caddy as Reverse Proxy

Write the Caddyfile:

```bash
sudo tee /etc/caddy/Caddyfile > /dev/null << 'EOF'
cohezion.duckdns.org {
    reverse_proxy localhost:3000

    # Compression for faster Three.js asset loading
    encode gzip zstd

    # WebSocket support (if needed by Three.js hot reload, etc.)
    @websockets {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websockets localhost:3000

    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    # Logging
    log {
        output file /var/log/caddy/genesis.log
        format json
    }
}
EOF
```

Create the log directory and start Caddy:

```bash
sudo mkdir -p /var/log/caddy

sudo systemctl enable caddy
sudo systemctl start caddy

# Or reload if already running
sudo systemctl reload caddy

# Verify
systemctl status caddy
```

Caddy automatically obtains and renews Let's Encrypt TLS certificates. No certbot
needed. It uses the HTTP-01 challenge, which requires ports 80 and 443 to be
reachable from the internet.

### A.6 -- Router Port Forwarding

Your machine is behind a NAT router at `192.168.86.1` (likely Google Wifi or Nest).
You must forward ports 80 and 443 from the router to this machine.

1. Open your router admin: http://192.168.86.1 (or use the Google Home app)
2. Navigate to Advanced Networking / Port Forwarding (or Port Management)
3. Add two rules:

| External Port | Internal IP    | Internal Port | Protocol |
|---------------|----------------|---------------|----------|
| 80            | 192.168.86.25  | 80            | TCP      |
| 443           | 192.168.86.25  | 443           | TCP      |

Use the wired IP (`192.168.86.25`) for reliability. If using Google Wifi/Nest,
port forwarding is in the Google Home app under Wi-Fi > Advanced Networking.

**Important:** Caddy needs port 80 for the ACME HTTP-01 challenge even though all
real traffic goes through 443. If you cannot forward port 80, use the DNS-01
challenge with a Caddy Duck DNS plugin instead (see Appendix B).

### A.7 -- Firewall Configuration

UFW is currently inactive. If you enable it:

```bash
sudo ufw allow 80/tcp    # Required for Let's Encrypt ACME challenge
sudo ufw allow 443/tcp   # HTTPS traffic
sudo ufw allow 22/tcp    # SSH (don't lock yourself out)
sudo ufw enable
sudo ufw status
```

### A.8 -- Verify End-to-End

```bash
# Check DNS resolution
host cohezion.duckdns.org

# Test HTTPS access (from the machine itself)
curl -I https://cohezion.duckdns.org

# Test genesis route
curl -s https://cohezion.duckdns.org/genesis | head -20

# Check certificate
echo | openssl s_client -connect cohezion.duckdns.org:443 -servername cohezion.duckdns.org 2>/dev/null | openssl x509 -noout -subject -dates
```

From a phone or external device, visit: `https://cohezion.duckdns.org/genesis`

---

## Approach B: Tailscale Funnel (Fastest, No Port Forwarding Needed)

Tailscale Funnel is already configured on this machine and requires NO router
port forwarding, NO Duck DNS, and NO certificates. Tailscale handles everything.

The current Funnel routes are:
- `https://frameworkdesktop.tail54eb71.ts.net` -> `localhost:8360`
- `https://frameworkdesktop.tail54eb71.ts.net:8443` -> `localhost:4040`

To serve the Genesis app via Tailscale Funnel:

```bash
# Start Next.js on port 3000
cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard
npm run start &

# Add a Funnel route (this replaces the existing :443 route)
sudo tailscale funnel --bg 3000
```

The URL would be: `https://frameworkdesktop.tail54eb71.ts.net`

**Pros:**
- Works immediately, no DNS/router/firewall configuration
- Automatic HTTPS with Tailscale-managed certificates
- No port forwarding required (works behind any NAT)

**Cons:**
- URL is `frameworkdesktop.tail54eb71.ts.net` instead of `cohezion.duckdns.org`
- Replaces the existing MCP server Funnel route on port 443
- Tailscale must remain running

**To use both the MCP server and Genesis simultaneously on Funnel:**

```bash
# Serve Genesis on the default HTTPS port
sudo tailscale funnel --set-path /genesis http://localhost:3000/genesis

# Keep MCP on port 8443
sudo tailscale funnel --set-path / http://localhost:8360
```

Note: Path-based routing with Next.js requires configuring `basePath` in
`next.config.ts` if the app expects to be at `/` but is served from `/genesis`.

---

## Approach C: Cloudflare Tunnel + Duck DNS (Most Robust)

This uses `cloudflared` (already installed, v2026.2.0) to create a tunnel that
bypasses NAT entirely -- no port forwarding needed. Previous deployment scripts
exist at `scripts/deploy_tunnel.sh` and `docs/archive/TUNNEL_SETUP.md`.

### C.1 -- Authenticate and Create Tunnel

```bash
# Authenticate (opens browser)
cloudflared tunnel login

# Create a tunnel named cohezion-genesis
cloudflared tunnel create cohezion-genesis
# Note the Tunnel ID and credentials file path
```

### C.2 -- Configure the Tunnel

```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: cohezion-genesis
credentials-file: /home/mike-anderson/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: cohezion.duckdns.org
    service: http://localhost:3000
  - service: http_status:404
EOF
```

### C.3 -- Set Up DNS

For Cloudflare Tunnel to work with `cohezion.duckdns.org`, the domain needs a
CNAME record pointing to `<TUNNEL_ID>.cfargotunnel.com`. Since Duck DNS only
supports A records (not CNAME), this approach requires either:

1. Using a Cloudflare-managed domain instead (e.g., `cohezion.pages.dev`)
2. Running `cloudflared` in `--proxy-dns` mode to handle DNS locally
3. Using the Duck DNS A record with a direct Caddy reverse proxy (Approach A)

**Recommendation:** If you want the `cohezion.duckdns.org` domain specifically,
use Approach A (Caddy). If you don't care about the domain name, Approach B
(Tailscale Funnel) is the fastest.

---

## Quick Reference: Start / Stop / Restart

### Using Approach A (Caddy + systemd):

```bash
# Start everything
sudo systemctl start cohezion-genesis caddy

# Stop everything
sudo systemctl stop cohezion-genesis caddy

# Restart the Next.js app (after code changes)
cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard
npm run build
sudo systemctl restart cohezion-genesis

# Restart Caddy (after config changes)
sudo systemctl reload caddy

# View Next.js logs
journalctl -u cohezion-genesis -f

# View Caddy logs
journalctl -u caddy -f
tail -f /var/log/caddy/genesis.log

# View Duck DNS update logs
tail -f /home/mike-anderson/dev/cohezion/logs/duckdns.log

# Check service health
systemctl status cohezion-genesis caddy
```

### Using Approach B (Tailscale Funnel):

```bash
# Start
cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard
npm run start &
sudo tailscale funnel --bg 3000

# Stop
sudo tailscale funnel reset
kill %1  # or kill the node process

# Check status
tailscale funnel status
```

---

## Preparing for an Interview Demo

Checklist to run the day before sharing the link:

1. **Rebuild the app** (picks up any recent code changes):
   ```bash
   cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard
   npm run build
   ```

2. **Verify Duck DNS IP is current**:
   ```bash
   curl -s ifconfig.me          # Your public IP
   host cohezion.duckdns.org    # Should match
   # If mismatch, run the updater manually:
   /home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh
   ```

3. **Start services** (if not already running):
   ```bash
   sudo systemctl start cohezion-genesis caddy
   ```

4. **Test from phone or external network**:
   - Visit `https://cohezion.duckdns.org/genesis`
   - Verify the Bloch sphere and fiber bundle explorer render
   - Check that the cosmogony sequence plays
   - Test on both mobile and desktop browsers

5. **Check TLS certificate**:
   ```bash
   echo | openssl s_client -connect cohezion.duckdns.org:443 2>/dev/null | grep -i verify
   ```

6. **Monitor during the interview**:
   ```bash
   # In a tmux pane
   journalctl -u cohezion-genesis -f
   ```

---

## Troubleshooting

### DNS not resolving

```bash
# Check what Duck DNS returns
host cohezion.duckdns.org
# Check current public IP
curl -s ifconfig.me
# Force update
/home/mike-anderson/dev/cohezion/scripts/update_duckdns.sh
cat /home/mike-anderson/dev/cohezion/logs/duckdns.log
```

If the IP changed and the cron is not running, the A record will be stale.

### HTTPS certificate not provisioning (Caddy)

Caddy auto-provisions Let's Encrypt certs on first request. If it fails:

```bash
# Check Caddy logs for ACME errors
journalctl -u caddy --since "5 minutes ago"

# Common cause: port 80 not reachable from the internet
# Test: from an external machine, `curl http://cohezion.duckdns.org`
# If it times out, port forwarding is not configured on the router

# Alternative: Use DNS-01 challenge (no port 80 needed)
# See Appendix B below
```

### Next.js app crashes or won't start

```bash
# Check logs
journalctl -u cohezion-genesis -n 50

# Test manually
cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard
npm run start
# Look for errors about missing dependencies or port conflicts

# Rebuild
npm run build 2>&1 | tail -20

# Check if port 3000 is already in use
ss -tlnp | grep :3000
```

### Site loads but Three.js visualizations are blank

This usually means WebGL context failed or large assets timed out.

```bash
# Check browser console for errors (from a client machine)
# Common fixes:
# - Ensure Caddy gzip/zstd encoding is enabled (reduces Three.js bundle size)
# - Add longer proxy timeouts for WebSocket connections
# - Check that the production build included all chunks:
ls -la /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/.next/build/chunks/
```

### Port forwarding not working

```bash
# Test from an external service
# On your phone (not on home wifi), visit: http://cohezion.duckdns.org
# Or use an online port checker: https://www.yougetsignal.com/tools/open-ports/
# Check port 80 and 443 for your public IP

# If using Google Wifi/Nest:
# Google Home app > Wifi > Settings > Advanced Networking > Port Management
# Note: Some ISPs block port 80/443 -- if so, use Tailscale Funnel (Approach B)
```

---

## Appendix A: Next.js Configuration for Production

The current `next.config.ts` is minimal. For production hosting, consider adding:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Output standalone build for smaller deployments
  output: "standalone",

  // If serving from a subpath (e.g., behind Tailscale Funnel path routing)
  // basePath: "/genesis",

  // Disable server-side image optimization if not using Vercel
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

The `output: "standalone"` option creates a self-contained build in
`.next/standalone/` that includes only the necessary `node_modules`. This is
useful if you want to deploy without the full `node_modules` directory.

## Appendix B: Caddy DNS-01 Challenge (No Port 80 Required)

If your ISP blocks port 80, use the DNS-01 ACME challenge via a Caddy plugin.
This requires building Caddy with the Duck DNS module:

```bash
# Install xcaddy (Caddy build tool)
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build Caddy with Duck DNS plugin
xcaddy build --with github.com/caddy-dns/duckdns

# Move the custom Caddy binary
sudo mv caddy /usr/local/bin/caddy
```

Then update the Caddyfile:

```
cohezion.duckdns.org {
    tls {
        dns duckdns {env.DUCKDNS_TOKEN}
    }
    reverse_proxy localhost:3000
    encode gzip zstd
}
```

And set the token in Caddy's environment:

```bash
sudo mkdir -p /etc/caddy
echo "DUCKDNS_TOKEN=your-token-here" | sudo tee /etc/caddy/env
sudo systemctl set-environment DUCKDNS_TOKEN=your-token-here
sudo systemctl restart caddy
```

## Appendix C: File Locations Reference

| File                                          | Purpose                        |
|-----------------------------------------------|--------------------------------|
| `src/web/anima_dashboard/`                    | Next.js app root               |
| `src/web/anima_dashboard/package.json`        | Dependencies and scripts       |
| `src/web/anima_dashboard/next.config.ts`      | Next.js configuration          |
| `src/web/anima_dashboard/src/app/genesis/`    | Genesis route (`/genesis`)     |
| `src/web/anima_dashboard/src/components/genesis/` | Genesis visualization components |
| `src/web/anima_dashboard/.next/`              | Production build output        |
| `scripts/update_duckdns.sh`                   | Duck DNS IP updater            |
| `scripts/deploy_tunnel.sh`                    | Cloudflare tunnel deployer     |
| `ops/container/nginx.conf`                    | Containerized nginx config     |
| `docs/DEPLOY.md`                              | Previous deployment guide      |
| `docs/archive/TUNNEL_SETUP.md`               | Cloudflare tunnel setup guide  |
| `/etc/caddy/Caddyfile`                        | Caddy reverse proxy config     |
| `/etc/systemd/system/cohezion-genesis.service`| Next.js systemd unit (to create) |
