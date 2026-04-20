---
title: Troubleshooting Guide - MCP Infrastructure
date: 2026-02-10
status: active
tags: [troubleshooting, runbook, operations, infrastructure]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 0
  synapse_out: 11
---

## Quick Diagnostic Checklist

When something is wrong, run this first:

```bash
# 1. Check overall health
curl -s http://localhost:8360/health | jq '.status'

# 2. Check individual services
curl -s http://localhost:11434/api/tags | jq '.models | length'      # Ollama
curl -s http://localhost:8000/health                                  # SurrealDB
gcloud auth application-default print-access-token 2>/dev/null | head -c 20  # Google Sheets

# 3. Check logs
tail -20 /var/log/cohezion/*
journalctl -u ollama -n 20
ps aux | grep -E "ollama|surrealdb|cloud-vault"

# 4. Basic connectivity
ping localhost
netstat -tlnp | grep -E "8360|11434|8000"
```

---

## Problem 1: Ollama MCP Not Responding After Restart

### Symptoms
- Claude Code IDE shows "MCP server unresponsive"
- Calls to Ollama MCP tools timeout
- Health check shows `ollama_mcp: unhealthy` or timeout

### Diagnosis
```bash
# Is MCP server process running?
ps aux | grep ollama-mcp
# Should show: python -m mcp_server.server

# Is Ollama service running?
curl http://localhost:11434/api/tags
# Should respond with model list

# Is MCP server crashing on start?
cd /home/mike-anderson/dev/cohezion/ollama-mcp
.venv/bin/python3 -m mcp_server.server
# Watch for exceptions in output
```

### Solutions (in order)

**Solution 1: Restart Claude Code**
```bash
# Claude Code re-initializes MCP connections on restart
# Quit Claude Code completely and reopen
# This restarts all MCP servers including Ollama MCP
```

**Solution 2: Verify Ollama Service is Running**
```bash
# Ollama MCP requires Ollama service to be running
curl http://localhost:11434/api/tags
# If: Connection refused → Ollama not running
ollama serve &

# If: Timeout → Ollama service hung
pkill -f "ollama serve"
sleep 2
ollama serve &
```

**Solution 3: Check for Crashes in Startup**
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp

# Run server manually to see errors
.venv/bin/python3 -m mcp_server.server
# Look for: ImportError, ConnectionError, Authentication failed, etc.

# Common issues:
# - Missing dependencies: pip install -e ".[dev]"
# - Wrong Python version: python3 --version (needs 3.11+)
# - Port already in use: lsof -i :8360
```

**Solution 4: Check MCP Configuration**
```bash
# Verify ~/.claude/mcp.json has correct Ollama MCP config
cat ~/.claude/mcp.json | jq '.mcpServers.ollama-mcp'

# Should reference correct Python executable
grep ollama-mcp ~/.claude/mcp.json

# Expected:
# "ollama-mcp": {
#   "command": "/home/mike-anderson/dev/cohezion/ollama-mcp/.venv/bin/python3",
#   "args": ["-m", "mcp_server.server"]
# }

# If wrong: Update config and restart Claude Code
```

**Solution 5: Reinstall Ollama MCP Dependencies**
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp

# Fresh virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# Reinstall
pip install -e ".[dev]"
pip list | grep -E "mcp|requests"

# Test manually
python3 -m mcp_server.server
# Should start without errors
```

### Prevention
- Monitor health check: `curl http://localhost:8360/health`
- Set up health check monitoring cron job (see health-checks runbook)
- Ensure Ollama service is enabled at boot: `systemctl enable ollama`

---

## Problem 2: Tests Failing in CI but Passing Locally

### Symptoms
- All tests pass: `pytest tests/ -v`
- Push to main → GitHub Actions CI fails
- Different error messages in CI vs local

### Common Causes & Fixes

**Cause 1: Different Python version**
```bash
# Check local Python version
python3 --version
# Check CI version in .github/workflows/test-*.yml
grep "python-version" .github/workflows/test-*.yml

# Fix: Ensure both are 3.11+
python3.11 --version
```

**Cause 2: Missing environment variables in CI**
```bash
# Local test uses env vars from shell
echo $VAULT_PATH $OLLAMA_URL

# CI doesn't have these unless set in workflow file
# Fix: Add to .github/workflows/test-*.yml
- name: Run tests
  env:
    VAULT_PATH: /tmp/test-vault
    OLLAMA_URL: http://localhost:11434
  run: pytest tests/ -v
```

**Cause 3: Service not running in CI**
```bash
# Ollama/SurrealDB not available in CI environment
# Error: "Connection refused" in CI only

# Fix: Either
# a) Mock the service in tests
# b) Add service startup step to workflow
# c) Skip integration tests in CI

# Example: Add to workflow
- name: Start Ollama
  run: ollama serve &

- name: Wait for service
  run: sleep 5 && curl http://localhost:11434/api/tags
```

