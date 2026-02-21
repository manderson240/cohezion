# Vault Health Report

## Summary

| Metric | Value |
|--------|-------|
| Total Files | 666 |
| Total Link Targets | 801 |
| Valid Links | 448 (55%) |
| Broken Links | 353 (44%) |
| Papers with null tags | 2 |

## Broken Links by Category

| Category | Count | Description |
|----------|-------|-------------|
| Date-prefixed | 2 | Links with YYYY-MM-DD- prefix (references to dated artifacts) |
| External references | 91 | Links to external systems/code (underscores, .py/.js files) |
| Missing concepts | 260 | Genuinely missing concept files |

## Top Broken Links (by reference count)

- `agent context` (27 references) - missing
- `mcp infrastructure architecture` (9 references) - missing
- `patterns/troubleshooting-mcp-infrastructure` (9 references) - missing
- `patterns/runbook-health-checks` (9 references) - missing
- `context management` (7 references) - missing
- `phase 1 implementation` (7 references) - missing
- `fractal_universe` (7 references) - date/external
- `compound engineering` (7 references) - missing
- `concepts/mcp-infrastructure-architecture` (6 references) - missing
- `multi agent systems` (5 references) - missing
- `lab_agent.py` (5 references) - date/external
- `decisions/2026-02-10-phase-a-implementation-complete` (5 references) - missing
- `lessons/2026-02-10-debug-log-bloat-analysis` (5 references) - missing
- `lab_agent` (4 references) - date/external
- `patterns/runbook-ollama-mcp-operations` (4 references) - missing
- `patterns/runbook-ci-cd-pipeline` (4 references) - missing
- `agentic ai` (4 references) - missing
- `fractal_universe.py` (3 references) - date/external
- `enhanced_simulator.py` (3 references) - date/external
- `decisions/2026-02-10-log-mining-adversarial-review` (3 references) - missing

## Recommendations

1. **Populate tags:** 2 papers need tags
2. **Create concept stubs:** 20 frequently-referenced concepts should get stub files
3. **Add cross-references:** Papers and concepts need Related sections populated

Run `python -m vault_linker fix` to apply automated fixes.
