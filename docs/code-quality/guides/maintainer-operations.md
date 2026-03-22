# Maintainer Operations Guide: Code Quality

## Overview

This guide is for **maintainers** of the Cohezion project responsible for security operations, alert triage, and code quality infrastructure.

## Daily Operations

### Morning Security Check (5 minutes)

```bash
# Quick security dashboard check
gh api /repos/manderson240/cohezion/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | [.number, .rule.id, .tool.name]'
```

**Checklist:**
- [ ] New CodeQL alerts overnight?
- [ ] New Dependabot alerts?
- [ ] Any Critical/High severity issues?
- [ ] Failed security workflows?

### Triage New Alerts

**Using GitHub CLI:**
```bash
# List open code scanning alerts
gh api /repos/manderson240/cohezion/code-scanning/alerts \
  -X GET \
  -f state=open \
  --jq '.[] | {number: .number, rule: .rule.id, severity: .rule.security_severity_level, path: .path}'

# List Dependabot alerts
gh api /repos/manderson240/cohezion/dependabot/alerts \
  -X GET \
  -f state=open \
  --jq '.[] | {number: .number, severity: .security_advisory.severity, package: .dependency.package.name}'
```

## Weekly Operations

### Monday: Security Review (30 minutes)

**1. Review Weekly CodeQL Scan**
```bash
# Get last week's alerts
gh api /repos/manderson240/cohezion/code-scanning/alerts \
  -f state=open \
  --jq '.[] | select(.created_at > "'$(date -d '7 days ago' +%Y-%m-%d)'")'
```

**2. Review Dependabot PRs**
```bash
# List open Dependabot PRs
gh pr list --author "dependabot[bot]" --state open

# Check CI status on each
gh pr checks $(gh pr list --author "dependabot[bot]" --json number -q '.[].number')
```

**3. Security Metrics Report**
```bash
# Generate metrics
python3 -c "
import json
import subprocess

# Get alert counts
alerts = subprocess.run([
    'gh', 'api', '/repos/manderson240/cohezion/code-scanning/alerts',
    '-X', 'GET', '-f', 'state=open'
], capture_output=True, text=True)

data = json.loads(alerts.stdout)
critical = len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'critical'])
high = len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'high'])

print(f'Open Alerts: {len(data)}')
print(f'  Critical: {critical}')
print(f'  High: {high}')
"
```

### Wednesday: Dependency Updates (15 minutes)

**Process Dependabot PRs:**

```bash
# Auto-merge patch updates (low risk)
for pr in $(gh pr list --author "dependabot[bot]" --json number,title -q '.[] | select(.title | contains("bump")) | .number'); do
    gh pr merge $pr --squash --delete-branch
done

# Review minor updates manually
gh pr list --author "dependabot[bot]" --state open
```

**Security Patches (Priority):**
```bash
# Find security patches
gh pr list --author "dependabot[bot]" --search "security" --state open

# Fast-track security fixes
gh pr review [PR_NUMBER] --approve
gh pr merge [PR_NUMBER] --squash
```

## Monthly Operations

### Security Audit (2 hours)

**1. Full Dependency Review**
```bash
# Generate SBOM
gh api /repos/manderson240/cohezion/dependency-graph/sbom \
  --jq '.sbom'

# Check for outdated dependencies
python3 -c "
import subprocess
import json

# Get dependency graph
deps = subprocess.run([
    'gh', 'api', '/repos/manderson240/cohezion/dependency-graph/dependencies'
], capture_output=True, text=True)

print('Dependency Review Complete')
"
```

**2. Access Review**
```bash
# List repository collaborators
gh api /repos/manderson240/cohezion/collaborators \
  --jq '.[] | {login: .login, permission: .permissions.admin}'

# Check recent token usage
gh api /repos/manderson240/cohezion/traffic/clones
```

**3. Policy Review**
- Update SECURITY.md if processes changed
- Review CONTRIBUTING.md security sections
- Check ADRs are current