**Cause 4: File path differences**
```bash
# Local: /home/user/vaults/cohezion-vault
# CI: /home/runner/work/cohezion/cohezion/vaults/cohezion-vault

# Error: "File not found" in CI only

# Fix: Use relative paths or environment variables
import os
VAULT_PATH = os.getenv("VAULT_PATH", "/tmp/test-vault")
# Or use temp directory for tests
import tempfile
test_vault = tempfile.TemporaryDirectory()
```

**Cause 5: Permissions issue**
```bash
# Local: Running as user with full permissions
# CI: Running as 'runner' user, limited permissions

# Fix: Ensure test creates writable temp directory
os.makedirs(test_path, exist_ok=True)
os.chmod(test_path, 0o755)
```

### Debugging CI Failures
```bash
# 1. View full CI logs
gh run view <run-id> --log

# 2. Look for environment info in CI logs
# Should show Python version, pip list, etc.

# 3. Compare to local environment
python3 --version && pip list | head

# 4. Try to replicate exact CI command locally
# Find exact pytest command in CI logs
# Run it locally with exact same command
```

---

## Problem 3: Health Check Timeout (5+ seconds)

### Symptoms
- `curl http://localhost:8360/health` takes > 5 seconds
- Or returns 504 Gateway Timeout
- Individual service might be very slow

### Diagnosis
```bash
# Time each dependency separately
time curl http://localhost:8360/health | jq '.checks'

# Which check is slowest?
curl http://localhost:8360/health | jq '.checks | to_entries | sort_by(.value.response_time_ms) | reverse | .[0:3]'
# Shows top 3 slowest checks
```

### Solutions by Cause

**If Ollama is slow:**
```bash
# First inference loads model to GPU (slow)
time curl http://localhost:11434/api/generate \
  -d '{"model": "qwen3:8b", "prompt": "test", "stream": false}' > /dev/null
# First call: 5-10 seconds (loading GPU)
# Second call: 1-3 seconds (inference only)

# If consistently slow: Check GPU
nvidia-smi  # Is GPU available?
```

**If SurrealDB is slow:**
```bash
# Test query latency
time curl http://localhost:8000/api/query -d 'SELECT * FROM papers LIMIT 1' \
  -H 'Accept: application/json'

# If > 500ms: Database may be building indexes
# Solution: Wait for index build to complete
# Monitor: curl http://localhost:8000/health
```

**If Sheets API is slow:**
```bash
# First API call includes auth overhead
gcloud auth application-default print-access-token
# Slow if token is expiring

# Fix: Refresh token
gcloud auth application-default login
```

**If Vault access is slow:**
```bash
# File system latency or network mount
time ls /home/mike-anderson/vaults/cohezion-vault

# If > 100ms: Check mount
mount | grep cohezion
lsof -p $$ | grep cohezion

# If slow network mount:
# 1. Move vault to local SSD
# 2. Or mount with caching options
```

**Fix: Increase health check timeout temporarily**
```bash
# While investigating root cause, increase timeout
# In cloud-vault-mcp/src/mcp_server/health.py
HEALTH_CHECK_TIMEOUT = 10  # Increase from 5 to 10

# Then restart service
```

---

## Problem 4: Benchmark Comparison Shows Unexpected Slowdown

### Symptoms
- Phase B was supposed to be faster
- Actual results: Phase B is SLOWER
- `compare_benchmarks.py` shows -30% instead of +20%

### Diagnosis
```bash
# 1. Verify benchmark data quality
python analyze_benchmark.py phase-b_results.json | grep -E "mean|stddev"
# High stddev (> 20% of mean) = unreliable data

# 2. Check for outliers
python analyze_benchmark.py phase-b_results.json | grep -E "min|max|p95|p99"
# Large min-max gap = system was contending

# 3. Rerun baseline for comparison
python benchmark_runner.py --test <test_name> --iterations 20

# 4. Check what changed
git diff HEAD~5 | grep -A5 -B5 <modified_function>
```

### Solutions

**Solution 1: Data Quality Issue**
```bash
# System was busy during benchmark run
# Rerun on quiet system

# Stop background processes
sudo systemctl stop docker
sudo systemctl stop postgresql

# Clear caches
sync && echo 3 > /proc/sys/vm/drop_caches

# Rerun benchmarks
python benchmark_runner.py --iterations 20 --warmup 5

# If still slow: Revert Phase B change and retest
git checkout main
python benchmark_runner.py --output baseline_reverted.json
# If baseline is slow too: Problem existed before Phase B
```

**Solution 2: Phase B Change is Ineffective**
```bash
# Example: Added batching but batch size is wrong

# Analyze which test is slow
python benchmark_runner.py --test surrealdb_batch

# Profile the slow code
python -m cProfile -s cumulative benchmark_runner.py --test surrealdb_batch

# Look at top functions by cumulative time
# If main work is done but overhead increased: Batch size too small

# Fix: Adjust batch size
# In surrealdb_batch.py
BATCH_SIZE = 10  # Increase from 10 to 50

# Retest
python benchmark_runner.py --test surrealdb_batch --output batch_50.json
```

