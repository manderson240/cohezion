# Health Check Endpoint Guide

## Overview

The Cloud Vault MCP Server includes a comprehensive health check system that monitors all critical dependencies and reports their status. This guide covers how to use and integrate the health check endpoint.

## Quick Start

### HTTP Endpoint

Check server health via HTTP:

```bash
curl http://localhost:8360/health
```

Response (all systems healthy):

```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T04:02:12.885791Z",
  "checks": {
    "vault": {
      "status": "ok",
      "latency_ms": 0,
      "path_accessible": true,
      "writable": true
    },
    "surrealdb": {
      "status": "ok",
      "latency_ms": 45,
      "connected": true
    },
    "sheets_api": {
      "status": "disabled",
      "latency_ms": 0,
      "authenticated": false,
      "message": "Sheets Bridge not configured"
    },
    "ollama": {
      "status": "ok",
      "latency_ms": 15,
      "models_loaded": 27
    },
    "disk_space": {
      "status": "ok",
      "free_gb": 1278.99,
      "threshold_gb": 10
    },
    "memory": {
      "status": "ok",
      "memory_percent": 0.03,
      "memory_mb": 36.44
    }
  }
}
```

### MCP Tool Interface

Check health programmatically via MCP:

```python
# Using FastMCP client
from mcp.client import ClientSession

async with ClientSession("http://localhost:8360") as session:
    result = await session.call_tool("vault_health_check")
    print(result)
```

## HTTP Status Codes

- **200 OK**: All checks passed, system is healthy
- **503 Service Unavailable**: One or more checks failed, system is degraded or unhealthy

## Response Format

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health status: `healthy`, `degraded`, or `unhealthy` |
| `timestamp` | string | ISO 8601 timestamp when check was performed |
| `checks` | object | Individual check results (see below) |

### Status Determination Rules

1. **Healthy**: All checks pass with status "ok"
2. **Degraded**: Any check has status "warning" or "critical" but none have "error"
3. **Unhealthy**: Any check has status "error"
4. **Disabled**: Checks with status "disabled" are ignored (e.g., Sheets API when not configured)

## Individual Health Checks

### 1. Vault Check

Tests filesystem access to the vault directory.

**Fields:**
- `status`: "ok", "error"
- `latency_ms`: Time to check (milliseconds)
- `path_accessible`: Boolean - vault path exists and is readable
- `writable`: Boolean - vault directory allows write operations
- `message`: Error message (if status is "error")

**What it tests:**
- Directory exists at configured path
- Read permissions work
- Write permissions work (by creating and deleting a test file)

**Typical values:**
- Latency: 0-5ms
- Status: OK for mounted local filesystems

### 2. SurrealDB Check

Tests connection to SurrealDB graph database.

**Fields:**
- `status`: "ok", "error"
- `latency_ms`: Time to reach SurrealDB (milliseconds)
- `connected`: Boolean - server is responding
- `message`: Error message (if status is "error")

**What it tests:**
- HTTP endpoint is responding (`GET /health`)
- Network connectivity to SurrealDB

**Typical values:**
- Latency: 20-100ms depending on network
- Status: OK if SurrealDB service is running

**Troubleshooting:**
- Connection refused: SurrealDB service not running
- Timeout: Network issues or service hanging

### 3. Google Sheets API Check

Tests authentication and access to Google Sheets.

**Fields:**
- `status`: "ok", "error", "disabled"
- `latency_ms`: Time to test authentication (milliseconds)
- `authenticated`: Boolean - credentials are valid
- `message`: Error message or "Sheets Bridge not configured"

**What it tests:**
- Google Sheets credentials are valid
- Can read from configured spreadsheet
- API quota is available

**Typical values:**
- Latency: 100-500ms (Sheets API is slower)
- Status: "disabled" if SheetsBridge not initialized
- Status: "error" if credentials missing or invalid

**Note:** This check is only available if SheetsBridge is initialized in the server.

### 4. Ollama Service Check

Tests connection to Ollama inference service.

**Fields:**
- `status`: "ok", "error"
- `latency_ms`: Time to reach Ollama (milliseconds)
- `models_loaded`: Number of models currently loaded
- `message`: Error message (if status is "error")

**What it tests:**
- Ollama HTTP API is responding (`GET /api/tags`)
- Models are available for inference

**Typical values:**
- Latency: 10-50ms for local service
- Models loaded: 1-30 depending on configuration
- Status: OK if Ollama service is running

**Troubleshooting:**
- Connection refused: Ollama service not running
- 0 models loaded: No models have been pulled yet

### 5. Disk Space Check

Monitors free disk space on the vault filesystem.

**Fields:**
- `status`: "ok", "warning", "critical"
- `free_gb`: Free space available (gigabytes)
- `threshold_gb`: Minimum required free space
- `message`: Warning or critical message

**What it tests:**
- Available disk space on vault partition
- Compares against thresholds

**Thresholds:**
- Critical: < 10 GB free
- Warning: 10-20 GB free
- OK: > 20 GB free

**Typical values:**
- Latency: Instant
- Free space: Depends on system
- Status: OK on systems with normal disk usage

### 6. Memory Check

Monitors process memory usage.

