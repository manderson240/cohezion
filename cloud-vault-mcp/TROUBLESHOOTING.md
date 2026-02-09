# Cloud Vault MCP - Troubleshooting Guide

## Quick Diagnostics

### Test All Components

```bash
# 1. Run comprehensive integration tests
python3 test_mcp_integration.py

# Expected: All tests pass
```

### Is the Server Running?

```bash
# Check process
ps aux | grep "python.*mcp\|uvicorn" | grep -v grep

# Check port
lsof -i :8360
netstat -tlnp | grep 8360
curl http://localhost:8360

# Check logs
tail -50 /tmp/mcp_server.log
```

---

## Common Issues & Solutions

### 1. "Connection refused" or Port 8360 not responding

**Symptoms**:
- `curl http://localhost:8360` returns "Connection refused"
- Claude Code can't reach MCP server
- In logs: `ERROR: [Errno 111] Connection refused`

**Causes**:
- Server process crashed
- Wrong port in configuration
- Firewall blocking port
- Port already in use by another process

**Solutions**:

```bash
# 1. Check if server is running
ps aux | grep "mcp_server\|uvicorn"

# 2. If not running, restart it
pkill -f "python.*mcp" 2>/dev/null || true
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault \
MCP_PORT=8360 \
MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263 \
uv run python -m src.mcp_server.main > /tmp/mcp_server.log 2>&1 &

# 3. Check if port is in use
lsof -i :8360
# If another process is using it, kill it
kill -9 <PID>

# 4. Change to different port if needed
MCP_PORT=8361 uv run python -m src.mcp_server.main

# 5. Update mcp.json with new port
# ~/.claude/mcp.json: "url": "http://127.0.0.1:8361"
```

---

### 2. "Vault path does not exist" error

**Symptoms**:
- Server fails to start with: `ValueError: Vault path does not exist: /vault`
- In logs: `Vault path does not exist: /vault`

**Causes**:
- `VAULT_PATH` environment variable not set
- Wrong vault path in `.env` or environment
- Vault directory moved or deleted

**Solutions**:

```bash
# 1. Verify vault exists
ls -ld /home/mike-anderson/vaults/cohezion-vault

# 2. Check current VAULT_PATH setting
echo $VAULT_PATH
cat /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env | grep VAULT_PATH

# 3. Set correct path before starting server
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault

# 4. Update .env file
sed -i 's|VAULT_PATH=/vault|VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault|' \
  /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env

# 5. Verify and restart
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault \
MCP_PORT=8360 \
MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263 \
uv run python -m src.mcp_server.main
```

---

### 3. ModuleNotFoundError or Import Errors

**Symptoms**:
- Server fails: `ModuleNotFoundError: No module named 'starlette.middleware.trustedhosts'`
- Or: `ModuleNotFoundError: No module named 'mcp'`

**Causes**:
- Stale Python cache/bytecode
- Virtual environment not properly built
- Wrong Python version
- Missing dependencies

**Solutions**:

```bash
# 1. Clear Python cache
find /home/mike-anderson/dev/cohezion/cloud-vault-mcp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 2. Check import is correct (as of Feb 2026)
grep "from starlette.middleware" \
  /home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/main.py
# Should show: from starlette.middleware.trustedhost import TrustedHostMiddleware

# 3. Rebuild virtual environment
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
rm -rf .venv
uv sync

# 4. Test imports
python3 -c "from mcp.server.fastmcp import FastMCP; print('MCP imports OK')"
python3 -c "from starlette.middleware.trustedhost import TrustedHostMiddleware; print('Starlette imports OK')"

# 5. Restart server
```

---

### 4. "Authorization failed" or 401 error

**Symptoms**:
- HTTP 401 response from server
- "Invalid API key" errors
- "Authorization header missing" in logs

**Causes**:
- API key mismatch between `mcp.json` and server
- Auth header missing or malformed
- API key changed without updating both locations

**Solutions**:

