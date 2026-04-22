# Health Check Endpoint Documentation

## Overview

The Cloud Vault MCP server includes a comprehensive health check endpoint (`/health`) that monitors all critical dependencies and infrastructure components. This endpoint is designed for both operational monitoring and automated health verification.

## Features

- **6 Dependency Checks**: Vault filesystem, SurrealDB, Google Sheets API, Ollama, disk space, and process memory
- **Fast Response Time**: < 50ms typical, with 60-second caching for repeated checks
- **Graceful Degradation**: Service failures don't crash the endpoint
- **Detailed Latencies**: Each check includes latency measurements
- **Overall Status Aggregation**: Calculates healthy/degraded/unhealthy status based on individual checks
- **Zero Configuration**: Works out-of-the-box with sensible defaults

## HTTP Endpoint

### Request

```bash
GET /health
```

### Response

**Status Code 200** (healthy or degraded):
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T04:02:21.762999+00:00",
  "checks": {
    "vault": {
      "status": "ok",
      "latency_ms": 0,
      "path_accessible": true,
      "writable": true
    },
    "surrealdb": {
      "status": "ok",
      "latency_ms": 26,
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
      "memory_mb": 40.23
    }
  }
}
```

**Status Code 503** (unhealthy):
```json
{
  "status": "unhealthy",
  "timestamp": "2026-02-10T04:02:21.762999+00:00",
  "checks": {
    "vault": {
      "status": "error",
      "message": "Vault path does not exist"
    },
    ...
  }
}
```

## Status Values

### Overall Status
- **healthy**: All checks passed (status: ok/disabled)
- **degraded**: At least one warning or critical condition
- **unhealthy**: At least one error condition

### Individual Check Statuses
- **ok**: Check passed
- **warning**: Check passed but with warning (e.g., disk low)
- **critical**: Critical threshold exceeded (e.g., disk very low)
- **error**: Check failed (connection error, timeout, etc.)
- **disabled**: Service not configured (e.g., Sheets API when not enabled)

## Individual Checks

### 1. Vault Check
**What it does**: Verifies vault filesystem is readable and writable

**Return fields**:
- `status`: "ok" or "error"
- `latency_ms`: Time to complete check
- `path_accessible`: True if vault directory exists and is readable
- `writable`: True if test write-delete succeeded
- `message`: Error description if status is "error"

**Thresholds**: None (binary pass/fail)

### 2. SurrealDB Check
**What it does**: Tests connection to SurrealDB and basic connectivity

**Return fields**:
- `status`: "ok" or "error"
- `latency_ms`: Time to complete check
- `connected`: True if health endpoint responded
- `message`: Error description if failed

**Thresholds**: None (binary pass/fail)

### 3. Sheets API Check
**What it does**: Authenticates with Google Sheets API and reads a row

**Return fields**:
- `status`: "ok", "error", or "disabled"
- `latency_ms`: Time to complete check
- `authenticated`: True if API call succeeded
- `message`: Error description or "Sheets Bridge not configured"

**Thresholds**: None (binary pass/fail)

### 4. Ollama Check
**What it does**: Tests connection to Ollama service and counts loaded models

**Return fields**:
- `status`: "ok" or "error"
- `latency_ms`: Time to complete check
- `models_loaded`: Number of models currently loaded
- `message`: Error description if failed

**Thresholds**: None (binary pass/fail)

### 5. Disk Space Check
**What it does**: Measures free disk space on vault partition

**Return fields**:
- `status`: "ok", "warning", or "critical"
- `free_gb`: Available disk space in gigabytes
- `threshold_gb`: Alert thresholds

**Thresholds**:
- `< 10 GB`: critical
- `< 20 GB`: warning
- `>= 20 GB`: ok

### 6. Memory Check
**What it does**: Measures process memory usage

**Return fields**:
- `status`: "ok" or "warning"
- `memory_percent`: Memory usage percentage (0-100)
- `memory_mb`: Memory usage in megabytes

**Thresholds**:
- `> 80%`: warning
- `<= 80%`: ok

## MCP Tool

The health check is also available as an MCP tool for programmatic access:

```python
# Call the vault_health_check() tool
result = await vault_health_check()
# Returns JSON string with health status
```

## Configuration

Health check behavior is controlled by environment variables:

```bash
# Enable/disable the health check endpoint (default: true)
HEALTH_CHECK_ENABLED=true

# Timeout for all checks combined (default: 5 seconds)
HEALTH_CHECK_TIMEOUT=5

# Cache TTL for repeated checks (default: 60 seconds)
HEALTH_CHECK_INTERVAL=60

# Service URLs
SURREALDB_URL=http://localhost:8000
OLLAMA_URL=http://localhost:11434
VAULT_PATH=/home/user/vaults/cohezion-vault
```

## Performance

### Response Time
- **Typical**: 30-50ms
- **Target**: < 1 second
- **With caching**: ~1ms (if within TTL)

### Caching
Results are cached for 60 seconds by default to avoid repeated checks overloading services. The cache TTL can be modified by setting `HEALTH_CHECK_INTERVAL`.

### Timeouts
All checks have individual timeouts (typically 5 seconds) and a global timeout (configurable). If any check times out, it's marked as "error" but doesn't crash the endpoint.

## Usage Examples

### Using curl

```bash
# Basic health check
curl http://localhost:8360/health

