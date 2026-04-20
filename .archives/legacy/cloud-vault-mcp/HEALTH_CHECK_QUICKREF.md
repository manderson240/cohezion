# Health Check Quick Reference

## Quick Start

```bash
# Test the health endpoint
curl http://localhost:8360/health | jq .

# Check overall status
curl -s http://localhost:8360/health | jq '.status'

# Check specific service
curl -s http://localhost:8360/health | jq '.checks.ollama'
```

## Response Status Codes

| Code | Status | Meaning |
|------|--------|---------|
| 200 | healthy/degraded | All or most services working |
| 503 | unhealthy | Critical errors detected |

## Individual Check Status Values

| Value | Meaning |
|-------|---------|
| ok | Check passed |
| warning | Service working but with warning (low disk/memory) |
| critical | Critical threshold exceeded |
| error | Service unavailable or auth failed |
| disabled | Service not configured (normal) |

## Configuration

```bash
# Enable/disable health check endpoint
export HEALTH_CHECK_ENABLED=true

# Timeout for all checks (seconds)
export HEALTH_CHECK_TIMEOUT=5

# Cache TTL (seconds)
export HEALTH_CHECK_INTERVAL=60

# Service URLs
export SURREALDB_URL=http://localhost:8000
export OLLAMA_URL=http://localhost:11434
export VAULT_PATH=/path/to/vault
```

## Monitoring Examples

### Check if healthy (for scripts)
```bash
if curl -sf http://localhost:8360/health > /dev/null; then
  echo "Healthy"
else
  echo "Unhealthy"
fi
```

### Alert on degraded status
```bash
status=$(curl -s http://localhost:8360/health | jq -r '.status')
if [ "$status" = "unhealthy" ]; then
  # Send alert
  exit 1
fi
```

### Check specific service
```bash
ollama_status=$(curl -s http://localhost:8360/health | jq -r '.checks.ollama.status')
echo "Ollama: $ollama_status"

surrealdb_latency=$(curl -s http://localhost:8360/health | jq -r '.checks.surrealdb.latency_ms')
echo "SurrealDB latency: ${surrealdb_latency}ms"
```

### Get all error details
```bash
curl -s http://localhost:8360/health | \
  jq '.checks[] | select(.status == "error")'
```

## Key Fields in Response

```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-02-10T04:02:21.762999+00:00",
  "checks": {
    "vault": {
      "status": "ok|error",
      "latency_ms": 0,
      "path_accessible": true,
      "writable": true
    },
    "surrealdb": {
      "status": "ok|error",
      "latency_ms": 26,
      "connected": true
    },
    "sheets_api": {
      "status": "ok|error|disabled",
      "latency_ms": 0,
      "authenticated": false
    },
    "ollama": {
      "status": "ok|error",
      "latency_ms": 15,
      "models_loaded": 27
    },
    "disk_space": {
      "status": "ok|warning|critical",
      "free_gb": 1278.99,
      "threshold_gb": 10
    },
    "memory": {
      "status": "ok|warning",
      "memory_percent": 0.03,
      "memory_mb": 40.23
    }
  }
}
```

## Thresholds

| Check | Status | Condition |
|-------|--------|-----------|
| Disk | warning | < 20GB free |
| Disk | critical | < 10GB free |
| Memory | warning | > 80% used |
| All checks | - | 5 second timeout |

## Test the Implementation

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Run all health check tests
python -m pytest tests/test_health_check.py -v

# Run with coverage
python -m pytest tests/test_health_check.py --cov=src/mcp_server/health

# Test locally
python /tmp/test_health_endpoint.py
```

## Files

| File | Purpose |
|------|---------|
| src/mcp_server/health.py | Health checker implementation (355 lines) |
| src/mcp_server/config.py | Configuration (added env vars) |
| src/mcp_server/main.py | HTTP endpoint handler |
| src/mcp_server/server.py | MCP tool registration |
| tests/test_health_check.py | Test suite (21 tests) |
| HEALTH_CHECK.md | Full documentation |

## Performance

- Typical response: **32ms**
- Target response: **< 1s**
- Results cached for: **60 seconds**
- All checks run: **in parallel**

## Troubleshooting

### Health check returns unhealthy
```bash
# Check which service is failing
curl -s http://localhost:8360/health | \
  jq '.checks | to_entries[] | select(.value.status == "error")'
```

### Endpoint times out
- Increase HEALTH_CHECK_TIMEOUT
- Check network connectivity to SurrealDB/Ollama
- Check disk I/O performance

### Memory/Disk warning
```bash
# Check current status
curl -s http://localhost:8360/health | \
  jq '.checks | {memory, disk_space}'
```

## Integration Patterns

### Kubernetes
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8360
  periodSeconds: 30
```

### Docker
```dockerfile
HEALTHCHECK --interval=30s CMD \
  curl -f http://localhost:8360/health || exit 1
```

### Prometheus
```yaml
scrape_configs:
  - job_name: vault-mcp
    static_configs:
      - targets: ['localhost:8360']
    metrics_path: '/health'
```

## MCP Tool Usage

```python
# Call via MCP tool
result = await vault_health_check()

# Parse JSON response
import json
data = json.loads(result)
print(f"Status: {data['status']}")
```