```bash
# 1. Check API key in mcp.json
cat ~/.claude/mcp.json | grep -A2 "cloud-vault-mcp"
# Look for: "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"

# 2. Check API key in server .env
grep MCP_API_KEY /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env

# 3. Generate new API key if needed
python3 -c "import hashlib,os; print(hashlib.sha256(os.urandom(32)).hexdigest())"

# 4. Update both files with same key
NEW_KEY=$(python3 -c "import hashlib,os; print(hashlib.sha256(os.urandom(32)).hexdigest())")
sed -i "s/MCP_API_KEY=.*/MCP_API_KEY=$NEW_KEY/" \
  /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env

# 5. Update mcp.json
cat > ~/.claude/mcp.json << EOF
{
  "cloud-vault-mcp": {
    "type": "http",
    "url": "http://127.0.0.1:8360",
    "headers": {
      "Authorization": "Bearer $NEW_KEY"
    }
  }
}
EOF

# 6. Restart server
pkill -f "python.*mcp" || true
sleep 2
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
uv run python -m src.mcp_server.main > /tmp/mcp_server.log 2>&1 &
```

---

### 5. "FastMCP takes 1 positional argument but 4 were given" error

**Symptoms**:
- Server starts but crashes on first request
- In logs: `TypeError: FastMCP.streamable_http_app() takes 1 positional argument but 4 were given`

**Causes**:
- Main.py trying to call `mcp.streamable_http_app()` directly
- Stale bytecode using old main.py code

**Status**: FIXED in current version (Feb 9, 2026)

**Solution** (if still happening):
```bash
# 1. Check main.py line 39-42
cat /home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/main.py | sed -n '39,42p'

# Should show:
# mcp = create_server(config)
# FastMCP is an ASGI app directly - use it as mcp_app
# mcp_app = mcp

# If it shows: mcp_app = mcp.streamable_http_app()
# Then edit the file:

sed -i 's/mcp_app = mcp\.streamable_http_app()/mcp_app = mcp/' \
  /home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/main.py

# 2. Clear cache and restart
find /home/mike-anderson/dev/cohezion/cloud-vault-mcp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
rm -rf /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv
pkill -f "python.*mcp" || true
sleep 2
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
uv run python -m src.mcp_server.main > /tmp/mcp_server.log 2>&1 &
```

---

### 6. Server crashes on startup with "address already in use"

**Symptoms**:
- `ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8360): address already in use`

**Causes**:
- Previous server process still running
- Port 8360 held by another application

**Solutions**:

```bash
# 1. Find what's using the port
lsof -i :8360
netstat -tlnp | grep 8360

# 2. Kill the process
kill -9 <PID>

# 3. Or use a different port
MCP_PORT=8361 uv run python -m src.mcp_server.main &

# 4. Update mcp.json if port changed
sed -i 's|8360|8361|g' ~/.claude/mcp.json
```

---

### 7. Claude Code doesn't discover MCP tools

**Symptoms**:
- Claude Code running but can't find vault tools
- `/mcp list` shows no tools
- Server is running and responding

**Causes**:
- `mcp.json` not in correct location
- `mcp.json` has syntax errors
- Claude Code not reloaded after config change
- Server not advertising tools properly

**Solutions**:

```bash
# 1. Verify mcp.json location and syntax
cat ~/.claude/mcp.json | python3 -m json.tool
# Should output valid JSON without errors

# 2. Check server is responding
curl -s http://localhost:8360/ | head -20

# 3. Reload Claude Code session
# - Exit and restart Claude Code
# - Or use `claude-code --refresh-tools`

# 4. Verify mcp.json has cloud-vault-mcp entry
grep "cloud-vault-mcp" ~/.claude/mcp.json

# 5. Check server logs for tool registration
tail -100 /tmp/mcp_server.log | grep -i "tool\|register"
```

---

### 8. Vault reads return empty or wrong data

**Symptoms**:
- Tools execute but return empty results
- Wrong file content returned
- File not found even though it exists

**Causes**:
- Wrong file path format
- Case sensitivity issues
- File not in vault directory
- File encoding issues

**Solutions**:

