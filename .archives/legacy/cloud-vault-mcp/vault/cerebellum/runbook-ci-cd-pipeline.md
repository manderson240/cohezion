---
title: Operational Runbook - CI/CD Pipeline
date: 2026-02-10
status: active
tags: [runbook, operations, ci-cd, github-actions]
aspect: thinker
neural:
  activation: 0.87
  stage: mature
  synapse_in: 0
  synapse_out: 10
---

## Overview

GitHub Actions CI/CD pipeline automates testing and deployment validation for:
- Cloud Vault MCP Server (`cloud-vault-mcp/`)
- Ollama MCP Server (`ollama-mcp/`)
- Documentation and runbooks

**Pipeline Triggers:**
- Push to any branch
- Pull request to main
- Manual trigger (workflow_dispatch)

## Running Tests Locally Before Pushing

### Prerequisites
```bash
# Verify Python environment
python3 --version  # Python 3.11+
pip --version      # pip 24+

# Install testing dependencies
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pip install -e ".[dev]"
pytest --version  # pytest 7.0+
```

### Run Full Test Suite Locally
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html to see coverage

# Run specific test file
pytest tests/test_vault_operations.py -v

# Run specific test
pytest tests/test_vault_operations.py::test_read_file -v
```

### Run Ollama MCP Tests
```bash
cd /home/mike-anderson/dev/cohezion/ollama-mcp

# Full test suite
pytest tests/ -v

# Just Ollama client tests
pytest tests/test_ollama_client.py -v
```

### Integration Tests (requires services running)
```bash
# Ensure services are running first
ollama serve &  # Start Ollama service
# Start Cloud Vault MCP (via Claude Code or manual)

# Run integration tests
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pytest tests/integration/ -v -s  # -s shows print output
```

### Quick Check Before Pushing
```bash
# Run fast unit tests only (no service dependencies)
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pytest tests/unit/ -v --tb=short

# Check for linting issues
pylint src/mcp_server/ --disable=all --enable=E,F  # Only errors/fatal
```

## Understanding CI/CD Pipeline Structure

### Workflows Location
```
.github/workflows/
├── test-cloud-vault-mcp.yml      # Tests for Cloud Vault MCP
├── test-ollama-mcp.yml           # Tests for Ollama MCP
├── deploy-production.yml         # Deployment (if enabled)
└── update-docs.yml               # Documentation builds
```

### Pipeline Stages (per workflow)

1. **Checkout** - Clone repository
2. **Setup Python** - Install Python 3.11
3. **Install Dependencies** - `pip install -e ".[dev]"`
4. **Run Linting** - Code style checks (pylint, flake8)
5. **Run Tests** - Unit + integration tests
6. **Generate Reports** - Coverage, test results
7. **Upload Artifacts** - Coverage HTML, test reports

## Fixing Failing CI Tests

### Step 1: Identify the Failure
```bash
# View GitHub Actions logs
gh workflow view test-cloud-vault-mcp.yml  # List recent runs
gh run view <run-id> --log                 # View detailed logs
```

Or via GitHub web UI:
1. Go to repository → Actions tab
2. Click failing workflow run
3. Expand "Run tests" section to see output

### Step 2: Reproduce Locally
```bash
# Pull latest changes
git pull origin main

# Run same test that failed in CI
pytest tests/test_vault_operations.py::test_name -v

# Note: CI may fail on things that work locally due to:
# - Missing environment variables
# - Service not running
# - Different Python version
# - File permission issues
```

### Step 3: Common Failures & Fixes

**Failure: "Import error: No module named 'mcp_server'"**
```bash
# Fix: Reinstall package in development mode
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pip install -e .
```

**Failure: "Test timeout after 30 seconds"**
```bash
# Usually indicates service dependency not running
# Fix: Start required services
ollama serve &
# Or mock the service in tests (use pytest fixtures)
```

**Failure: "AssertionError: expected X, got Y"**
```bash
# Logic error in code or test
# Fix:
# 1. Read test expectation
# 2. Compare to actual output
# 3. Fix code or test assertion
pytest tests/test_name.py -vvs  # -vvs for verbose output
```

**Failure: "File not found: /home/user/vault/papers/..."**
```bash
# Path issue - absolute paths may differ on CI
# Fix: Use environment variables for paths
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
pytest tests/ -v
```

**Failure: "SurrealDB connection refused"**
```bash
# Service not running in CI environment
# Fix: Either:
# a) Mock SurrealDB in tests
# b) Use test database container
# c) Skip tests if SurrealDB unavailable
```

## Interpreting GitHub Actions Output

### Workflow Run Status

```
✅ PASSED (All jobs successful)
❌ FAILED (One or more jobs failed)
⏭️  SKIPPED (Workflow condition not met)
🔄 IN_PROGRESS (Currently running)
```

### Job-Level Status
```
test-cloud-vault-mcp
├── checkout ✅ (0.5s)
├── setup-python ✅ (2.3s)
├── install-deps ✅ (15.4s)
├── run-linting ✅ (3.2s)
├── run-tests ❌ (45.2s)  <-- This failed
└── upload-coverage ⏭️  (skipped due to failure)
```

### Reading Test Output

Look for these sections:

**FAILED tests:**
```
FAILED tests/test_vault_operations.py::test_read_file - AssertionError: content mismatch
```

**Error details:**
```
E   AssertionError: assert 'actual content' == 'expected content'
E     - expected content
E     + actual content
```

**Coverage summary:**
```
Coverage: 78.5% (total lines covered / total lines)
Minimum required: 75%
Status: PASSED ✅
```

## How to Skip Tests (When Justified)

### Skip Individual Test
```python
# In test file
import pytest

