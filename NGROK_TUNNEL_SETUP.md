# Ngrok Tunnel Setup for Obsidian MCP Server

## ✓ Status: ACTIVE

- **Public URL**: `https://yaretzi-unconvoluted-overweakly.ngrok-free.dev`
- **MCP Endpoint**: `https://yaretzi-unconvoluted-overweakly.ngrok-free.dev/mcp`
- **Local MCP Server**: `http://localhost:8360/mcp`
- **Tunnel PID**: 1257097
- **Created**: 2026-02-09 02:14:38 UTC

## Next Steps

### 1. Configure claude.ai Custom Connector

1. Go to **https://claude.ai** (click your profile icon)
2. Select **Settings** → **Connectors** (or **Developer Settings**)
3. Click **"Add custom connector"** (or **"Add MCP server"**)
4. Fill in:
   - **Name**: `obsidian-vault`
   - **URL**: `https://yaretzi-unconvoluted-overweakly.ngrok-free.dev/mcp`
   - **Authentication**: None (unless you configured auth on MCP server)
5. Click **Save** or **Connect**

You should now be able to use Obsidian Vault resources in claude.ai!

### 2. Configure Claude Code (Optional)

To access the vault from Claude Code CLI across all your projects:

```bash
# Add user-scoped MCP server (available in all projects)
claude mcp add --transport http --scope user obsidian-vault \
  https://yaretzi-unconvoluted-overweakly.ngrok-free.dev/mcp
```

Or if you configured Bearer token auth on the MCP server:

```bash
claude mcp add --transport http --scope user obsidian-vault \
  https://yaretzi-unconvoluted-overweakly.ngrok-free.dev/mcp \
  --header "Authorization: Bearer YOUR_TOKEN_HERE"
```

Verify it works:
```bash
claude mcp ls
```

### 3. Keep Tunnel Alive (Optional)

The tunnel is currently running as process 1257097. To keep it persistent:

**Option A: Let it run (auto-restarts on reconnect)**
- Tunnel will stay active for ~8 hours on ngrok free tier
- To restart manually: `uv run scripts/setup_ngrok_tunnel.py`

**Option B: Stop and restart**
```bash
uv run scripts/setup_ngrok_tunnel.py --stop
uv run scripts/setup_ngrok_tunnel.py
```

**Option C: Upgrade to ngrok Pro (permanent URLs)**
- Upgrade at https://dashboard.ngrok.com
- Pro URLs don't expire
- Recommended for production use

## Technical Details

### Architecture

```
┌─ Local MCP Server ────┐
│   localhost:8360      │
│   (Obsidian Vault)    │
└──────────┬────────────┘
           │
           ▼
┌─ Ngrok Local Agent ───┐
│   (Tunnel TCP Proxy)  │
└──────────┬────────────┘
           │ HTTPS
           ▼
┌─ Ngrok Edge Servers ──┐
│   (Public Endpoint)   │
└──────────┬────────────┘
           │
      ┌────┴─────────────────┐
      │                       │
      ▼                       ▼
   claude.ai            Claude Code
```

### Configuration Files

- **Tunnel Config**: `~/.ngrok2/ngrok.yml` (authtoken stored)
- **Tunnel Setup Script**: `scripts/setup_ngrok_tunnel.py` (uv-executable)
- **Environment**: `.env.ngrok` (tunnel URLs)

### MCP Protocol

The tunnel proxies the MCP protocol (JSON-RPC 2.0 over HTTP SSE):

```
POST /mcp HTTP/2
Content-Type: application/json
Accept: application/json, text/event-stream

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {...}
}
```

## Troubleshooting

### Tunnel stopped working

**Symptom**: Connection refused or timeout

**Solution**:
```bash
# Check tunnel status
ps aux | grep ngrok

# Restart tunnel
uv run scripts/setup_ngrok_tunnel.py --stop
uv run scripts/setup_ngrok_tunnel.py
```

### New public URL every restart

**Expected on ngrok free tier** (URLs rotate every 8 hours)

**Solution**:
1. Update `.env.ngrok` with new URL
2. Reconfigure in claude.ai settings
3. Re-run `claude mcp add` command for Claude Code
4. Consider ngrok Pro for stable URLs

### Authentication issues

**Symptom**: 401 Unauthorized from claude.ai

**Solution**:
- Check MCP server auth requirements
- If needed, add Bearer token to claude.ai connector settings
- Or configure header in Claude Code: `--header "Authorization: Bearer TOKEN"`

### Firewall/Network issues

**Symptom**: Can reach tunnel locally but not from claude.ai

**Solution**:
- Verify tunnel is running: `curl https://YOUR_TUNNEL_URL`
- Check ngrok logs: `cat /tmp/ngrok_tunnel.log`
- Ensure local MCP server is responding: `curl http://localhost:8360/mcp`

## Security Notes

⚠️ **Keep .env.ngrok private!**
- Contains your public tunnel URL
- Do NOT commit to version control
- Treat like API credentials

The tunnel URL is publicly accessible but:
- Only proxies to your local MCP server
- Shares Obsidian vault resources only
- No sensitive data exposed beyond what MCP server exposes

## References

- [Ngrok Documentation](https://ngrok.com/docs)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io)
- [Claude Code MCP Integration](https://modelcontextprotocol.io/claude-code)
