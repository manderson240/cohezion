# Vault Health Report

## Summary

| Metric | Value |
|--------|-------|
| Total Files | 661 |
| Total Link Targets | 830 |
| Valid Links | 487 (58%) |
| Broken Links | 343 (41%) |
| Papers with null tags | 125 |

## Broken Links by Category

| Category | Count | Description |
|----------|-------|-------------|
| Date-prefixed | 2 | Links with YYYY-MM-DD- prefix (references to dated artifacts) |
| External references | 88 | Links to external systems/code (underscores, .py/.js files) |
| Missing concepts | 253 | Genuinely missing concept files |

## Top Broken Links (by reference count)

- `patterns/troubleshooting-mcp-infrastructure` (9 references) - missing
- `patterns/runbook-health-checks` (9 references) - missing
- `fractal_universe` (7 references) - date/external
- `concepts/mcp-infrastructure-architecture` (6 references) - missing
- `decisions/2026-02-10-phase-a-implementation-complete` (5 references) - missing
- `lab_agent.py` (5 references) - date/external
- `lessons/2026-02-10-debug-log-bloat-analysis` (5 references) - missing
- `patterns/runbook-ci-cd-pipeline` (4 references) - missing
- `lab_agent` (4 references) - date/external
- `patterns/runbook-ollama-mcp-operations` (4 references) - missing
- `fractal_universe.py` (3 references) - date/external
- `enhanced_simulator.py` (3 references) - date/external
- `decisions/2026-02-10-log-mining-adversarial-review` (3 references) - missing
- `semantic_caching_prime` (2 references) - date/external
- `adversarial_testing_prime` (2 references) - date/external
- `usage_analytics_prime` (2 references) - date/external
- `token_efficiency_prime` (2 references) - date/external
- `system_monitoring_prime` (2 references) - date/external
- `testing_prime` (2 references) - date/external
- `security_guardrails_prime` (2 references) - date/external

## Recommendations

1. **Populate tags:** 125 papers need tags
2. **Create concept stubs:** 13 frequently-referenced concepts should get stub files
3. **Add cross-references:** Papers and concepts need Related sections populated

Run `python -m vault_linker fix` to apply automated fixes.