## Quarterly Operations

### Security Deep Dive (4 hours)

**1. Penetration Testing Simulation**
```bash
# Run comprehensive scans
bandit -r src/ -f json -o quarterly-bandit.json
detect-secrets scan > quarterly-secrets.json

# Analyze trends
diff <(cat last-quarter-bandit.json) <(cat quarterly-bandit.json)
```

**2. Dependency Health Check**
```bash
# Check for abandoned dependencies
python3 scripts/security/check_dependencies_health.py

# Review transitive dependencies
dependency-check --project cohezion --scan src/
```

**3. Compliance Review**
- OWASP Top 10 coverage: ✅
- CWE Top 25 coverage: ✅
- SLSA Level 1: ✅
- Update compliance documentation

**4. Token Rotation**
```bash
# Rotate GitHub PAT
# 1. Create new token at https://github.com/settings/tokens
# 2. Update .env: GITHUB_TOKEN=new_token
# 3. Update MCP server config
# 4. Test MCP connection
# 5. Revoke old token
```

## Alert Response Procedures

### Critical Vulnerability Response (0-24 hours)

**Immediate (0-1 hour):**
```bash
# 1. Acknowledge receipt
gh api /repos/manderson240/cohezion/code-scanning/alerts/[ALERT_NUMBER] \
  -X PATCH -f dismissed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -f dismissed_reason="false_positive" \
  --jq '.dismissed_at'

# 2. Create emergency issue
gh issue create --title "CRITICAL: [CVE-ID]" \
  --label "security,critical" \
  --body "See alert #[ALERT_NUMBER]"

# 3. Notify team
gh api /repos/manderson240/cohezion/issues/[ISSUE_NUMBER]/comments \
  -f body="@manderson240 Critical security issue requires immediate attention"
```

**Short-term (1-24 hours):**
- Assess scope and impact
- Develop fix or mitigation
- Test fix in staging
- Deploy hotfix if production affected

**Post-incident (24-72 hours):**
- Document in security advisory
- Update runbooks
- Review detection gaps

### False Positive Management

**When to Mark as False Positive:**

1. **Test code with intentionally weak patterns**
   ```python
   # Example: Test with hardcoded credentials
   TEST_PASSWORD = "password123"  # nosec: B105 - Test data
   ```

2. **Dead/unreachable code**
   ```python
   # CodeQL detects issue in unreachable code
   if False:
       exec(user_input)  # Never executed
   ```

3. **Intentional design patterns**
   ```python
   # Pickle for model serialization (intentional)
   model = pickle.load(f)  # nosec: B301 - Required for ML
   ```

**Process:**
```bash
# Dismiss with reason
curl -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/manderson240/cohezion/code-scanning/alerts/[ALERT_NUMBER] \
  -d '{
    "dismissed_reason": "false_positive",
    "dismissed_comment": "Intentional use in test fixtures"
  }'
```

## Workflow Monitoring

### Check Workflow Health

```bash
# List recent workflow runs
gh run list --workflow=codeql.yml --limit 10

# Check specific run
gh run view [RUN_ID]

# View logs
gh run view [RUN_ID] --log
```

### Common Failures and Fixes

**1. CodeQL: "No source code found"**
```bash
# Fix: Ensure Python dependencies are installed before analysis
# In workflow: Add dependency installation step
```

**2. Dependabot: "Too many PRs"**
```yaml
# Fix: Increase grouping in dependabot.yml
groups:
  all-dependencies:
    patterns:
      - "*"
    update-types:
      - "minor"
      - "patch"
```

**3. Dependency Review: "License violation"**
```yaml
# Fix: Update license allowlist
with:
  allow-licenses: MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause, ISC, MPL-2.0
```

## Metrics and Reporting

### Security Dashboard

**Key Metrics:**

