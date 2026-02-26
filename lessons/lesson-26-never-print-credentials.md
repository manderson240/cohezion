---
title: Never Print Credentials: API Keys and Tokens Must Never Appear in Logs
date: 2026-02-23
severity: CRITICAL
category: security
tags: [security, credentials, logging, api-keys]
status: validated
---

# Lesson: Never Print Credentials: API Keys and Tokens Must Never Appear in Logs

## Context

API keys, bearer tokens, and connection strings were logged in debug output during development, causing credentials to appear in log files and CI output.

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
- [[cisa-chatgpt-data-leak]] - The CISA incident is the institutional-scale version of this lesson: sensitive data leaked into a commercial AI system via a human decision point, exactly as credentials leak into logs via a developer print statement

## Validation

**Status**: CRITICAL -- zero tolerance policy enforced across all Cohezion code