**Fields:**
- `status`: "ok", "warning"
- `memory_percent`: Memory usage as percentage of system RAM
- `memory_mb`: Absolute memory usage in megabytes
- `message`: Warning message if usage is high

**What it tests:**
- RAM usage of MCP server process
- System memory availability

**Thresholds:**
- Warning: > 80% of system RAM
- OK: < 80% of system RAM

**Typical values:**
- Memory: 30-100 MB for idle server
- Memory percent: 0.1-5% on systems with 16GB+ RAM

## Configuration

### Environment Variables

Control health check behavior with environment variables:

```bash
# Enable/disable health checks (default: true)
HEALTH_CHECK_ENABLED=true

# Timeout for all checks to complete (default: 5 seconds)
HEALTH_CHECK_TIMEOUT=5

# Cache results for this many seconds (default: 60)
HEALTH_CHECK_INTERVAL=60

# Service URLs for dependency checks
SURREALDB_URL=http://localhost:8000
OLLAMA_URL=http://localhost:11434
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
```

### Caching

Health check results are cached for 60 seconds by default. This prevents excessive load from repeated health checks while still providing timely status updates.

To disable caching, set `HEALTH_CHECK_INTERVAL=0`.

## Integration with Monitoring Systems

### Prometheus

The health endpoint integrates with Prometheus monitoring (Phase B):

```yaml
scrape_configs:
  - job_name: 'cloud-vault-mcp'
    static_configs:
      - targets: ['localhost:8360']
    metrics_path: '/health'
    scrape_interval: '60s'
```

### Kubernetes Liveness/Readiness Probes

Use in Kubernetes deployments:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8360
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8360
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 1
```

### Docker HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8360/health || exit 1
```

### Alerting Rules (example)

```
alert: UnhealthyVaultService
  expr: health_status{service="cloud-vault-mcp"} == 0
  for: 5m
  annotations:
    summary: "Cloud Vault MCP unhealthy"
    description: "Service has been unhealthy for 5+ minutes"
```

## Performance Considerations

### Timeout Behavior

All health checks must complete within 5 seconds (configurable). If a service doesn't respond:

1. Check waits up to 5 seconds
2. If service doesn't respond by then, check returns "error"
3. Overall status becomes "unhealthy"

### Concurrent Execution

All checks run concurrently using `asyncio.gather()`:

```
Start time: 0ms
├─ vault check:      0-5ms    (parallel)
├─ surrealdb check:  20-100ms (parallel)
├─ sheets check:     100-500ms (parallel)
├─ ollama check:     10-50ms  (parallel)
├─ disk check:       <1ms     (parallel)
└─ memory check:     <1ms     (parallel)

Total time: ~500ms (or timeout after 5s)
```

### Load Impact

- Health check endpoint has minimal impact on main server
- Results are cached for 60 seconds (configurable)
- Each check is independent and can fail without affecting others

## Troubleshooting

### All Checks Failing

1. Check server logs: `tail -f server.log`
2. Verify service URLs are correct:
   ```bash
   curl http://localhost:8000/health  # SurrealDB
   curl http://localhost:11434/api/tags  # Ollama
   ```
3. Check network connectivity:
   ```bash
   ping localhost
   netstat -an | grep 8000
   netstat -an | grep 11434
   ```

### Vault Check Failing

```bash
# Check vault directory exists
ls -la /home/mike-anderson/vaults/cohezion-vault

# Test write permissions
touch /home/mike-anderson/vaults/cohezion-vault/.test && rm $_
```

### High Disk Space Warning

```bash
# Check available space
df -h /home/mike-anderson/vaults/

# Find large files
du -sh /home/mike-anderson/vaults/* | sort -h
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep cloud-vault-mcp

# Monitor over time
watch -n 1 'ps aux | grep cloud-vault-mcp'
```

## API Reference

### HTTP Endpoint

**Request:**
```
GET /health HTTP/1.1
Host: localhost:8360
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T04:02:12.885791Z",
  "checks": { ... }
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "timestamp": "2026-02-10T04:02:12.885791Z",
  "checks": { ... }
}
```

### MCP Tool: `vault_health_check`

**Returns:**
- JSON string with health status and all check results
- Same format as HTTP endpoint

**Example usage:**
```python
import json
result = await session.call_tool("vault_health_check")
status = json.loads(result)
print(status["status"])  # "healthy"
```

## Testing

### Manual Testing

```bash
# Test endpoint responds
curl -v http://localhost:8360/health

# Test with specific timeout
curl --max-time 3 http://localhost:8360/health

# Test with jq for pretty output
curl http://localhost:8360/health | jq .

# Test specific check
curl http://localhost:8360/health | jq '.checks.surrealdb'
```

### Automated Testing

```bash
#!/bin/bash
# health_check_monitor.sh

ENDPOINT="http://localhost:8360/health"
THRESHOLD=503

while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT)

    if [ $STATUS -ne 200 ]; then
        echo "$(date): Unhealthy - HTTP $STATUS"
        curl -s $ENDPOINT | jq '.checks[] | select(.status != "ok")'
    else
        echo "$(date): Healthy"
    fi

    sleep 30
done
```

## See Also

- `benchmarks/README.md` - Performance baseline metrics
- `patterns/runbook-health-checks.md` - Operational guide
- `.env.example` - Configuration template