```bash
# 1. List vault contents
find /home/mike-anderson/vaults/cohezion-vault -name "*.md" | head -20

# 2. Test vault_read directly
curl -X POST http://localhost:8360/call/vault_read \
  -H "Content-Type: application/json" \
  -d '{"path": "decisions"}'

# 3. Check file exists with exact path
ls -la /home/mike-anderson/vaults/cohezion-vault/decisions/

# 4. Verify file is readable
cat /home/mike-anderson/vaults/cohezion-vault/decisions/2026-02-08-something.md

# 5. Check for encoding issues
file /home/mike-anderson/vaults/cohezion-vault/decisions/*.md
```

---

## Performance Issues

### Server is slow or unresponsive

**Symptoms**:
- Tools take >10 seconds to respond
- Server becomes unresponsive after heavy use
- Memory usage climbing

**Solutions**:

```bash
# 1. Check server load
top -p $(pgrep -f "uvicorn|mcp_server") -b -n 1

# 2. Check disk I/O
iotop -p $(pgrep -f "uvicorn|mcp_server")

# 3. Check vault size
du -sh /home/mike-anderson/vaults/cohezion-vault

# 4. Monitor active connections
lsof -p $(pgrep -f "uvicorn|mcp_server") | grep -c "REG"

# 5. Restart server if memory leaking
pkill -f "python.*mcp"
sleep 2
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
uv run python -m src.mcp_server.main > /tmp/mcp_server.log 2>&1 &
```

---

## Log Analysis

### Check recent errors

```bash
# Last 50 lines
tail -50 /tmp/mcp_server.log

# Last errors
grep -i "error\|exception\|traceback" /tmp/mcp_server.log | tail -20

# By severity
grep "\[ERROR\]\|\[CRITICAL\]" /tmp/mcp_server.log

# Full traceback
grep -A 20 "Traceback" /tmp/mcp_server.log | tail -40
```

### Rotate logs to prevent growth

```bash
# Archive current log
mv /tmp/mcp_server.log /tmp/mcp_server.log.$(date +%Y%m%d_%H%M%S)

# Or use logrotate (for production)
cat > /etc/logrotate.d/mcp-server << 'EOF'
/tmp/mcp_server.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## Health Checks & Monitoring

### Simple health check script

```bash
#!/bin/bash
# health_check.sh

SERVER_URL="http://localhost:8360"
TIMEOUT=5

# Check connectivity
if ! timeout $TIMEOUT curl -s $SERVER_URL > /dev/null 2>&1; then
    echo "ERROR: Server not responding at $SERVER_URL"
    ps aux | grep "mcp\|uvicorn" | grep -v grep || echo "Server process not found"
    exit 1
fi

# Check API
curl -s $SERVER_URL/health || echo "Health endpoint not available (OK)"

echo "✓ Server is running"
```

### Cron job for monitoring

```bash
# Add to crontab: crontab -e
# Every 5 minutes check if server is running
*/5 * * * * /path/to/health_check.sh || /path/to/restart_mcp.sh 2>&1 >> /var/log/mcp_monitor.log
```

---

## Emergency Recovery

### If all else fails

```bash
# 1. Kill everything
pkill -9 -f "python.*mcp\|uvicorn"
pkill -9 -f "uv run"

# 2. Wait
sleep 5

# 3. Clean up
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
rm -rf .venv src/**/__pycache__

# 4. Start fresh
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
export MCP_PORT=8360
export MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263

uv sync
uv run python -m src.mcp_server.main

# 5. Test
curl http://localhost:8360/health
python3 test_mcp_integration.py
```

---

## Getting Help

If issues persist after troubleshooting:

1. **Collect diagnostics**:
   ```bash
   python3 test_mcp_integration.py 2>&1 | tee /tmp/diagnostics.txt
   tail -200 /tmp/mcp_server.log >> /tmp/diagnostics.txt
   ```

2. **Check logs**: Review `/tmp/mcp_server.log` for specific error messages

3. **Verify setup**:
   - `~/.claude/mcp.json` exists and is valid
   - `/home/mike-anderson/vaults/cohezion-vault` exists and contains files
   - Server can start: `uv run python -m src.mcp_server.main`

4. **Reference**: See `MCP_CLAUDE_CODE_INTEGRATION.md` for full configuration guide

