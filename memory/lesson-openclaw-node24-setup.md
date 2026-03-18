---
title: OpenClaw Installation - Node 24 Required
date: 2026-03-14
tags: [tooling, openclaw, nodejs, nvm, setup, playwright, mcp]
aspect: knower
neural:
  activation: 0.6
  stage: emerging
  synapse_in: 1
  synapse_out: 2
---

# OpenClaw Installation - Node 24 Required

## Problem

OpenClaw requires Node 22.16+ (Node 24 recommended), but the system had Node 20 installed.

## Solution

1. **Install Node 24 via nvm**:
   ```bash
   source ~/.nvm/nvm.sh
   nvm install 24
   nvm alias default 24
   nvm use 24
   ```

2. **Install OpenClaw**:
   ```bash
   npm install -g openclaw
   ```

3. **Update .nvmrc** (if project-specific):
   ```bash
   echo "24" > .nvmrc
   ```

## Key Learnings

- OpenClaw 2026.3.12+ requires Node 24 (not just Node 22)
- nvm must be sourced in shell: `source ~/.nvm/nvm.sh`
- Global packages are installed per-Node-version
- The `.nvmrc` file triggers auto-switch via nvm

## Running OpenClaw

```bash
source ~/.nvm/nvm.sh && nvm use 24
openclaw gateway --allow-unconfigured &  # Start gateway
openclaw status                            # Check status
```

## Token for Dashboard

Located in `~/.openclaw/openclaw.json` under `gateway.auth.token`.

## Troubleshooting

- "command not found" → nvm not initialized in shell startup file
- Wrong Node version → Check `.nvmrc` in current directory and parent directories
- "ECONNREFUSED" → Gateway not started, run `openclaw gateway`

---

# Playwright MCP Server Setup

## Installed Packages

- `@playwright/mcp` v0.0.68 (official Microsoft package)
- `playwright` v1.58.2 (browser automation)
- Chromium, Firefox, WebKit browsers installed

## Configuration

Two MCP config files created:

1. `~/.mcp.json` - global config
2. `/home/mike-anderson/dev/cohezion/mcp_servers.json` - project config

```json
{
  "mcpServers": {
    "playwright": {
      "command": "/home/mike-anderson/.nvm/versions/node/v24.14.0/bin/playwright-mcp",
      "args": ["--browser", "chromium", "--headed", "--timeout-navigation", "30000", "--timeout-action", "10000"]
    }
  }
}
```

## Available Tools (via MCP)

The Playwright MCP provides browser automation tools that can be used in Claude Code sessions:
- `playwright_navigate` - Navigate to URL
- `playwright_snapshot` - Get DOM snapshot with element refs
- `playwright_click` - Click element by ref
- `playwright_fill` - Fill input field
- `playwright_screenshot` - Take screenshot
- And many more...

## Testing

To test the Playwright MCP server:
```bash
# Start MCP server manually
playwright-mcp --browser chromium --port 3001
```

## Ollama Cloud Models

After onboarding, available cloud models include:
- `kimi-k2.5:cloud`
- `minimax-m2.5:cloud`
- `glm-5:cloud`
- `qwen3.5:cloud`
- And many local models (glm-4.7-flash, deepseek-r1, etc.)

Sign in with `ollama signin` to access cloud models.