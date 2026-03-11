---
title: Never Print Credentials: API Keys and Tokens Must Never Appear in Logs
date: 2026-02-23
severity: CRITICAL
category: security
cost_of_forgetting: "Credential exposure in logs, CI output, or exception traces; mandatory key rotation and potential unauthorized access"
tags: [security, credentials, logging, api-keys]
status: validated
aspect: knower
neural:
  activation: 0.481
  stage: growing
  cluster: lessons
---

# Lesson: Never Print Credentials: API Keys and Tokens Must Never Appear in Logs

## Context

During Cohezion development, API keys (Anthropic, Ollama, SurrealDB connection strings) were being logged in debug output. A developer added `logger.debug(f"Connecting with key: {api_key}")` to troubleshoot a connection issue. The debug log was committed to the test output in CI, making the API key visible in the CI build log. The key had to be rotated immediately. A second incident involved a bearer token appearing in an exception traceback that was captured in a log file.

## Problem

Credential leakage through logging has cascading consequences:

1. **Log persistence**: Log files, CI output, and exception traces are often stored persistently and may be accessible to broader audiences than the developer who wrote the log statement
2. **Exception tracebacks**: Python's default exception handling includes local variables in tracebacks. If a credential is in scope when an exception is raised, it appears in the traceback automatically.
3. **Debug-to-production leak**: Debug log statements added during development may not be removed before merge. Even at DEBUG level, the credential is written to the log destination.
4. **Cascading rotation**: Once a credential appears in any log, it must be rotated immediately. This disrupts all services that use that credential.

## Core Learning

**No credential, API key, token, or connection string may appear in any log, stdout, or exception message. Mask or omit always.**

### Pattern
```python
# WRONG: logging credentials
logger.debug(f"Connecting with key: {api_key}")

# RIGHT: mask credentials
logger.debug(f"Connecting with key: {api_key[:4]}...{api_key[-4:]}")
raise ValueError("Connection failed -- check credentials in environment")
```

## Solution

Three protective measures are now standard across all Cohezion code:

1. **Masking function**: A utility function `mask_credential(key)` returns `key[:4]...key[-4:]` for any credential that must appear in diagnostics
2. **Exception handling**: Custom exception classes that never include credentials in their message. Connection errors say "check credentials in environment" rather than displaying the credential.
3. **Code review discipline**: Any `print()`, `logger.*()`, or `raise` statement that references a variable containing credentials is flagged during review

## Prevention

- **Never log credentials at any level**: Not even DEBUG. Use masked versions for diagnostic output.
- **Use environment variables**: Store credentials in environment, not in code. Log the environment variable name, not the value.
- **Sanitize exception messages**: Custom exceptions should reference "credentials in environment," not the credential itself
- **Rotate immediately**: If a credential appears in any log, rotate it before investigating the leak source
- **Lint for credential patterns**: Use ruff or custom rules to flag `f"...{api_key}..."` patterns in log statements

## Cost of Forgetting

- **Credential exposure**: API keys visible in CI logs, error reports, or log files
- **Mandatory rotation**: Every exposed credential requires immediate rotation across all services
- **Potential unauthorized access**: If logs are accessible to unauthorized parties, the credential may be used maliciously
- **Compliance violations**: Credential exposure may violate security compliance requirements

## Recommendations

### Do
- Mask all credentials in logs: show first 4 + last 4 characters only
- Rotate any credential that appeared in logs

### Don't
- Log full API keys even at DEBUG level
- Include credentials in exception messages or tracebacks

## Related Concepts

- [[compound-engineering]] - Security discipline compounds -- one breach compromises the system
- [[ai-safety]] - CRITICAL: credential leakage is a direct AI safety and security failure mode
- [[cisa-chatgpt-data-leak]] - institutional-scale version: sensitive data leaked into a commercial AI system
- [[lesson-21-runtime-json-pollution]] - debug print statements that pollute stdout can also leak credentials into machine-readable output
- [[ai-safety-alignment]] - credential handling is a concrete AI alignment problem: agents must not expose secrets

## Validation

**Discovered**: Feb 2026 during debugging session; credential found in CI log
**Impact**: Mandatory key rotation; security review of all log statements
**Status**: CRITICAL -- zero tolerance policy enforced across all Cohezion code
