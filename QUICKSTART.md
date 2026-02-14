# Quick Start: Phase A Complete

## Overview

Phase A implementation is complete with:
- ✅ Ollama MCP Server (core infrastructure)
- ✅ GitHub Actions CI/CD pipeline
- ✅ Health check endpoint
- ✅ Performance benchmarking framework
- ✅ Comprehensive runbooks

This quickstart verifies Phase A works and shows how to use the infrastructure.

## 1. Verify Infrastructure

### Check Ollama Service
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags | jq '.models | length'
# Expected output: 28 (or similar, number of loaded models)

# If error "Connection refused": Start Ollama
ollama serve &

# List models
curl http://localhost:11434/api/tags | jq '.models[].name'
```

### Check Cloud Vault MCP
```bash
# Health check (comprehensive)
curl http://localhost:8360/health | jq .status
# Expected: "healthy"

# View all health checks
curl http://localhost:8360/health | jq '.checks'
```

### Check Services Status
```bash
# Quick checklist
echo "=== Services ===" && \
echo "Ollama: $(curl -s http://localhost:11434/api/tags | jq -r '.models | length') models" && \
echo "Cloud Vault MCP: $(curl -s http://localhost:8360/health | jq -r '.status')" && \
echo "SurrealDB: $(curl -s http://localhost:8000/health | jq -r '.status // "off"')" && \
echo "Sheets API: $(gcloud auth application-default print-access-token 2>/dev/null | wc -c) bytes in token"
```

## 2. Run Tests Locally

### Cloud Vault MCP Tests
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Expected: All tests pass
# Run time: ~1-2 minutes
```

### Ollama MCP Tests
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp

# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Expected: All tests pass
# Run time: ~30-60 seconds
```

### Quick Smoke Test
```bash
# Fast checks before pushing
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pytest tests/unit/ -v --tb=short  # < 30 seconds

# Check linting
pylint src/mcp_server/ --disable=all --enable=E,F  # Errors only
```

## 3. Use Ollama MCP

### Option A: Via Cloud Vault MCP (Recommended)
```bash
# Python example - call through Cloud Vault MCP
python3 << 'EOF'
import requests
import json

# Call Cloud Vault MCP
response = requests.post(
    "http://localhost:8360/api/ollama_query",
    json={
        "prompt": "What is machine learning in 2 sentences?",
        "model": "auto",  # Auto-select based on prompt length
    }
)

result = response.json()
print(f"Model used: {result.get('model_used')}")
print(f"Response: {result.get('response')}")
print(f"Tokens: {result.get('tokens_used')}")
EOF
```

### Option B: Direct HTTP (Advanced)
```bash
# Query via Ollama service directly
curl http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:8b",
    "prompt": "Explain transformers briefly",
    "stream": false
  }' | jq '.response'
```

### Option C: Via Claude Code IDE
```
Use Claude Code IDE directly with Ollama MCP tools:
- ollama_query: Run inference
- ollama_embed: Generate embeddings
- ollama_status: Check model status
- ollama_select_model: Choose model for task
- ollama_batch: Batch inference requests
```

## 4. Capture Performance Baselines

**Baseline benchmarks establish metrics for Phase B validation.**

### Run Full Benchmark Suite
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks

# Capture baseline
python benchmark_runner.py \
  --output baseline_$(date +%Y-%m-%d).json \
  --warmup 3 \
  --iterations 10

# Expected output:
# Benchmark results written to: baseline_2026-02-10.json
# Total time: 5-10 minutes
```

### View Benchmark Results
```bash
# Pretty-print results
python3 << 'EOF'
import json

with open("baseline_2026-02-10.json") as f:
    data = json.load(f)

print(f"Captured: {data['timestamp']}")
print(f"System: {data['system_info']}")
print("\nResults:")
for test_name, results in data["benchmarks"].items():
    print(f"\n{test_name}:")
    print(f"  Mean: {results['results'].get('mean_time_ms')}ms")
    print(f"  P95:  {results['results'].get('p95_time_ms')}ms")
    print(f"  P99:  {results['results'].get('p99_time_ms')}ms")
EOF
```

### Benchmark Specific Tests
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks

# Ollama query only
python benchmark_runner.py --test ollama_query --output ollama_baseline.json

# Vault operations only
python benchmark_runner.py --test vault_operations --output vault_baseline.json

