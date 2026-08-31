#!/bin/bash
# Demand-driven model sprint daemon — keeps the right local models resident.
#
# Polls the Lemonade :13305 catalog on a configurable interval and runs a
# role-based hotswap sprint whenever the roster changes. Uses the
# ModelSprintOrchestrator so it composes the existing hotswap + FleetRoster
# modules instead of duplicating eviction/load logic.
#
# Usage:
#   bash scripts/model_sprint_daemon.sh [interval_seconds]
#
# Environment:
#   LEMONADE_BASE_URL  - default http://localhost:13305
#   SPRINT_ROLES       - comma-separated roles, default interactive,code,reason,fast,route
#   DAEMON_INTERVAL    - default 60 seconds

set -u

LEMONADE_BASE_URL="${LEMONADE_BASE_URL:-http://localhost:13305}"
SPRINT_ROLES="${SPRINT_ROLES:-interactive,code,reason,fast,route}"
DAEMON_INTERVAL="${DAEMON_INTERVAL:-${1:-60}}"
export LEMONADE_BASE_URL SPRINT_ROLES DAEMON_INTERVAL

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure repo venv is available
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  source "$REPO_ROOT/.venv/bin/activate"
elif command -v uv >/dev/null 2>&1; then
  cd "$REPO_ROOT" && uv sync --locked >/dev/null 2>&1 || true
fi

echo "======================================================================"
echo "🛰️  Cohezion model sprint daemon"
echo "   base:    $LEMONADE_BASE_URL"
echo "   roles:   $SPRINT_ROLES"
echo "   interval: ${DAEMON_INTERVAL}s"
echo "======================================================================"

python3 - <<PYEOF
import asyncio
import os
from cohezion.inference.model_sprint_orchestrator import (
    ModelSprintOrchestrator,
    poll_model_roster_forever,
)

base_url = os.environ["LEMONADE_BASE_URL"]
interval = int(os.environ["DAEMON_INTERVAL"])

async def main():
    orchestrator = ModelSprintOrchestrator(base_url=base_url)
    # Run an initial sprint so the fleet is warm immediately.
    roles = os.environ["SPRINT_ROLES"].split(",")
    roles = [r.strip() for r in roles if r.strip()]
    initial = await orchestrator.run_sprint(roles)
    for r in initial:
        status = "✅" if r.ok else "❌"
        print(f"{status} {r.role:12} → {r.model_id or 'none'} ({r.reason})")
    # Then watch the catalog and react to changes.
    await poll_model_roster_forever(base_url=base_url, interval_s=interval)

asyncio.run(main())
PYEOF
