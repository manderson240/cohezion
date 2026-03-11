---
title: Cloudflare Tunnel for Persistent MCP Remote Access
date: '2026-02-12'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Cloudflare Tunnel for Persistent MCP Remote Access'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 0.464
  stage: growing
  cluster: decisions
---

## Context

The [[cloud-vault-mcp]] server runs locally on port 8360, providing programmatic access to the Cohezion vault for Claude Code agents, automation pipelines, and future web-based interfaces. However, this server is only accessible from `localhost` -- remote access (from mobile devices, other machines, or cloud-hosted CI/CD) is impossible without additional networking.

Use cases requiring remote access:
- **Mobile research triage**: Reviewing vault state and triggering operations from a phone or tablet
- **Multi-machine development**: Accessing the MCP server from a laptop while the server runs on a desktop
- **CI/CD integration**: GitHub Actions or other cloud CI triggering MCP tools as part of automated workflows
- **Collaborative sessions**: Multiple developers or agents accessing the same vault server

Traditional approaches (port forwarding, VPN, direct public IP) each have significant drawbacks for a development workstation.

## Decision

Use **Cloudflare Tunnel** (`cloudflared`) to create a persistent, encrypted tunnel from the local MCP server to a Cloudflare-managed subdomain. This exposes port 8360 as an HTTPS endpoint without opening any inbound ports on the local machine.

Configuration:
```bash
# Install cloudflared
sudo apt install cloudflared

# Create a named tunnel
cloudflared tunnel create cohezion-mcp

# Configure the tunnel to route to local MCP server
# ~/.cloudflared/config.yml
tunnel: cohezion-mcp
credentials-file: /home/mike-anderson/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: mcp.cohezion.dev
    service: http://localhost:8360
  - service: http_status:404

# Run the tunnel
cloudflared tunnel run cohezion-mcp
```

The tunnel can be run as a systemd service for persistence across reboots.

## Consequences

**Positive:**
- **Zero inbound ports**: No firewall rules, no port forwarding, no dynamic DNS needed
- **Automatic HTTPS**: Cloudflare provides TLS termination with valid certificates
- **Persistent URL**: `mcp.cohezion.dev` (or equivalent) is stable across IP changes and reboots
- **Authentication options**: Cloudflare Access can add SSO/MFA in front of the tunnel for production use
- **Free tier available**: Cloudflare Tunnels are free for personal use

**Negative:**
- **Cloudflare dependency**: Tunnel availability depends on Cloudflare's infrastructure (mitigated by their 99.99% SLA)
- **Latency**: Adds a network hop through Cloudflare's edge (typically <50ms, acceptable for MCP tool calls)
- **Authentication required for production**: Without Cloudflare Access or bearer token verification, anyone with the URL can reach the MCP server
- **Local process must be running**: If `cloudflared` or the MCP server stops, remote access is lost

## Alternatives Considered

### Alt 1: Direct Port Forwarding (Router/Firewall)
- **Rejected**: Exposes a port on the public internet. Requires a static IP or dynamic DNS. No built-in TLS. Security risk for a development workstation.

### Alt 2: Tailscale/WireGuard VPN
- **Rejected**: Requires Tailscale client on every accessing device. Good for machine-to-machine but poor for browser-based or CI/CD access. Does not provide a public URL.

### Alt 3: ngrok
- **Rejected**: Free tier has rate limits, rotating URLs, and no custom domains. Paid tier ($8/month) offers less than Cloudflare's free tier.

### Alt 4: SSH Reverse Tunnel to a VPS
- **Rejected**: Requires maintaining a VPS ($5-20/month). SSH tunnels are fragile -- they drop on network changes and require reconnection logic. No built-in TLS or authentication.

## See Also

- [[mcp-infrastructure-architecture]]
- [[mcp-model-context-protocol]]
- [[troubleshooting-mcp-infrastructure]]

## Related

- [[cloud-vault-mcp]] — the MCP server exposed remotely via the Cloudflare tunnel
- [[mcp-infrastructure-architecture]] — the full architecture this tunnel decision extends to remote access
- [[mcp-tunnel/SETUP_GUIDE|MCP Tunnel Setup Guide]] — deployment guide implementing this decision
