# Cloud Vault MCP - Quick Reference Card

## 🚀 Server Startup (Copy-Paste Ready)

```bash
# Terminal 1: Start server
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
export MCP_PORT=8360
export MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263
uv run python -m src.mcp_server.main
```

Expected: Server starts on port 8360 ✓

## ✅ Verify Integration

```bash
# Terminal 2: Run all tests
python3 /home/mike-anderson/dev/cohezion/cloud-vault-mcp/test_mcp_integration.py
```

Expected: "All tests passed!" ✓

## 🔧 Common Commands

```bash
# Check if server is running
curl http://localhost:8360

# List vault contents
curl -X POST http://localhost:8360/call/vault_list \
  -H "Content-Type: application/json" -d '{"path":"decisions"}'

# Search vault
curl -X POST http://localhost:8360/call/vault_search \
  -H "Content-Type: application/json" -d '{"query":"token optimization"}'

# Check logs
tail -50 /tmp/mcp_server.log

# Kill server
pkill -f "python.*mcp_server"
```

## 📋 MCP Tools Quick Guide

| Tool | Usage | Example |
|------|-------|---------|
| `vault_read` | Read file content | `vault_read("decisions/2026-02-09-something.md")` |
| `vault_search` | Search notes | `vault_search("token optimization", max_results=10)` |
| `vault_list` | List directory | `vault_list("decisions")` |
| `vault_write` | Create/update file | `vault_write("decisions/new.md", "content")` |
| `compound_record_decision` | Log design decision | `compound_record_decision(title="...", context="...", decision="...", reasoning="...", tags=[])` |
| `compound_record_experiment` | Log experiment | `compound_record_experiment(title="...", hypothesis="...", procedure="...", results="...", insights="...")` |
| `compound_record_pattern` | Document pattern | `compound_record_pattern(name="...", problem="...", solution="...", examples="...", trade_offs="...")` |

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Server not running - run startup command above |
| "Authorization failed" | Check API key matches in ~/.claude/mcp.json and .env |
| "Vault path not found" | Set VAULT_PATH env var: `/home/mike-anderson/vaults/cohezion-vault` |
| "Address already in use" | Kill existing: `pkill -f "python.*mcp_server"` |
| "ImportError" | Clear cache: `find . -name __pycache__ -exec rm -rf {} +` |
| Claude Code can't find tools | Restart Claude Code session after server starts |

**For detailed help**: See `TROUBLESHOOTING.md`

## 📁 Key Locations

| Item | Path |
|------|------|
| MCP Server | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/` |
| Main entry point | `src/mcp_server/main.py` |
| Configuration | `.env` (gitignored for security) |
| Claude Code config | `~/.claude/mcp.json` |
| Vault directory | `/home/mike-anderson/vaults/cohezion-vault/` |
| Server logs | `/tmp/mcp_server.log` |
| API key (for reference) | `a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263` |

## 🔐 Configuration Files

### ~/.claude/mcp.json
```json
{
  "cloud-vault-mcp": {
    "type": "http",
    "url": "http://127.0.0.1:8360",
    "headers": {
      "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
    }
  }
}
```

### Environment Variables (set before running)
```bash
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_PORT=8360
MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263
MCP_HOST=0.0.0.0
CORS_ORIGINS=*
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `MCP_CLAUDE_CODE_INTEGRATION.md` | Full integration guide (400+ lines) |
| `TROUBLESHOOTING.md` | Issue resolution guide (500+ lines) |
| `QUICK_REFERENCE.md` | This file - copy-paste commands |

## 🎯 Typical Workflow

1. **Start server** (Terminal 1)
   ```bash
   # Copy startup command from "Server Startup" section above
   ```

2. **Verify** (Terminal 2)
   ```bash
   python3 test_mcp_integration.py
   ```

3. **Use in Claude Code**
   - Tools auto-discovered ✓
   - Use vault operations to persist knowledge
   - Example: `vault_search("previous solutions")`

4. **Monitor**
   ```bash
   tail -f /tmp/mcp_server.log
   ```

5. **Stop**
   ```bash
   pkill -f "python.*mcp_server"
   ```

## ⚠️ Important Notes

- **API Key**: Plaintext in mcp.json (dev only - not production-safe)
- **HTTPS**: Not enabled (dev only - use HTTPS in production)
- **Port 8360**: Must be available (check with: `lsof -i :8360`)
- **Vault Access**: All authenticated users can access entire vault (implement ACLs in production)
- **Backups**: Vault is source of truth - keep git updated

## 📞 Get Help

- Check `TROUBLESHOOTING.md` for common issues
- Run `test_mcp_integration.py` to diagnose problems
- Review `/tmp/mcp_server.log` for error details
- See `MCP_CLAUDE_CODE_INTEGRATION.md` for detailed documentation

---

**Last Updated**: February 9, 2026
**Task**: #5 - Configure Claude Code MCP Integration
**Status**: ✅ COMPLETE
