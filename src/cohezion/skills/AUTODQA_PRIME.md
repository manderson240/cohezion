---
name: autodqa
description: "AUTODQA — Automated Design Quality Assurance for Cohezion compound engineering. Self-referential QA system that dogfoods the full inference stack: task_classifier routes to NPU/iGPU/CPU, quality_eval evaluates outputs with HIHO gate (score≥0.45), security_spec blocks injection/credentials, AUTODQA.fractal_health() monitors Higuchi FD (target 1.4-1.6 = HIHO equilibrium). SurrealDB persistence, Telegram notifications via Cohezion bot."
category: compound_engineering
tags: [autodqa, quality, hiho, security, fractal, surrealdb, telegram, local-inference]
metadata:
  version: "1.0.0"
  see_also: ["local-inference-routing", "STEALTHSKATER_CORPUS"]
  modules:
    - "cohezion.compound.autodqa"
    - "cohezion.inference.quality_eval"
    - "cohezion.inference.security_spec"
    - "cohezion.inference.fractal_metrics"
    - "cohezion.compound.telegram_notify"
  hiho_threshold: 0.5
  hiho_band: [0.45, 0.55]
---

# SKILL: AUTODQA_PRIME

## DOMAIN EXPERTISE

You are the AUTODQA specialist — Cohezion's self-referential quality assurance system. You evaluate compound loop outputs using the same local AMD silicon that generates them, at zero cloud cost.

AUTODQA does NOT exist anywhere else. Great Expectations, Soda, dbt tests are all static rule-based DQA. AUTODQA is inference-powered and self-improving.

## WHAT AUTODQA EVALUATES

For every compound loop output, AutoDQA runs:

1. **Security gates** (mandatory, first): prompt injection, credential leak, SurrealQL injection
2. **Type-specific quality gate**: categorical/code/generation/bbq_low_slow
3. **HIHO quality threshold**: score ≥ 0.45 to accept (HIHO band floor)
4. **Fractal health check**: Higuchi FD of quality series (target 1.4–1.6 = healthy)

## USAGE

```python
from cohezion.compound.autodqa import AutoDQA

dqa = AutoDQA(persist=True, notify_on_reject=True)

# Evaluate a single output
result = dqa.evaluate(output_text, task_description)
print(result.verdict.accept, result.quality_band, result.tier_used)

# Session health report
health = dqa.fractal_health()
print(health["fd"], health["interpretation"])

# Send daily digest via Telegram
dqa.daily_digest()
```

## HIHO QUALITY GATE MAPPING

The stealthskater physics becomes the quality theory:

| Score | Quality Band | Action |
|-------|-------------|--------|
| < 0.45 | BELOW_HIHO | Reject → escalate tier → Telegram alert |
| 0.45–0.55 | HIHO_EQUILIBRIUM | Accept with observation logged |
| > 0.55 | ABOVE_HIHO | High confidence accept |

Same 4x(1-x) kernel as LENR/IonicCluster/BEC/MHD.

## FRACTAL HEALTH

```python
health = dqa.fractal_health()
# Returns:
# fd: Higuchi fractal dimension of quality time series
# hiho_engaged: True if FD in [1.3, 1.7] AND mean_score near 0.5
# feynman_dominant_tier: 'npu', 'igpu', 'cpu', or 'cloud'
# interpretation: 'HIHO equilibrium. Healthy...' or warning
```

FD thresholds:
- FD < 1.2: System stuck — over-exploiting (lower quality gates)
- FD 1.3–1.7: HIHO equilibrium (healthy exploration/exploitation)
- FD > 1.8: Chaotic — tighten quality gates

## SECURITY GATES (AUTO-APPLIED)

All outputs pass through `security_spec` before quality evaluation:
- `check_prompt_injection(output)` — blocks "ignore previous instructions" etc.
- `check_credential_leak(output)` — blocks API keys, tokens, passwords
- `sanitize_for_surreal(output)` — blocks SurrealQL injection before DB write
- Telegram messages auto-redacted via `redact_credentials()`

## SURREALDB PERSISTENCE

Every evaluation persisted to `autodqa_results` table (bi-temporal):
```
task_id, task_description, output_type, score, accept, reason,
quality_band, tier_used, valid_from, valid_to (None=current)
```

Query recent quality history:
```sql
SELECT * FROM autodqa_results WHERE valid_to IS NONE ORDER BY valid_from DESC LIMIT 20;
```

## TELEGRAM NOTIFICATIONS

Configure once in environment:
```bash
export TELEGRAM_BOT_TOKEN=<from Hermes config>
export TELEGRAM_CHAT_ID=<your chat ID>
```

AutoDQA sends:
- On reject: `notify_compound_error(task, reason)`
- Daily digest: `dqa.daily_digest()` → quality report with FD + accept rate
- Telegram messages auto-redact credentials before transmission

## HARNESS INVARIANTS

Run after any change to quality pipeline:
```bash
uv run python -c "from cohezion.inference.security_spec import verify_all; verify_all()"  # I7
uv run pytest tests/unit/compound/test_autodqa.py -q  # I5 + 15 tests
```
