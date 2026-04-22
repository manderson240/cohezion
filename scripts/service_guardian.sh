#!/usr/bin/env bash
# Cohezion Service Guardian — self-healing remediator for cohezion systemd services.
#
# Called every ~2 minutes by cohezion-guardian.timer (user scope). Runs as a
# systemd Type=oneshot service so it exits quickly and doesn't accumulate state.
#
# Idempotent: running 100x in a row produces the same end state.
# Silent on happy path: only logs when remediation is actually applied.
# Non-destructive: never deletes user data, git state, or unit files.
#
# Remediations:
#   (1) Recreate /tmp/surrealdb if tmpfs wiped it on boot.
#   (2) Reset failed-state counters on known cohezion services so a single
#       flake doesn't exhaust StartLimitBurst and permanently block restart.
#
# Restored 2026-04-21 after the original copy was lost in commit 9dfb5a4ef
# ("archaeology: Final phase"). The crash-loop incident that prompted the
# rebuild is documented in ~/.claude/plans/do-we-have-turbo-distributed-torvalds.md.

set -u

readonly LOG_TAG="cohezion-guardian"
log() { logger -t "${LOG_TAG}" -- "$*"; }

# Remediation 1: transient runtime directory that tmpfs wipes on every boot.
# SurrealDB's --temporary-directory arg points here and fails hard on startup
# if the directory is missing.
if [[ ! -d /tmp/surrealdb ]]; then
    mkdir -p /tmp/surrealdb && log "created /tmp/surrealdb (tmpfs wipe)"
fi

# Remediation 2: reset failed-state counters. StartLimitBurst=5 in 60s means
# a single burst of transient failures (e.g. from a dependency briefly dying)
# locks a service out until a human intervenes. Resetting here lets systemd
# retry on the next demand trigger.
readonly SERVICES=(
    "surrealdb.service"
    "cohezion-vault.service"
    "cohezion-vault-sync.service"
    "cohezion-compound.service"
    "overture-proxy.service"
)

for svc in "${SERVICES[@]}"; do
    systemctl --user cat "${svc}" >/dev/null 2>&1 || continue
    state="$(systemctl --user is-failed "${svc}" 2>/dev/null || true)"
    if [[ "${state}" == "failed" ]]; then
        log "${svc} in failed state — resetting restart counter"
        systemctl --user reset-failed "${svc}" 2>/dev/null || true
    fi
done

exit 0
