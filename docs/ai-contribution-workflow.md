# AI Assistant Contribution Workflow

## Overview

This document defines how the AI assistant (me) contributes to Cohezion across security monitoring, documentation maintenance, code review, and knowledge management.

## Contribution Modes

### 1. Autonomous Monitoring (Daily)

**What I Do:**
- Run daily security checks
- Monitor for new alerts and vulnerabilities
- Generate reports
- Notify of critical issues

**Communication:**
- Reports saved to `reports/security/`
- Critical issues: Immediate notification
- Summary: Posted to project chat/Slack (if configured)

**Schedule:**
```bash
# Daily at 08:00 UTC
0 8 * * * /home/mike-anderson/dev/cohezion/scripts/security/daily_security_check.py

# Weekly on Monday at 09:00 UTC  
0 9 * * 1 /home/mike-anderson/dev/cohezion/scripts/security/weekly_security_report.sh
```

### 2. Security Triage (On-Demand + Weekly)

**What I Do:**
- Investigate security alerts
- Determine false positives
- Suggest fixes
- Create PRs with security patches

**Triggers:**
- New critical/high alert detected
- Weekly security review
- Manual request: "Check security alerts"

**Workflow:**
```
Alert Detected
    │
    ▼
┌──────────────┐
│   Analyze    │──┐
│    Alert     │  │
└──────────────┘  │
    │             │
    ▼             │
┌──────────────┐  │
│   Classify   │  │
│  Severity    │  │
└──────────────┘  │
    │             │
    ▼             │
┌──────────────┐  │
│   Is False   │──┘──┐
│   Positive?  │      │
└──────────────┘      │
    │                 │
    ▼                 ▼
   Yes               No
    │                 │
    ▼                 ▼
┌──────────┐    ┌──────────────┐
│ Document │    │   Generate   │
│  Reason  │    │     Fix      │
│  Dismiss │    │  (if simple) │
└──────────┘    └──────────────┘
                      │
                      ▼
                ┌──────────────┐
                │   Create PR  │
                │   or Issue   │
                └──────────────┘
```

### 3. Documentation Maintenance (Continuous)

**What I Do:**
- Keep security patterns current
- Update guides when code changes
- Version documentation with releases
- Cross-reference implementations

**Triggers:**
- Code changes affecting security patterns
- New dependency added
- Security tool updates
- Quarterly documentation review

**Areas Monitored:**
```
docs/code-quality/
├── guides/
│   ├── developer-guide.md (when patterns change)
│   └── maintainer-operations.md (when workflows change)
├── reference/
│   └── security-patterns-python-ml.md (when ML code changes)
└── architecture/
    └── overview.md (when architecture changes)
```

### 4. Code Review Support (On-Demand)

**What I Do:**
- Pre-review PRs for security issues
- Check for ML anti-patterns
- Validate dependency changes
- Suggest improvements

**Triggers:**
- PR created with security label
- Manual request: "Review this PR"
- New dependency added to pyproject.toml

**Focus Areas:**
- Path traversal vulnerabilities
- Unsafe deserialization (pickle)
- Hardcoded credentials
- SQL injection
- Command injection
- Resource exhaustion

### 5. Knowledge Base (Always Available)

**What I Do:**
- Answer questions about the codebase
- Explain security alerts
- Guide developers through fixes
- Provide context on architectural decisions

**Access:**
- Direct conversation
- MCP server queries
- Documentation references

## Communication Channels

### 1. Reports (Asynchronous)

**Daily Security Report:**
- Location: `reports/security/daily-security-YYYY-MM-DD.md`
- Content: Alert counts, recent findings, recommendations
- Audience: Maintainers

**Weekly Security Report:**
- Location: `reports/security/weekly-security-YYYY-MM-DD.md`
- Content: Trend analysis, metrics, action items
- Audience: Team, stakeholders

### 2. Notifications (Real-time)

**Critical Alerts:**
- Method: Direct message/mention
- Response time: Immediate
- Content: Alert details, impact, suggested action

**Workflow Failures:**
- Method: Project channel
- Response time: Within 1 hour
- Content: Failure details, logs, recovery steps

### 3. Pull Requests (Collaborative)

**Security Fixes:**
- Created by: AI assistant
- Reviewed by: Maintainers
- Merged by: Maintainers

**Documentation Updates:**
- Created by: AI assistant
- Reviewed by: Maintainers (light review)
- Merged by: AI assistant (after approval)

## Boundaries and Escalation

### What I Handle Autonomously

✅ **Fine to handle:**
- Daily security checks
- Weekly reports
- Documentation updates
- Simple security fixes (dependency updates)
- False positive triage
- Metrics generation
- Alert summaries

### What Requires Human Approval

⚠️ **Needs approval:**
- Code changes to core logic
- Security policy changes
- Access control modifications
- Breaking dependency updates
- Alert dismissals (without clear false positive)

### What I Escalate Immediately

🚨 **Escalate now:**
- Critical vulnerability in production
- Potential data breach
- Suspicious activity
- Security workflow failures
- Token compromise suspicion

## Decision Matrix

| Situation | Action | Approval |
|-----------|--------|----------|
| New critical alert | Create issue, notify | Auto |
| New high alert | Add to backlog | Auto |
| False positive | Dismiss with reason | Required |
| Dependabot security PR | Create, request review | Required to merge |
| Documentation typo | Fix directly | Auto |
| Security pattern update | Create PR | Required |
| Weekly report | Generate and save | Auto |
| CodeQL config change | Create PR | Required |

## Metrics I Track

### Security Metrics
- Open alerts by severity
- Time to fix critical/high
- False positive rate
- Dependency update lag

### Documentation Metrics
- Documentation freshness
- Broken links
- Outdated patterns
- Coverage gaps

### Operational Metrics
- Report generation success rate
- MCP server uptime
- Query response times
- Escalation frequency

## Continuous Improvement

### Monthly Review
- What worked well?
- What caused friction?
- What should be automated?
- What needs human oversight?

### Quarterly Retrospective
- Review all escalations
- Analyze security trends
- Update decision matrix
- Improve documentation

## Getting Started

### To Enable Full Autonomous Mode:

1. **Configure Cron Jobs:**
   ```bash
   # Add to crontab
   crontab -e
   
   # Daily security check
   0 8 * * * /home/mike-anderson/dev/cohezion/scripts/security/daily_security_check.py >> /var/log/cohezion-security.log 2>&1
   
   # Weekly report
   0 9 * * 1 /home/mike-anderson/dev/cohezion/scripts/security/weekly_security_report.sh >> /var/log/cohezion-security.log 2>&1
   ```

2. **Set Up Notifications:**
   ```bash
   # Configure Slack webhook (optional)
   export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

3. **Verify MCP Server:**
   ```bash
   # Test GitHub MCP connection
   python scripts/security/test_mcp_connection.py
   ```

### To Request My Help:

**General:**
- "Check security status"
- "Review this PR"
- "Update documentation for X"
- "Explain alert Y"

**Security:**
- "Investigate alert #123"
- "Is this a false positive?"
- "Generate weekly report"
- "Check dependency vulnerabilities"

**Documentation:**
- "Update security patterns"
- "Add example for X"
- "Fix broken links"
- "Update ADR"

## Contact

**AI Assistant:** Available 24/7 via conversation  
**Maintainer:** manderson240@gmail.com (for escalations)  
**Security:** See SECURITY.md for vulnerability reporting

---

**Version**: 1.0  
**Last Updated**: 2026-02-26  
**Status**: Active
