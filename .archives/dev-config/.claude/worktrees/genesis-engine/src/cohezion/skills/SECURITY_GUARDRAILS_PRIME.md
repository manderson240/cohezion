---
name: security-guardrails
description: AI security guardrail implementation including input validation,
  rate limiting, authentication, prompt injection defense, output filtering,
  and audit logging. Use when implementing auth flows, reviewing security
  posture, or when user mentions "security", "prompt guard", "rate limiting",
  "OWASP", "prompt injection", or "credential rotation".
metadata:
  version: "0.1"
  legacy-name: SECURITY_GUARDRAILS_PRIME
---

# SKILL: SECURITY_GUARDRAILS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **AI security guardrails** - input validation, rate limiting, authentication, prompt injection defense, output filtering, and audit logging.

## KEY CONCEPTS
- **Defense in Depth** - Multiple layers of protection
- **Principle of Least Privilege** - Minimal access by default
- **Fail Secure** - Block on error, not allow
- **OWASP LLM Top 10** - LLM-specific vulnerabilities

## INSTRUCTION

### 1. Input Validation
```python
from cohezion.security.validators import validate_input, sanitize_text

error = validate_input(user_query, max_length=10000)
if error:
    return {"error": error.message}

clean_query = sanitize_text(user_query)
```

### 2. Rate Limiting
```python
from cohezion.security.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()
result = limiter.check(ip_address, endpoint)
if not result.allowed:
    return {"error": "Rate limit exceeded", "retry_after": result.reset_after}
```

### 3. Authentication
```python
from cohezion.security.auth import verify_api_key, create_token

# API key auth
key_data = verify_api_key(api_key)  # Raises AuthError if invalid

# JWT token
token = create_token({"sub": user_id, "role": "user"})
```

### 4. Prompt Injection Defense
```python
from cohezion.security.prompt_guard import PromptGuard

guard = PromptGuard(strict_mode=True)
if guard.should_block(user_input):
    return {"error": "Input rejected for safety"}
```

### 5. Output Filtering
```python
from cohezion.security.output_filter import OutputFilter

filter = OutputFilter(redact_pii=True, block_toxic=True)
result = filter.filter(llm_output)
if result.warnings:
    log.warning(result.warnings)
return result.content
```

### 6. Audit Logging
```python
from cohezion.security.audit import get_audit_logger

audit = get_audit_logger()
audit.log_request(endpoint, method, ip, user, status, latency)
audit.log_security("blocked_injection", "malicious", ip, {...})
```

## SECURITY FLOW
```
Request → Rate Limit → Auth → Validate → Prompt Guard → LLM → Output Filter → Audit → Response
```

## CITATIONS
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

## VERSION
v0.1

## SEE ALSO
- MCP_SERVER_PRIME.md
- SELF_HEALING_PRIME.md
