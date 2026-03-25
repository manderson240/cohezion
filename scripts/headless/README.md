# Headless Mode Scripts

Run Claude Code non-interactively for autonomous workflows. Each script constrains tools
and turn count to prevent drift into unbounded exploration.

## Scripts

### `maintain.sh` — Autonomous Maintenance Cycle

```bash
./scripts/headless/maintain.sh        # Fix up to 10 issues
./scripts/headless/maintain.sh 20     # Fix up to 20 issues
```

Runs the `/maintain` skill: scans for lint errors, missing `__init__.py`, vault orphans,
and oversized files. Fixes top N issues and verifies each fix doesn't regress tests.

### `execute-plan.sh` — Plan Execution

```bash
./scripts/headless/execute-plan.sh docs/plans/2026-03-25-add-auth.md
```

Runs the `/execute` skill on a plan file. Validates preconditions, executes each task
with test gating, and commits at milestones.

## Customization

- **Turn limits**: Edit `--max-turns` in the script (default: 30 for maintain, 50 for execute)
- **Allowed tools**: Edit `--allowedTools` to restrict or expand capabilities
- **Logging**: All output goes to `~/.cohezion-engine/logs/<script>-<timestamp>.log`

## Scheduling

Run maintenance on a schedule with cron:

```bash
# Every day at 3am
0 3 * * * cd /home/mike-anderson/dev/cohezion && ./scripts/headless/maintain.sh 10
```

Or as a one-shot from the terminal:

```bash
nohup ./scripts/headless/maintain.sh 20 &
```
