# GitHub Code Quality Architecture

## Executive Summary

This document describes the architecture for implementing GitHub's Code Quality features within the Cohezion project. The implementation follows GitHub's best practices while respecting their MIT license and adapting concepts for our Python-based ML/AI training environment.

## Architecture Principles

1. **Security First**: All changes prioritize security without compromising development velocity
2. **License Compliance**: All implementations respect GitHub's MIT license
3. **Minimal Overhead**: Automated tooling reduces manual security reviews
4. **Developer Experience**: Security feedback integrated into existing workflows
5. **Transparency**: All security processes documented and auditable

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Platform                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   CodeQL     │  │  Dependabot  │  │   Secret     │      │
│  │   Analysis   │  │   Updates    │  │   Scanning   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          │                 │                 │
    ┌─────▼─────┐     ┌────▼────┐      ┌────▼────┐
    │   SARIF   │     │   PR    │      │  Alert  │
    │  Results  │     │ Checks  │      │   API   │
    └─────┬─────┘     └────┬────┘      └────┬────┘
          │                │                 │
┌─────────▼────────────────▼─────────────────▼──────────────┐
│              GitHub Security Dashboard                    │
├───────────────────────────────────────────────────────────┤
│  • Security Alerts     • Dependabot Alerts               │
│  • Code Scanning       • Secret Scanning                 │
│  • Vulnerability Graph                                   │
└───────────────────────────────────────────────────────────┘
          │
          │ Webhooks/API
          │
┌─────────▼────────────────────────────────────────────────┐
│              MCP Server Integration                       │
├───────────────────────────────────────────────────────────┤
│  GitHub MCP Server → Code Security Tools                   │
│  • list_code_scanning_alerts                               │
│  • list_dependabot_alerts                                  │
│  • get_workflow_run                                        │
│  • create_pull_request                                     │
└───────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. CodeQL Analysis Engine

**Purpose**: Static security analysis for Python code

**Configuration**:
- **Query Suites**: `security-extended`, `security-and-quality`
- **Languages**: Python 3.11, 3.13
- **Paths**: `src/`, `tests/` (excludes `node_modules/`, `__pycache__/`, `.venv/`)
- **Triggers**: Push to `main`/`develop`, PRs, Weekly schedule

**Output Format**: SARIF (Static Analysis Results Interchange Format)

**Key Queries**:
- Python security vulnerabilities (SQL injection, XSS, path traversal)
- CWE Top 25 coverage
- Custom ML-specific patterns (unsafe deserialization, pickle usage)

### 2. Dependabot Dependency Manager

**Purpose**: Automated dependency updates and security alerts

**Ecosystems**:
- **pip**: Python packages (weekly updates)
- **GitHub Actions**: CI/CD dependencies (monthly updates)

**Grouping Strategy**:
```
dev-dependencies/     → pytest, ruff, mypy
ml-dependencies/      → torch, transformers, numpy
security-patches/     → Critical CVE fixes
actions-updates/        → GitHub Actions versions
```

**Update Policy**:
- Patch updates: Auto-merge after CI passes
- Minor updates: Review for breaking changes
- Major updates: Manual review required

### 3. Dependency Review Action

**Purpose**: PR-level vulnerability scanning

**Blocking Rules**:
- Fails on High/Critical severity
- Checks license compatibility
- Comments summary on PR

**License Allowlist**:
- MIT
- Apache-2.0
- BSD-3-Clause, BSD-2-Clause
- ISC

### 4. MCP Server Bridge

**Purpose**: AI assistant integration with GitHub security data

**Architecture**:
```
Docker Container
    ├── github-mcp-server
    │   ├── GitHub API Client
    │   ├── Tool Registry
    │   └── stdio Transport
    └── Environment
        ├── GITHUB_PERSONAL_ACCESS_TOKEN (from .env)
        └── GITHUB_TOOLSETS
```

