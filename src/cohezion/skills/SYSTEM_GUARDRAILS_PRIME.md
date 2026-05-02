---
name: system-guardrails-prime
description: "Unified guardrail framework protecting all LLM inference operations with composable pipeline orchestration."
metadata:
  version: "1.0"
  source: "src/cohezion/skills/SYSTEM_GUARDRAILS_PRIME.md"
---

# PRIME Skill: System Guardrails

## Purpose
Unified guardrail framework protecting all LLM inference operations with composable pipeline orchestration.

## Instructions

### 1. CONSTITUTIONAL_CHECK
Verify alignment with system ethics and constitution.

**Input**: User request, system context
**Process**:
  - Check request size (block if >100KB)
  - Verify semantic alignment
  - Apply sanitization if needed

**Output**: ALLOW, BLOCK, or SANITIZE decision

### 2. INJECTION_CHECK
Detect prompt injection and manipulation attacks.

**Input**: User prompt
**Process**:
  - Pattern matching for common injections
  - Heuristic scoring
  - Cross-reference against vault attack database

**Output**: ALLOW or BLOCK decision

### 3. RESOURCE_CHECK
Verify system capacity and resource availability.

**Input**: Request size, current load
**Process**:
  - Check concurrency limits
  - Monitor memory utilization
  - Verify CPU capacity
  - Enforce per-agent quotas

**Output**: ALLOW or BLOCK decision

### 4. RATE_CHECK
Enforce quotas and rate limiting.

**Input**: Agent ID, time window
**Process**:
  - Token bucket algorithm
  - Per-agent request counting
  - Time-window enforcement
  - Quota management

**Output**: ALLOW or BLOCK decision

### 5. OUTPUT_FILTER
Validate response safety before returning to user.

**Input**: Model output
**Process**:
  - Content safety filtering
  - Harmful pattern detection
  - PII redaction preparation
  - Compliance validation

**Output**: ALLOW or BLOCK decision

### 6. AUDIT
Log all guardrail actions to vault for observability.

**Input**: Guard name, action, reason, context
**Process**:
  - Non-blocking persistence to vault
  - Fallback to local JSONL if vault unavailable
  - Statistical aggregation
  - Alert on anomalies

**Output**: Audit record persisted

## Success Criteria
- All malicious inputs blocked (0 false negatives)
- False positive rate <1% on benign requests
- Latency overhead <50ms per check
- 100% audit coverage for all blocks
- Fail-open on guard exceptions (unless strict mode)
- Graceful degradation if vault unavailable

## Implementation Details

### Pipeline Orchestration
Guards execute in sequence with short-circuit on BLOCK:
```
Constitutional → Injection → Resource → Rate → Output
```

### Atomic Operations
Each guard must:
- Complete within 10ms
- Return GuardrailResult with action and metadata
- Support both sync and async execution
- Log exceptions without breaking pipeline

### Fail Modes
- Fail-open (default): Log exception, continue to next guard
- Fail-closed (strict mode): Block request on any exception

## Version: 1.0.0
## Keywords: security, validation, injection, rate-limit, safety
## Domain: system-infrastructure
## Dependencies: None (self-contained)
