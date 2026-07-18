#!/usr/bin/env bash
# Install a cron keepalive for compound_daemon. Run from YOUR terminal
# (or `! bash scripts/ops/install_daemon_keepalive.sh` in Claude Code) —
# crontab is setuid and cannot be installed from an agent shell (no_new_privs).
#
# The keepalive checks by process name (pgrep), NOT the PID file: the daemon's
# self-reported pid is namespace-local when launched from a Claude session, so
# PID-file liveness checks lie from the host. Host pgrep sees into namespaces.
#
# It launches from the cohezion REPO so `uv run` resolves the repo venv —
# this restores the LC1 in-process LoopCoordinator path (the labs dir venv
# lacks httpx, forcing subprocess fallback).
set -euo pipefail

REPO="$HOME/dev/cohezion"
UV="$HOME/.local/bin/uv"
LINE="*/5 * * * * flock -n \$HOME/.cohezion/compound_daemon.cron.lock -c 'pgrep -f \"python.*compound_daemon.py\" >/dev/null || (cd $REPO && $UV run python \$HOME/cohezion-labs/compound_daemon.py --interval 10 >> \$HOME/.cohezion/compound_daemon.cron.log 2>&1)' # compound_daemon_keepalive"

( crontab -l 2>/dev/null | grep -v compound_daemon_keepalive ; echo "$LINE" ) | crontab -
echo "Installed:"
crontab -l | grep compound_daemon_keepalive
