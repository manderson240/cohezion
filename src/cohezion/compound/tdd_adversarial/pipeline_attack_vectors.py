"""Pipeline attack-vector library — generic adversarial probes as pure data.

Merged from the retired consortium_instigator.py (elegant-simplicity audit
2026-08-14): the probe definitions survive here as config; runners live in the
adversarial-review system, not in a parallel agent framework.

Each vector: id, description, category, severity, payload (kwargs for the
pipeline under test), expected_behavior, failure_indicators (substrings whose
presence in output/traceback indicates the pipeline broke).
"""

from __future__ import annotations

from typing import Any


_DEFAULT_TIMEOUT = 30

PIPELINE_ATTACK_VECTORS: list[dict[str, Any]] = [
    {
        "id": "empty-prompt",
        "description": "Empty prompt must raise ValueError, not crash or hang",
        "category": "input_validation",
        "severity": "critical",
        "payload": {"prompt": "", "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline raises ValueError with clear message",
        "failure_indicators": ["consortium failed", "INTERNAL ERROR", "traceback", "hanging"],
    },
    {
        "id": "whitespace-only",
        "description": "Whitespace-only prompt must raise ValueError",
        "category": "input_validation",
        "severity": "high",
        "payload": {"prompt": "   \t\n  ", "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline raises ValueError",
        "failure_indicators": ["consortium failed", "hanging"],
    },
    {
        "id": "large-prompt",
        "description": "10KB prompt must be handled without truncation",
        "category": "input_validation",
        "severity": "high",
        "payload": {"prompt": "A" * 10240, "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline processes without truncation errors",
        "failure_indicators": ["truncat", "too long", "413", "414"],
    },
    {
        "id": "concurrent-three",
        "description": "Three concurrent calls must not interfere (thread safety)",
        "category": "concurrency",
        "severity": "high",
        "payload": {"concurrent": 3, "prompt": "What is 2+2?"},
        "expected_behavior": "All three independent, no cross-contamination",
        "failure_indicators": [
            "race condition",
            "cross-contamination",
            "deadlock",
            "timeout on concurrent",
        ],
    },
    {
        "id": "lemonade-down",
        "description": "Lemonade unreachable must return clean error, not hang",
        "category": "network_failure",
        "severity": "critical",
        "payload": {
            "prompt": "What is 2+2?",
            "timeout": 5,
            "_override_url": "http://127.0.0.1:19999/v1/chat/completions",
        },
        "expected_behavior": "Returns [ERROR: URLError] for all stages, pipeline completes",
        "failure_indicators": ["hanging", "timeout without error", "crash"],
    },
    {
        "id": "tight-timeout",
        "description": "Unrealistically tight timeout must fail cleanly",
        "category": "timeout",
        "severity": "medium",
        "payload": {"prompt": "What is 2+2?", "timeout": 1},
        "expected_behavior": "Timeout error propagated, pipeline continues gracefully",
        "failure_indicators": ["unhandled timeout", "crash on timeout"],
    },
    {
        "id": "malformed-json",
        "description": "Malformed prompt must not crash parser",
        "category": "response_integrity",
        "severity": "medium",
        "payload": {"prompt": '{"broken": "json"\n\n\n\n', "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline handles special characters without crash",
        "failure_indicators": ["json decode error", "unhandled exception", "crash"],
    },
    {
        "id": "unicode-explosion",
        "description": "Unicode-heavy prompt must not corrupt pipeline",
        "category": "response_integrity",
        "severity": "low",
        "payload": {"prompt": "🔥" * 5000, "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline handles unicode without encoding errors",
        "failure_indicators": ["encode", "decode", "unicode error", "crash"],
    },
    {
        "id": "control-chars",
        "description": "Control characters must not break context propagation",
        "category": "context_corruption",
        "severity": "low",
        "payload": {"prompt": "Hello\x00World\x1b[31mRED", "timeout": _DEFAULT_TIMEOUT},
        "expected_behavior": "Pipeline sanitizes or passes through without corruption",
        "failure_indicators": ["null byte", "control character", "escape sequence"],
    },
]
