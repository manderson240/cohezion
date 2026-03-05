# ADR-001: GitHub Code Quality Integration

## Status

**Status**: Accepted  
**Date**: 2026-02-26  
**Author**: Mike Anderson  
**Reviewers**: (Self-reviewed)  
**Supersedes**: N/A  

## Context

Cohezion is an AI training environment framework written in Python with significant ML dependencies. As the codebase grows, we need automated code quality tooling to:

1. Detect security vulnerabilities in Python code and dependencies
2. Ensure dependency hygiene across the supply chain
3. Provide actionable security alerts to developers
4. Maintain compliance with security best practices

Currently, the project has:
- Ruff for linting and basic security (flake8-bandit)
- Pre-commit hooks for secrets detection
- Manual dependency management
- No automated security scanning

## Decision

We will integrate **GitHub Code Quality features** to provide comprehensive security and code quality automation.

### Selected Tools

| Tool | Purpose | Trigger | Severity |
|------|---------|---------|----------|
| **CodeQL** | Static analysis security scanning | Push, PR, Weekly | Medium+ |
| **Dependabot** | Dependency updates and alerts | Weekly | Security patches |
| **Dependency Review** | PR-level dependency scanning | PR creation | High+ |

### Why GitHub Code Quality?

**Pros:**
- ✅ Native GitHub integration (no external services)
- ✅ Free for public repositories
- ✅ MIT licensed (compatible with our MIT license)
- ✅ Comprehensive: code scanning + dependencies + secrets
- ✅ SARIF standard support for interoperability
- ✅ Actionable alerts in GitHub Security tab
- ✅ No additional infrastructure needed

**Cons:**
- ⚠️ GitHub vendor lock-in
- ⚠️ Requires GitHub Actions minutes
- ⚠️ Limited customization vs standalone tools

**Alternatives Considered:**
| Tool | Why Not Selected |
|------|-----------------|
| SonarQube | Additional infrastructure cost, not free |
| Snyk | Paid for advanced features, external service |
| Semgrep | Good but requires separate configuration |
| Trivy | Container-focused, less GitHub integration |

## Implementation

### 1. CodeQL Configuration

**File**: `.github/workflows/codeql.yml`

Key decisions:
- **Query suites**: `security-extended`, `security-and-quality` (comprehensive coverage)
- **Schedule**: Weekly (Mondays at 00:00 UTC) - balances freshness vs compute
- **Paths**: Monitor `src/` and `tests/`, ignore build artifacts
- **Python-specific**: ML/scientific code patterns considered

### 2. Dependabot Configuration

**File**: `.github/dependabot.yml`

Key decisions:
- **Frequency**: Weekly for Python (balances noise vs security)
- **Grouping**: dev-dependencies, ml-dependencies, security-patches
- **Assignment**: Auto-assign to `manderson240` for visibility
- **License checking**: Enabled for compliance

### 3. Dependency Review

**File**: `.github/workflows/dependency-review.yml`

Key decisions:
- **Fail threshold**: High severity (allows medium/low warnings)
- **License allowlist**: MIT, Apache-2.0, BSD variants, ISC
- **PR comments**: Only on failure (reduces noise)

### 4. Security Policy

**File**: `SECURITY.md`

Key decisions:
- **Reporting**: GitHub Security Advisories (private by default)
- **Response time**: 48h acknowledgment, 30d fix (realistic for solo maintainer)
- **Compliance**: OWASP Top 10, CWE Top 25

## Consequences

### Positive

1. **Security posture improved**: Automated detection of vulnerabilities
2. **Developer experience**: Alerts in familiar GitHub interface
3. **Compliance**: Aligns with industry security standards
4. **Cost**: Free for open source
5. **Maintenance**: Minimal ongoing configuration needed

### Negative

1. **CI time**: CodeQL adds ~5-10 minutes to builds
2. **Alert fatigue**: May generate false positives initially
3. **Dependency**: Relies on GitHub ecosystem
4. **Learning curve**: Team needs to understand SARIF and GitHub security

### Migration Path

If we need to migrate away from GitHub Code Quality:
- SARIF outputs can be imported into other tools
- Dependabot alerts can be exported via API
- Custom CodeQL queries are portable

## References

- [GitHub Code Quality Docs](https://docs.github.com/en/code-security/concepts/about-code-quality)
- [CodeQL Query Help](https://docs.github.com/en/code-security/code-scanning/creating-an-advanced-security-configuration/codeql-query-help)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | Adopt GitHub Code Quality | Native integration, comprehensive coverage, free for OSS |
| 2026-02-26 | Weekly Dependabot | Balance between security updates and PR noise |
| 2026-02-26 | High severity threshold | Allow medium/low for triage, block critical in PRs |

## Appendix

### GitHub Actions Usage Estimate

| Workflow | Frequency | Minutes/Run | Monthly Minutes |
|----------|-----------|-------------|-----------------|
| CodeQL | Weekly | 10 | 40 |
| Dependency Review | Per PR | 2 | ~20 |
| **Total** | - | - | **~60** |

*Well within GitHub free tier (2000 minutes/month for public repos)*

### Security Alert Triage Matrix

| Severity | Response Time | Action |
|----------|--------------|--------|
| Critical | 24 hours | Immediate patch |
| High | 72 hours | Next sprint |
| Medium | 2 weeks | Backlog |
| Low | 1 month | Deprioritize |
