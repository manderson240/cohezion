# Developer Guide: Code Quality

## Quick Start

As a developer on Cohezion, here's what you need to know about code quality.

## Before You Commit

### 1. Pre-commit Hooks (Automatic)

Security checks run automatically:

```bash
$ git commit -m "feat: add new feature"

[INFO] Installing environment for https://github.com/pre-commit/pre-commit-hooks
[INFO] Running security checks...

- trailing-whitespace..............................Passed
- end-of-file-fixer..............................Passed
- check-yaml.......................................Passed
- detect-private-key...............................Passed
- detect-secrets...................................Passed
- bandit...........................................Passed
```

**If hooks fail**, fix the issues before committing.

### 2. Manual Security Check (Optional)

```bash
# Run security scans locally
uv run bandit -r src/cohezion

# Check for secrets
uv run detect-secrets scan
```

## Creating a Pull Request

### What Happens Automatically

When you create a PR, GitHub runs:

1. **Dependency Review** (~1 min)
   - Checks for vulnerable dependencies
   - Validates licenses
   - Comments results on PR

2. **CodeQL Analysis** (if scheduled)
   - Runs on PRs to `main`
   - Results in "Security" tab

3. **Existing CI**
   - Tests, linting, type checks

### Understanding the Checks

#### ✅ All checks pass
```
✅ Dependency Review — No vulnerabilities found
✅ CodeQL Analysis — No new alerts
✅ CI / Tests — All tests passed
```

**You can merge!**

#### ⚠️ Dependency Review found issues
```
❌ Dependency Review — High severity vulnerability detected

Package: requests@2.31.0
CVE-2024-XXXX (High)

Recommendation: Upgrade to requests@2.32.0
```

**Action Required:**
1. Update the dependency: `uv pip install requests>=2.32.0`
2. Update `pyproject.toml`
3. Commit and push
4. Re-run checks

#### ⚠️ CodeQL found issues
```
❌ CodeQL Analysis — 2 new alerts

1. py/hardcoded-credentials (Medium)
   File: src/cohezion/config.py:45
   
2. py/path-injection (High)
   File: src/cohezion/utils.py:23
```

**Action Required:**
1. Check Security tab for details
2. Fix or dismiss (with reason)
3. Re-run analysis

## Working with Security Alerts

### Viewing Alerts

**In GitHub:**
1. Go to **Security** tab → **Code scanning alerts**
2. Filter by severity, tool, or status
3. Click alert for details

**With MCP Server:**
```bash
# List open alerts
# (Requires MCP server setup)
```

### Triaging Alerts

**Severity Guide:**

| Severity | Response Time | Action |
|----------|--------------|--------|
| **Critical** | 24 hours | Fix immediately |
| **High** | 72 hours | Next priority |
| **Medium** | 2 weeks | Backlog |
| **Low** | 1 month | Optional |

**Common Alert Types:**

**1. py/hardcoded-credentials**
```python
# BAD: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"

# GOOD: Use environment variables
API_KEY = os.getenv("API_KEY")
```

**2. py/path-injection**
```python
# BAD: User-controlled path
with open(user_input, "r") as f:
    data = f.read()

# GOOD: Validate path
import os
from pathlib import Path

safe_path = Path("/safe/directory") / Path(user_input).name
if not safe_path.resolve().startswith("/safe/directory"):
    raise ValueError("Invalid path")
with open(safe_path, "r") as f:
    data = f.read()
```

**3. py/sql-injection**
```python
# BAD: String formatting
query = f"SELECT * FROM users WHERE id = {user_id}"

# GOOD: Parameterized queries
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### Dismissing False Positives

**When to dismiss:**
- Alert is in test code
- Pattern is intentional (with security justification)
- Code is unreachable (dead code)

**How to dismiss:**
1. In Security tab, click alert
2. Click **Dismiss**
3. Select reason:
   - **False positive** - Code doesn't actually have the vulnerability
   - **Won't fix** - Acceptable risk with justification
   - **Used in tests** - Test data, not production
4. Add comment explaining why

**Example comment:**
```
False positive: This is test data with intentionally weak
credentials for testing authentication failure scenarios.
Not used in production.
```

## Managing Dependencies

### When Dependabot Creates PRs

You'll receive PRs like:
```
Bump requests from 2.31.0 to 2.32.0