```python
# scripts/security/metrics.py
import json
import subprocess
from datetime import datetime, timedelta

def get_security_metrics():
    """Generate security metrics report."""
    
    # CodeQL metrics
    alerts = subprocess.run([
        'gh', 'api', '/repos/manderson240/cohezion/code-scanning/alerts',
        '-f', 'state=open'
    ], capture_output=True, text=True)
    
    data = json.loads(alerts.stdout)
    
    metrics = {
        'date': datetime.now().isoformat(),
        'total_open_alerts': len(data),
        'by_severity': {
            'critical': len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'critical']),
            'high': len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'high']),
            'medium': len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'medium']),
            'low': len([a for a in data if a.get('rule', {}).get('security_severity_level') == 'low']),
        },
        'by_tool': {
            'codeql': len([a for a in data if a.get('tool', {}).get('name') == 'CodeQL']),
            'dependabot': len([a for a in data if 'dependabot' in a.get('tool', {}).get('name', '')]),
        }
    }
    
    return metrics

if __name__ == '__main__':
    print(json.dumps(get_security_metrics(), indent=2))
```

### Weekly Report Template

```markdown
# Security Weekly Report

**Week**: [DATE]  
**Prepared by**: [MAINTAINER]

## Summary

- **Open Alerts**: [X] total
  - Critical: [X]
  - High: [X]
  - Medium: [X]
  - Low: [X]

## New This Week

- [Alert #123] py/path-injection (High) - Fixed in PR #456
- [Dependabot] Bump requests 2.31.0 → 2.32.0 (Security patch) - Merged

## Actions Taken

- Fixed: [X] alerts
- Dismissed: [X] false positives
- Updated: [X] dependencies

## Pending Actions

- [ ] Review medium severity alerts
- [ ] Test dependency updates in staging
- [ ] Update security documentation

## Notes

[Any observations or concerns]
```

## Automation Scripts

### Auto-dismiss False Positives

```bash
#!/bin/bash
# scripts/auto-dismiss.sh

# Dismiss alerts matching patterns
curl -s "https://api.github.com/repos/manderson240/cohezion/code-scanning/alerts" \
  -H "Authorization: Bearer $GITHUB_TOKEN" | \
  jq -r '.[] | select(.rule.id == "py/test-failure") | .number' | \
  while read alert_id; do
    curl -X PATCH \
      "https://api.github.com/repos/manderson240/cohezion/code-scanning/alerts/$alert_id" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -d '{"dismissed_reason": "false_positive", "dismissed_comment": "Test fixture pattern"}'
  done
```

### Security Alert Slack Notification

```python
# scripts/notify_slack.py
import json
import os
import requests

def notify_slack(message, webhook_url):
    """Send security alert to Slack."""
    payload = {
        "text": f":warning: Security Alert: {message}",
        "channel": "#security-alerts"
    }
    requests.post(webhook_url, json=payload)

# Usage
if __name__ == '__main__':
    webhook = os.getenv('SLACK_WEBHOOK_URL')
    notify_slack("New critical vulnerability detected", webhook)
```

## Emergency Contacts

| Role | Contact | Method |
|------|---------|--------|
| Primary Maintainer | manderson240 | GitHub: @manderson240 |
| Email | manderson240@gmail.com | manderson240@gmail.com |
| Security | GitHub Security | https://github.com/manderson240/cohezion/security |

## Resources

### Quick Links

- [Security Dashboard](https://github.com/manderson240/cohezion/security)
- [Code Scanning](https://github.com/manderson240/cohezion/security/code-scanning)
- [Dependabot](https://github.com/manderson240/cohezion/security/dependabot)
- [Actions](https://github.com/manderson240/cohezion/actions)

### Documentation

- [Developer Guide](./developer-guide.md)
- [Architecture Overview](../architecture/overview.md)
- [ADR-001: GitHub Code Quality](../adrs/adr-001-github-code-quality.md)
- [GitHub Security Docs](https://docs.github.com/en/code-security)

---

**Last Updated**: 2026-02-26  
**Version**: 1.0