# SurrealDB batch operations
python benchmark_runner.py --test surrealdb_batch --output surrealdb_baseline.json
```

## 5. Monitor Health Continuously

### One-time Check
```bash
curl http://localhost:8360/health | jq '.'
```

### Continuous Monitoring (Every 5 Minutes)
```bash
# Create monitoring script
cat > /tmp/monitor_health.sh << 'EOF'
#!/bin/bash
while true; do
  HEALTH=$(curl -s http://localhost:8360/health)
  STATUS=$(echo $HEALTH | jq -r '.status')
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  if [ "$STATUS" = "healthy" ]; then
    echo "[$TIMESTAMP] ✅ System healthy"
  else
    echo "[$TIMESTAMP] ❌ ALERT: $STATUS"
    echo $HEALTH | jq '.checks'
  fi

  sleep 300  # 5 minutes
done
EOF

chmod +x /tmp/monitor_health.sh
/tmp/monitor_health.sh &

# Stop monitoring
# pkill -f "monitor_health.sh"
```

## 6. Next Steps: Phase B (Optional)

Phase B optimizations are optional. Proceed only if benchmarks show value.

### Decision Criteria
```
If Phase A benchmarks show performance issues:
  → Proceed with Phase B optimizations

If Phase A benchmarks are satisfactory:
  → Phase B is optional (defer or skip)
```

### Phase B Options (If Needed)
1. **SurrealDB Batch Optimization** - Faster queries with batching
2. **Backlink Indexing** - Pre-compute reverse relationships
3. **Query Caching** - Cache repeated queries
4. **Model Tuning** - Optimize Ollama for your workload

## 7. Important Files & Locations

### Core Infrastructure
```
cloud-vault-mcp/
├── src/mcp_server/server.py          # Main MCP server
├── benchmarks/benchmark_runner.py    # Performance testing
└── tests/                            # Unit + integration tests

ollama-mcp/
├── src/mcp_server/server.py          # Ollama MCP server
├── benchmarks/benchmark_runner.py    # Performance testing
└── tests/                            # Unit + integration tests
```

### Documentation (Vault)
```
/home/mike-anderson/vaults/cohezion-vault/

decisions/
└── 2026-02-10-phase-a-implementation-complete.md  # This decision

patterns/
├── runbook-ollama-mcp-operations.md                # Ollama operations
├── runbook-ci-cd-pipeline.md                       # CI/CD guide
├── runbook-health-checks.md                        # Health monitoring
├── runbook-benchmarking-validation.md              # Benchmarking guide
└── troubleshooting-mcp-infrastructure.md           # Troubleshooting

concepts/
└── mcp-infrastructure-architecture.md              # Architecture deep-dive
```

## 8. Troubleshooting

### Ollama Service Not Running
```bash
# Start Ollama
ollama serve &

# Verify
curl http://localhost:11434/api/tags
```

### Cloud Vault MCP Not Responding
```bash
# Restart Claude Code IDE
# This automatically restarts all MCP servers

# Or manually restart (if running standalone)
pkill -f cloud-vault-mcp
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
python -m mcp_server.server
```

### Tests Failing Locally
```bash
# Ensure services are running
ollama serve &
# Start Claude Code to run Cloud Vault MCP

# Then rerun tests
pytest tests/ -v

# If still failing, check specific errors
pytest tests/test_name.py -vvs
```

### Health Check Slow or Timing Out
See: [[patterns/troubleshooting-mcp-infrastructure]] for detailed diagnosis

## 9. Key Metrics (Establish Baseline)

After running benchmarks, note these values:

| Metric | Your Baseline | Target |
|--------|---------------|--------|
| Ollama query (8B) | ___ms | < 2000ms |
| Vault read latency | ___ms | < 20ms |
| SurrealDB batch (100x) | ___ms | < 700ms |
| Health check time | ___ms | < 5000ms |
| Memory peak | ___MB | < 500MB |

Store these in: `/tmp/phase_a_baseline_$(date +%Y-%m-%d).txt`

## 10. Complete Documentation

For detailed operational guidance, see vault docs:

**For Operations:**
- [[patterns/runbook-ollama-mcp-operations]] - Starting, monitoring, troubleshooting Ollama
- [[patterns/runbook-health-checks]] - Health check interpretation and monitoring
- [[patterns/runbook-ci-cd-pipeline]] - Running tests and understanding CI failures

**For Development:**
- [[patterns/runbook-benchmarking-validation]] - Capturing baselines and comparing results
- [[patterns/troubleshooting-mcp-infrastructure]] - Diagnosing issues
- [[concepts/mcp-infrastructure-architecture]] - System architecture and configuration

**Decision Record:**
- [[decisions/2026-02-10-phase-a-implementation-complete]] - Phase A rationale and alternatives

## Support

If you encounter issues:

1. Check health: `curl http://localhost:8360/health | jq .`
2. Review runbooks in vault (above)
3. Check troubleshooting guide: `patterns/troubleshooting-mcp-infrastructure.md`
4. Gather diagnostics (see troubleshooting guide for bundle script)

---

**Phase A Complete** - Infrastructure is ready for Phase B optimization (if needed).