Changelog:
- Fixed CVE-2024-XXXX
- Improved connection pooling
```

**Review process:**

1. **Check CI status**
   - All tests must pass
   - Security scans must pass

2. **Review changelog**
   - Breaking changes?
   - Security fixes?
   - API changes?

3. **Merge if:**
   - ✅ CI passes
   - ✅ No breaking changes
   - ✅ Security fix (priority)

**Auto-merge configuration:**
- Patch updates: Can auto-merge if CI passes
- Minor updates: Review first
- Major updates: Always review

### Manual Dependency Updates

```bash
# Update all dependencies
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt

# Update specific package
uv pip install package>=version

# Check for vulnerabilities
uv pip install safety
uv run safety check
```

## Local Security Tools

### Bandit (Python Security Linter)

```bash
# Install
uv pip install bandit

# Run on entire codebase
uv run bandit -r src/cohezion

# Run on specific file
uv run bandit src/cohezion/utils.py

# Output formats
uv run bandit -r src/ -f json -o bandit-report.json
```

### Detect Secrets

```bash
# Install
uv pip install detect-secrets

# Scan for secrets
uv run detect-secrets scan

# Update baseline
uv run detect-secrets scan > .secrets.baseline

# Audit potential secrets
uv run detect-secrets audit .secrets.baseline
```

### Safety (Dependency Vulnerabilities)

```bash
# Install
uv pip install safety

# Check current environment
uv run safety check

# Check with full report
uv run safety check --full-report
```

## Security Best Practices

### Code Guidelines

**1. Never commit secrets**
```bash
# Use environment variables
export API_KEY="your-key"

# Or .env file (gitignored)
echo "API_KEY=your-key" >> .env
```

**2. Validate all inputs**
```python
from pydantic import BaseModel

class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
```

**3. Use type hints**
```python
# Helps static analysis find bugs
def process_data(data: dict[str, Any]) -> Result:
    ...
```

**4. Keep dependencies updated**
```bash
# Check weekly
uv run pip list --outdated

# Update security patches immediately
```

### Review Checklist

Before creating PR:

- [ ] Pre-commit hooks pass
- [ ] No hardcoded secrets
- [ ] Input validation added
- [ ] Tests pass locally
- [ ] Security scan passes
- [ ] Dependencies up to date (if modified)

After PR created:

- [ ] Dependency Review passes
- [ ] CodeQL Analysis passes (no new alerts)
- [ ] All CI checks pass
- [ ] Reviewer approved

## Troubleshooting

### Common Issues

**1. Pre-commit hooks failing**
```bash
# Update hooks
uv run pre-commit autoupdate

# Clean and reinstall
uv run pre-commit clean
uv run pre-commit install
```

**2. CodeQL false positive**
- Check if suppression comment is appropriate:
```python
# nosec: B105 - This is test data, not a real secret
password = "test_password_123"
```

**3. Dependency conflict**
```bash
# Check for conflicts
uv pip check

# Resolve manually
# Update pyproject.toml with compatible versions
```

**4. Security alert not relevant**
- Dismiss with appropriate reason
- Add comment for future reference

### Getting Help

**Security Questions:**
- Check [SECURITY.md](../../SECURITY.md)
- Create GitHub Security Advisory (for vulnerabilities)
- Email: manderson240@gmail.com (urgent issues)

**Tool Issues:**
- CodeQL: [GitHub Docs](https://docs.github.com/en/code-security/code-scanning)
- Dependabot: [Configuration](https://docs.github.com/en/code-security/dependabot)
- Bandit: [Documentation](https://bandit.readthedocs.io/)

## Quick Reference

### Commands

```bash
# Security scan
uv run bandit -r src/

# Secret check
uv run detect-secrets scan

# Dependency check
uv run safety check

# Pre-commit run
uv run pre-commit run --all-files

# Update dependencies
uv pip install -U package_name
```

### Severity Levels

| Icon | Severity | Response |
|------|----------|----------|
| 🔴 | Critical | Fix immediately |
| 🟠 | High | Next sprint |
| 🟡 | Medium | Backlog |
| 🔵 | Low | Optional |

### File Locations

```
.github/workflows/codeql.yml          # CodeQL config
.github/dependabot.yml               # Dependabot config
.github/workflows/dependency-review.yml  # PR checks
SECURITY.md                          # Security policy
CONTRIBUTING.md                      # Security guidelines
```

---

**Questions?** Check the full [Architecture Overview](../architecture/overview.md) or [Security Policy](../../SECURITY.md).
