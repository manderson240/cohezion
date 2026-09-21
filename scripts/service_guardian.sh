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

# Remediation 2: reset failed-state counters, but only after the FAILED state has been
# visible for a while. A start limit exists to turn a crash loop into a visible FAILED;
# resetting it every 2 minutes (the old behaviour) erased that signal, which is how a
# 43-restart loop went unnoticed on 2026-09-21. After 30 min FAILED we still reset, so a
# one-off burst from a briefly-dead dependency does not lock a service out forever.
# cohezion-compound.service was removed: it is a stdio MCP server, not a daemon.
readonly SERVICES=(
    "surrealdb.service"
    "cohezion-vault.service"
    "cohezion-vault-sync.service"
    "overture-proxy.service"
)
readonly FAILED_VISIBLE_US=1800000000 # 30 min

for svc in "${SERVICES[@]}"; do
    systemctl --user cat "${svc}" >/dev/null 2>&1 || continue
    state="$(systemctl --user is-failed "${svc}" 2>/dev/null || true)"
    if [[ "${state}" == "failed" ]]; then
        since="$(systemctl --user show -p InactiveEnterTimestampMonotonic --value "${svc}" 2>/dev/null)"
        now="$(awk '{printf "%d", $1 * 1000000}' /proc/uptime)"
        if [[ "${since}" =~ ^[0-9]+$ ]] && (( since > 0 && now - since < FAILED_VISIBLE_US )); then
            log "${svc} FAILED — leaving visible (start limit tripped; reset after 30 min)"
        else
            log "${svc} FAILED >30min (or age unknown) — resetting restart counter"
            systemctl --user reset-failed "${svc}" 2>/dev/null || true
        fi
    fi
done

exit 0
