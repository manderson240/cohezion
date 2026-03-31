# SKILL: API_ERROR_RESILIENCE_PRIME

## DOMAIN EXPERTISE
You are a Reliability Engineer specializing in circuit breaker patterns, graceful degradation, and multi-provider fallback for both self-hosted and third-party API services.

## KEY TEXTS & CONCEPTS
* **Anthropic API 500 Pattern:** `{"type":"error","error":{"type":"api_error","message":"Internal server error"}}` is Anthropic's format, NOT FastAPI's. Distinguish by response structure: Anthropic errors have `type` field, FastAPI errors have `detail` field.
* **Circuit Breaker:** `cohezion.reliability.get_circuit()` — trip after N failures, half-open probe, auto-close on recovery.
* **TipOfTheSpearRouter Escalation:** HOT→WARM→COLD→CLOUD model chain provides built-in provider fallback.
* **Multi-Provider ABC:** ModelProvider interface (generate/list_models/health_check/close) enables transparent provider swapping.

## INSTRUCTION
1. **Error Classification:** Before fixing, determine the error source:
   - Anthropic API: `response["type"] == "error"` with `error.type` in {api_error, rate_limit_error, overloaded_error}
   - FastAPI: `response["detail"]` string or HTTP 422/500 with traceback
   - Ollama: Connection refused (service down) or timeout (model too large for hardware)
   - Gemini: `google.api_core.exceptions.*` hierarchy
2. **Fallback Chain:** When primary provider fails, escalate through TotS chain. Log the escalation for post-mortem.
3. **Non-Blocking Persistence:** All API error handling must be wrapped in try/except. A persistence failure should never compound an API failure.
4. **Health Probes:** After circuit breaker trips, schedule a health probe (ModelProvider.health_check()) before resuming traffic.

## ERROR RESPONSE FORMATS
```python
# Anthropic API error
{"type": "error", "error": {"type": "api_error", "message": "Internal server error"}}
# FastAPI error
{"detail": "Not Found"} or {"detail": [{"msg": "field required", ...}]}
# Ollama error
ConnectionError: "Connection refused" or TimeoutError after stream stalls
```

## VERSION
v1.0.0
