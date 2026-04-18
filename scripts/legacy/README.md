# Legacy scripts

Scripts that accumulated at the repo root across sessions — sim drivers, status checkers, one-off `fix_*` helpers, launch scripts for retired demos. Relocated here to declutter the root without deleting the content.

## Policy

- Nothing here is guaranteed to still work against the current codebase.
- If you need one of these, try running it; fix or resurrect as needed and potentially promote back to `scripts/` proper.
- If you write a new utility script, put it in `scripts/` (not here).

## What's here (categories, not an exhaustive list)

- **Status/health checkers**: `check_bbq_status.py`, `check_db_tables.py`, `check_leaderboard.py`, `check_ns.py`, `check_root.py`, `check_status_8001.py`
- **FLUME demos / viz**: `demo_flume_cli.sh`, `demo_flume_journey.py`, `flume_journey_cli.py`, `flume_journey_visualizer.py`, `flume_viz_simple.py`, `launch_flume_viz.sh`, `launch_simple_flume.sh`
- **Deployment/ops**: `deploy_production.sh`, `monitor_production.sh`, `start-mcp-servers.sh`, `production_scheduler.py`, `activate_omnibus.py`
- **Long-running drivers**: `mass_sim_driver.py`, `overnight_driver.py`
- **DB inspection**: `list_comps.py`, `list_tables.py`
- **Repo maintenance helpers**: `fix_all_toFixed.sh`, `fix_all_toFixed_comprehensive.sh`, `fix_tofixed_quick.sh`, `scan_todos.py`, `record_final_status.py`, `resume-session.sh`, `EXECUTE_AT_2310.sh`

## Removing safely

Deleting any of these is OK if you're confident it's unused. Verify first:

```bash
grep -r "<script-name>" scripts/ src/ Makefile .claude/ .github/
```

No hits = safe to delete. One hit in CI/Makefile = update the ref first.