@pytest.mark.skip(reason="Waiting for SurrealDB container fix")
def test_surrealdb_query():
    # This test will be skipped
    pass
```

### Skip Test Conditionally
```python
import pytest
import os

@pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS") == "true",
    reason="Integration tests disabled"
)
def test_sheets_api_integration():
    # Skipped if env var is set
    pass
```

### Mark Test as Expected to Fail
```python
@pytest.mark.xfail(reason="Known issue #123, fixed in PR #456")
def test_known_issue():
    # This test is expected to fail
    # CI will report XFAIL (expected failure) instead of FAIL
    pass
```

### Skip in CI Workflow Only
Edit `.github/workflows/test-cloud-vault-mcp.yml`:
```yaml
- name: Run tests
  run: |
    pytest tests/ -v --ignore=tests/integration/
  # Or:
  env:
    SKIP_INTEGRATION_TESTS: "true"
```

**Important:** Document why tests are skipped. Use GitHub issues to track skipped tests.

## Monitoring CI/CD Status

### Before Each Push
```bash
# Check if CI will pass before pushing
git status              # See what will be tested
git diff origin/main    # Preview changes

# Run fast local checks
pytest tests/unit/ -v --tb=short
```

### After Pushing
```bash
# Check CI status
gh run list --repo=anthropics/claude-code

# Watch CI progress
gh run watch <run-id>

# Get detailed logs if failed
gh run view <run-id> --log | less
```

### Set Up CI Status Notifications

```bash
# Get notified on GitHub
# Go to Settings → Notifications → Actions
# Enable "Send notifications for failed workflow runs"

# Or subscribe to workflow status
gh workflow view test-cloud-vault-mcp.yml --web
```

## CI/CD Environment Configuration

### Environment Variables in Workflows

These are set automatically for CI:

| Variable | CI Value | Local Value |
|----------|----------|-------------|
| VAULT_PATH | /tmp/test-vault | /home/user/vaults/cohezion-vault |
| OLLAMA_URL | http://localhost:11434 | Same |
| SHEETS_ENABLED | false | true (if configured) |
| SurrealDB_URL | (mocked) | http://localhost:8000 |

To use different values in CI, edit `.github/workflows/test-cloud-vault-mcp.yml`:

```yaml
- name: Run tests
  env:
    VAULT_PATH: /home/actions/test-vault
    CUSTOM_VAR: custom-value
  run: pytest tests/ -v
```

## Deployment Pipeline (When Enabled)

### Manual Trigger Deployment
```bash
gh workflow run deploy-production.yml \
  --ref main \
  --field environment=production
```

### View Deployment Status
```bash
gh deployment list --repo anthropics/claude-code
gh deployment status <deployment-id>
```

## Troubleshooting CI/CD Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Tests pass locally, fail in CI" | Environment difference | Check env vars, paths, service config |
| "Intermittent CI failures" | Race condition or timeout | Increase timeout, add retries, fix async code |
| "CI takes 5+ minutes" | Slow dependencies | Cache Python dependencies, parallel jobs |
| "Out of disk space" | Too many artifacts | Reduce artifact retention |
| "GitHub API rate limited" | Too many API calls | Batch calls, use pagination |

## Best Practices

1. **Test locally before pushing**
   ```bash
   pytest tests/ -v
   ```

2. **Keep tests fast** (target: < 30 seconds total)
   - Use mocking for external services
   - Use pytest fixtures for setup
   - Parallelize tests: `pytest -n auto`

3. **Keep CI logs clear**
   - Silence debug output
   - Only show failures
   - Use `--tb=short` for concise tracebacks

4. **Document all skipped tests**
   ```python
   @pytest.mark.skip(reason="GitHub issue #123 - waiting for...")
   ```

5. **Review CI logs on failure**
   - Don't ignore failing CI
   - Fix immediately to avoid blocking others
   - Update tests if behavior change is intentional

## Related Documentation
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-health-checks]]
- [[troubleshooting-mcp-infrastructure]]
- [[mcp-infrastructure-architecture]]

## Related Concepts

- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
- [[runbook-ollama-mcp-operations]]
- [[runbook-health-checks]]
- [[entire-io-sync-daemon-operations]]
- [[runbook-sheets-research-pipeline]]
- [[troubleshooting-mcp-infrastructure]]
