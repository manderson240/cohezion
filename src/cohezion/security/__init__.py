"""
Cohezion Security Package - Guardrails for safe operation.

Components:
- validators: Input validation and sanitization
- rate_limiter: Token bucket rate limiting
- auth: API key and JWT authentication
- prompt_guard: Prompt injection defense
- output_filter: PII and toxicity filtering
- audit: Structured audit logging
"""

from cohezion.security.audit import AuditLogger
from cohezion.security.auth import create_token, verify_api_key
from cohezion.security.output_filter import OutputFilter
from cohezion.security.prompt_guard import PromptGuard
from cohezion.security.rate_limiter import RateLimiter
from cohezion.security.validators import sanitize_text, validate_input

__all__ = [
    "validate_input",
    "sanitize_text",
    "RateLimiter",
    "verify_api_key",
    "create_token",
    "PromptGuard",
    "OutputFilter",
    "AuditLogger",
]