**Available Tools**:
- `list_code_scanning_alerts` - Query security findings
- `list_dependabot_alerts` - Check dependency vulnerabilities
- `get_workflow_run` - Monitor CI status
- `get_repository` - Repository metadata
- `list_pull_requests` - PR security status

## Data Flow

### Security Alert Lifecycle

```
1. Vulnerability Discovered
   │
   ├─→ CodeQL: Static analysis detects issue
   ├─→ Dependabot: CVE published for dependency
   └─→ Secret Scanning: Credential committed
   │
2. Alert Generated
   │
   ├─→ SARIF uploaded to GitHub
   ├─→ Security dashboard updated
   └─→ Notification sent (if configured)
   │
3. Alert Triaged
   │
   ├─→ Severity assessed (Critical/High/Medium/Low)
   ├─→ CWE category assigned
   └─→ Affected paths identified
   │
4. Remediation
   │
   ├─→ Automated: Dependabot PR created
   ├─→ Semi-auto: CodeQL autofix suggested
   └─→ Manual: Developer fixes code
   │
5. Verification
   │
   ├─→ CI runs with security checks
   ├─→ Alert dismissed/resolved
   └─→ Audit trail maintained
```

### PR Security Workflow

```
Developer Creates PR
        │
        ▼
┌──────────────────┐
│ Dependency Review│────┐
│ Action Runs      │    │
└──────────────────┘    │
        │               │
        ▼               │
┌──────────────────┐    │
│ Check Licenses   │    │
│ ✓ MIT/Apache     │    │
└──────────────────┘    │
        │               │
        ▼               │
┌──────────────────┐    │
│ Check Vulns      │    │
│ ✓ No Critical    │────┘
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ CodeQL Analysis  │
│ (if scheduled)   │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ PR Can Merge     │
│ (if all pass)    │
└──────────────────┘
```

## Security Boundaries

### Trust Model

| Component | Trust Level | Mitigation |
|-----------|-------------|------------|
| GitHub Platform | High | HTTPS, 2FA, branch protection |
| CodeQL Queries | Medium | Review custom queries, use official packs |
| MCP Server | Medium | Token in .env, not committed |
| Docker Images | Medium | Use official `ghcr.io/github/github-mcp-server` |
| CI Runners | Medium | Ephemeral, minimal permissions |

### Token Scoping

**GITHUB_TOKEN** (via `.env`):
- **Scopes**: `repo`, `security_events`, `read:org`
- **Rotation**: Recommended quarterly
- **Storage**: `.env` file (gitignored)
- **Usage**: MCP Server, CI workflows

## Scalability Considerations

### Performance

| Workflow | Estimated Time | Optimization |
|----------|----------------|--------------|
| CodeQL Initial | ~10 min | Caching, parallelization |
| CodeQL Incremental | ~3 min | Incremental analysis |
| Dependabot | ~2 min | Grouped updates |
| Dependency Review | ~1 min | Cached vulnerability DB |

### Resource Limits

- **GitHub Actions**: 2000 minutes/month (free tier)
- **CodeQL**: 35,000 lines of Python analyzed
- **SARIF Upload**: 1000 results per upload
- **Dependabot PRs**: 10 open at a time

### Monitoring

```python
# Metrics to track
security_metrics = {
    "codeql_alerts_open": 0,
    "dependabot_alerts_open": 0,
    "avg_time_to_fix": "3 days",
    "false_positive_rate": 0.05,
    "ci_security_failures": 0
}
```

## Integration Points

### With Existing Tools

| Existing Tool | Integration | Status |
|--------------|-------------|--------|
| Ruff | Complements (fast vs deep) | ✅ Active |
| Pre-commit | Runs before commit | ✅ Active |
| pytest | Security tests | ✅ Active |
| mypy | Type safety | ✅ Active |
| detect-secrets | Secret scanning | ✅ Active |
| bandit | Python security | ✅ Active |

### With Development Workflow

