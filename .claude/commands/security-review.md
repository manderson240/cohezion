---
description: Review code for security vulnerabilities
allowed-tools: Read, Grep, Bash(git:*)
model: sonnet
---

Perform a comprehensive security review of recently changed files.

**Files to review:**
!`git diff --name-only HEAD~10 2>/dev/null || git diff --name-only HEAD 2>/dev/null || echo "(could not determine changed files — review all source files)"`

**Check each file for:**

**Injection Vulnerabilities:**
- SQL injection (string concatenation in queries)
- Command injection (shell commands with user input)
- Path traversal (user-controlled file paths)
- SSTI / template injection

**Authentication & Authorization:**
- Missing auth checks on endpoints
- Insecure session management
- Hardcoded credentials or API keys
- Overly permissive access controls

**Data Handling:**
- Sensitive data logged or exposed in errors
- Unencrypted storage of secrets
- Insecure deserialization
- Missing input validation at system boundaries

**Web/API Specific:**
- Cross-site scripting (XSS) — unescaped output
- CORS misconfiguration
- Missing CSRF protection
- Insecure direct object references (IDOR)

**Dependencies:**
- Known-vulnerable package versions
- Unnecessary permissions requested

**For each issue found, report:**
1. File and line number
2. Severity: Critical / High / Medium / Low
3. Vulnerability description
4. Recommended fix with code example if helpful

Prioritize by severity. If no files changed, summarize the overall security posture of the codebase.