**Solution 3: Regression Introduced by Phase B**
```bash
# Example: Added unintended nested loop

# Commit-by-commit bisect to find regression
git log --oneline | head -20
git bisect start
git bisect bad HEAD  # Current (slow) commit
git bisect good <earlier-known-good-commit>

# Git will binary search for regression
# Test each commit with: python benchmark_runner.py --test <test>

# Once found, analyze the change
git show <regression-commit>

# Fix: Remove the problematic code or optimize it
```

---

## Problem 5: API Calls Hanging / No Response

### Symptoms
- `curl http://localhost:8360/api/ollama_query` hangs
- Request never completes, no response
- Must kill process with Ctrl+C

### Diagnosis
```bash
# With timeout to see what happens
timeout 10 curl -v http://localhost:8360/api/ollama_query -d '{"prompt": "test"}'

# If timeout: Server is not responding

# Check if server is responsive at all
curl http://localhost:8360/health --max-time 5
# If timeout: Server is hung

# Check process
ps aux | grep cloud-vault-mcp
# Is process using CPU? Or idle?
top -p <pid> -n 1

# Check for infinite loop or deadlock
strace -p <pid>  # See what syscalls it's making
# If stuck on: read(), write(), sem_wait() → deadlock likely
```

### Solutions

**Solution 1: Service Hung - Restart**
```bash
# Clean restart
pkill -f cloud-vault-mcp
sleep 2
# Restart Claude Code to restart MCP servers
```

**Solution 2: Infinite Loop or Deadlock**
```bash
# Get thread dump to see where stuck
python -c "
import sys, traceback, threading
import time

# Print all thread stacks
for t in threading.enumerate():
    traceback.print_stack(sys._current_frames()[t.ident])
"

# Or use debugger
python -m pdb -c continue -m mcp_server.server
# Then Ctrl+C to interrupt and inspect state
```

**Solution 3: Dependent Service Hung (Ollama, SurrealDB)**
```bash
# Cloud Vault MCP waiting for Ollama
curl http://localhost:11434/api/tags --max-time 5
# If timeout: Ollama is hung

# Restart Ollama
pkill ollama
sleep 2
ollama serve &

# Then retry API call
timeout 10 curl http://localhost:8360/api/ollama_query -d '{"prompt": "test"}'
```

**Solution 4: Request Body Processing Issue**
```bash
# Maybe request is large and slow to process
# Try with smaller request
curl http://localhost:8360/api/ollama_query \
  -d '{"prompt": "hi"}' \
  --max-time 10

# If works: Large request is slow
# Add request size limit:
# In mcp_server/limits.py
MAX_REQUEST_SIZE = 10_000_000  # 10MB
```

---

## Quick Reference: Common Errors & Fixes

| Error Message | Check | Fix |
|---------------|-------|-----|
| "Connection refused" | Service running? | `ollama serve &` or `surreal start` |
| "Timeout after 30s" | Service responsive? | Restart service, check logs |
| "Authentication failed" | Credentials valid? | `gcloud auth application-default login` |
| "Out of memory" | System resources? | `free -h`, kill unused processes |
| "Model not found" | Model loaded? | `ollama pull model-name` |
| "Port already in use" | Port conflict? | `lsof -i :8360`, use different port |
| "Assertion failed in test" | Logic correct? | Review test expectation vs actual |
| "FileNotFoundError" | Path exists? | `ls -la /path/to/file`, check permissions |
| "Import error: module not found" | Package installed? | `pip install -e ".[dev]"` |
| "Python version mismatch" | Python 3.11+? | `python3 --version`, use python3.11 |

---

## When to Escalate

**Escalate if:**
1. Service crashes on startup with ImportError
2. Persistent timeout (> 30s) even after restart
3. Out of memory (OOM) errors repeatedly
4. Corrupted database or vault files
5. Security vulnerability suspected

**For escalation:**
```bash
# Collect diagnostic bundle
mkdir /tmp/cohezion_diagnostics
cp ~/.claude/mcp.json /tmp/cohezion_diagnostics/
ps aux | grep -E "ollama|surrealdb|cloud-vault" > /tmp/cohezion_diagnostics/processes.txt
curl http://localhost:8360/health > /tmp/cohezion_diagnostics/health.json
journalctl -u ollama -n 100 > /tmp/cohezion_diagnostics/ollama.log
df -h > /tmp/cohezion_diagnostics/disk.txt

# Share diagnostic bundle
tar czf cohezion_diagnostics.tar.gz /tmp/cohezion_diagnostics/
```

## Related Documentation
- [[runbook-ollama-mcp-operations]]
- [[runbook-health-checks]]
- [[runbook-ci-cd-pipeline]]
- [[mcp-infrastructure-architecture]]

## Related Concepts

- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-10-compound-node-linking-plan]]
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
- [[runbook-ci-cd-pipeline]]
