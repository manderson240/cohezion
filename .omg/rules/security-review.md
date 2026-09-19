---
description: "Security and credentials guardrails for auth surfaces and endpoints"
globs: ["**/*auth*", "**/*cred*", "**/*secret*", "**/*key*"]
alwaysApply: false
---

# Rule: Security & Credential Review

## Triggers
- Touched authentication logic, API keys, HTTP request headers, or secrets.

## Enforced Behavior
1. **No Hardcoded Production Secrets**: Production API keys and sensitive tokens must never be written into tracked source files.
2. **Local Development Resilience**: Local development against SurrealDB port 8001 may use default local credentials (`root:root`) via safe fallbacks, but never expose external keys.
3. **URL Scheme Validation**: Always validate URL schemes (`http://`, `https://`) on `urllib.request` calls to prevent arbitrary file or protocol injection (Bandit S310 compliance).
