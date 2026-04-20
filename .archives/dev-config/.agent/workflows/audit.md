---
description: Perform a deep audit of Cohezion's performance and HIHO stability.
---

1. Run the platform audit script.
// turbo
run_command(CommandLine="python3 src/cohezion/healing/platform_audit.py", Cwd="/home/mike-anderson/dev/cohezion/")

2. Run the utilization audit.
// turbo
run_command(CommandLine="python3 src/cohezion/healing/utilization_audit.py", Cwd="/home/mike-anderson/dev/cohezion/")

3. Check SurrealDB persistence status.
// turbo
run_command(CommandLine="python3 src/cohezion/db/surreal_client.py --verify-schema", Cwd="/home/mike-anderson/dev/cohezion/")

4. Summarize findings in `src/cohezion/knowledge_graph/reports/AUDIT_$(date +%Y%m%d_%H%M).md`.