```
Local Development
    │
    ├─→ Pre-commit hooks (bandit, detect-secrets)
    │
    ▼
Push to Branch
    │
    ├─→ CI: CodeQL (if scheduled)
    ├─→ CI: Dependency review (if PR)
    │
    ▼
Pull Request
    │
    ├─→ Required: Dependency review pass
    ├─→ Required: Tests pass
    │
    ▼
Merge to Main
    │
    ├─→ Trigger: CodeQL full scan
    ├─→ Trigger: Dependabot check
    │
    ▼
Weekly
    │
    └─→ Scheduled CodeQL scan
        └─→ Dependabot updates
```

## Disaster Recovery

### Failure Scenarios

1. **CodeQL Fails to Run**
   - Fallback: Manual `bandit` scan in CI
   - Escalation: Block merge until fixed

2. **Dependabot Overwhelming**
   - Mitigation: Reduce open PR limit to 5
   - Grouping: Increase grouping granularity

3. **False Positive Flood**
   - Action: Configure `.github/codeql.yml` exclusions
   - Documentation: Maintain false positive list

4. **Token Compromise**
   - Immediate: Rotate token
   - Audit: Check recent API calls
   - Review: Access permissions

### Backup Strategy

- **SARIF Results**: Kept for 90 days in GitHub
- **Alert History**: GitHub Security tab retains history
- **Configuration**: All configs in git (`.github/`)

## Compliance Mapping

### OWASP Top 10 Coverage

| OWASP Category | CodeQL Query | Status |
|-----------------|--------------|--------|
| A01: Broken Access Control | py/path-injection | ✅ |
| A02: Cryptographic Failures | py/weak-crypto | ✅ |
| A03: Injection | py/sql-injection | ✅ |
| A06: Vulnerable Components | Dependabot | ✅ |
| A07: Auth Failures | py/hardcoded-credentials | ✅ |

### CWE Coverage

- **CWE-79**: XSS (Cross-site scripting)
- **CWE-89**: SQL Injection
- **CWE-352**: CSRF
- **CWE-798**: Hardcoded Credentials
- **CWE-918**: Server-Side Request Forgery

### SLSA Levels

| Level | Requirement | Status |
|-------|-------------|--------|
| 1 | Provenance generation | ✅ SBOM via Dependabot |
| 2 | Signed provenance | ⚠️ Future: Artifact attestations |
| 3 | Build environment isolation | ✅ GitHub Actions ephemeral |
| 4 | Reproducible builds | ❌ Not yet implemented |

## Future Roadmap

### Phase 2 (Q2 2026)
- [ ] Custom CodeQL queries for ML-specific patterns
- [ ] Artifact attestations (SLSA Level 2)
- [ ] Security campaigns for alert triage

### Phase 3 (Q3 2026)
- [ ] Security configuration at organization level
- [ ] Auto-triage rules for Dependabot
- [ ] Integration with security overview dashboard

### Phase 4 (Q4 2026)
- [ ] Multi-repository variant analysis
- [ ] Custom security configurations
- [ ] Security risk assessment automation

## References

1. [GitHub Code Security Documentation](https://docs.github.com/en/code-security)
2. [CodeQL for Python](https://code.github.com/codeql/python/)
3. [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/)
4. [OWASP Code Review Guide](https://owasp.org/www-pdf-archive/OWASP_Code_Review_Guide_v2.pdf)
5. [SLSA Framework](https://slsa.dev/)

## Appendix

### A. Configuration Files

```
.github/
├── codeql.yml                    # CodeQL workflow
├── dependabot.yml                # Dependency management
├── dependency-review.yml         # PR security checks
└── workflows/
    └── (existing CI workflows)

SECURITY.md                       # Security policy
CONTRIBUTING.md                   # Updated with security
mcp_servers.json                  # MCP server config
docs/code-quality/                # This documentation
```

### B. License Attribution

All GitHub Code Quality concepts adapted under MIT License:
- © 2024 GitHub, Inc.
- Repository: https://github.com/github/github-mcp-server
- License: MIT (https://github.com/github/github-mcp-server/blob/main/LICENSE)

Implementation files in this repository are also under MIT License.
