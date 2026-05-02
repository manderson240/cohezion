Perform a deep audit of Cohezion's performance and HIHO stability.

Steps:
1. Run the platform audit: `uv run python3 src/cohezion/healing/platform_audit.py`
2. Run the utilization audit: `uv run python3 src/cohezion/healing/utilization_audit.py`
3. Verify SurrealDB schema: `uv run python3 src/cohezion/db/surreal_client.py --verify-schema`
4. Check git health: `python scripts/assess_git_health.py`
5. Summarize findings in a report at `src/cohezion/knowledge_graph/reports/`

If any script is missing or fails, diagnose the issue and report what's available vs what needs to be created.