# Check only if healthy (exit 1 if not)
curl -f http://localhost:8360/health > /dev/null && echo "healthy" || echo "unhealthy"

# Pretty-print JSON response
curl http://localhost:8360/health | jq .

# Check specific component (using jq)
curl http://localhost:8360/health | jq '.checks.ollama'
```

### Using Python

```python
import httpx

response = httpx.get("http://localhost:8360/health")
if response.status_code == 200:
    data = response.json()
    print(f"Status: {data['status']}")
    for check_name, result in data['checks'].items():
        print(f"  {check_name}: {result['status']}")
else:
    print("Health check failed")
```

### Using Docker/Kubernetes

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8360
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5

# Docker HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8360/health || exit 1
```

## Monitoring and Alerting

### Prometheus Integration

The health check endpoint can be scraped for Prometheus metrics:

```
# Example: Extract vault writability as metric
curl http://localhost:8360/health | \
  jq '.checks.vault.writable | if . then 1 else 0 end'
```

### Alert Rules

Configure alerts based on status codes:
- **503**: Unhealthy (critical alert)
- **200 + degraded**: Degraded (warning alert)
- Response time > 1s: Performance issue (warning)

### Example Monitoring Script

```bash
#!/bin/bash
# Monitor health endpoint every 60 seconds

while true; do
  response=$(curl -s -w "\n%{http_code}" http://localhost:8360/health)
  status_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$status_code" != "200" ]; then
    echo "Health check failed: $status_code"
    echo "$body" | jq '.status'
  fi

  sleep 60
done
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
python -m pytest tests/test_health_check.py -v
```

Test files:
- `tests/test_health_check.py`: 21 tests covering all checks and scenarios
- `src/mcp_server/health.py`: Health checker implementation (355 lines)

## Architecture

### Components

1. **HealthChecker** (`src/mcp_server/health.py`)
   - Runs individual checks concurrently
   - Aggregates results into overall status
   - Implements caching and timeout handling

2. **HTTP Endpoint** (`src/mcp_server/main.py`)
   - FastAPI/Starlette route
   - JSON response formatting
   - Status code mapping

3. **MCP Tool** (`src/mcp_server/server.py`)
   - Programmatic access via MCP protocol
   - Same underlying health checker

### Error Handling

- Timeouts: Checks that timeout are marked "error"
- Connection failures: Marked "error" with exception message
- Disabled services: Marked "disabled" (not counted as error)
- Endpoint crash: Won't happen - exceptions are caught and returned as unhealthy

## Troubleshooting

### Endpoint returns 503
Check the response body's `checks` field for which specific service is failing:
```bash
curl -s http://localhost:8360/health | jq '.checks[] | select(.status != "ok" and .status != "disabled")'
```

### Slow health check (> 1 second)
- Check for network latency issues to SurrealDB or Ollama
- Increase `HEALTH_CHECK_TIMEOUT` if services are slow
- Use caching (don't call endpoint more than every 60 seconds)

### "Sheets API" shows error
Sheets API is optional - it will show "disabled" if SheetsBridge is not configured, which is normal.

### Memory or disk warning
- Memory warning: Process is using > 80% of available RAM
- Disk critical: Less than 10GB free
- Disk warning: Less than 20GB free

Check with:
```bash
curl -s http://localhost:8360/health | jq '.checks.memory, .checks.disk_space'
```

## Implementation Details

### Async/Await Pattern
All checks run concurrently using `asyncio.gather()` for minimal latency:

```python
results = await asyncio.gather(
    self.check_vault(),
    self.check_surrealdb(),
    self.check_sheets_api(),
    self.check_ollama(),
    self.check_disk_space(),
    self.check_memory(),
    return_exceptions=True,
)
```

### Caching Strategy
Results are cached for 60 seconds by default. Cache key is implicit (single global cache). Useful for:
- Load balancing (avoid thundering herd)
- Reduced latency on repeated checks
- Protecting external services from health check storms

### Status Code Mapping
- **200 OK**: healthy or degraded (business logic determines severity)
- **503 Service Unavailable**: unhealthy (critical errors detected)

This allows:
- Uptime monitoring tools to alert on 503
- Applications to distinguish between "mostly ok" (degraded) and "broken" (unhealthy)

## Future Enhancements

Potential improvements for future versions:

1. **Metrics Export**: Prometheus `/metrics` endpoint
2. **Detailed Diagnostics**: Optional deep-dive checks
3. **Custom Checks**: Plugin system for application-specific checks
4. **Historical Data**: Track check history and trends
5. **Alerting Integration**: Built-in webhook notifications
6. **Check Skipping**: Allow disabling specific checks per request
7. **Performance Baselines**: Track and alert on latency regressions

## References

- **Health Check Pattern**: [Microservices Patterns](https://microservices.io/patterns/observability/health-check-api.html)
- **HTTP Status Codes**: [RFC 7231](https://tools.ietf.org/html/rfc7231#section-6.3.1)
- **Prometheus Monitoring**: [Prometheus Docs](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
