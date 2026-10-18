#!/usr/bin/env bash
# ==============================================================================
# Cohezion ZFS Checkpoint & Rollback Utility
# Hardware: Framework Desktop (AMD Ryzen AI MAX+ 395, 128GB UMA, ZFS rpool)
# Dataset:  rpool/USERDATA/home_7r4ayl
# ==============================================================================
set -euo pipefail

DATASET="${ZFS_DATASET:-rpool/USERDATA/home_7r4ayl}"
TIMESTAMP="$(date +'%Y%m%d-%H%M%S')"

usage() {
    cat <<EOF
Usage: $0 [COMMAND] [ARGS]

Commands:
    create [tag]       Create an instant CoW snapshot with optional tag (default: timestamp)
    list [limit]       List recent Cohezion snapshots (default limit: 10)
    diff <tag>         Show filesystem changes since snapshot
    rollback <tag>     Roll back dataset to specified snapshot (Destructive! Requires CONFIRM=1)
    destroy <tag>      Destroy specified snapshot

Examples:
    $0 create pre-refactor-swarm
    $0 list
    $0 diff pre-refactor-swarm
    CONFIRM=1 $0 rollback pre-refactor-swarm
EOF
    exit 1
}

cmd="${1:-}"

case "$cmd" in
    create)
        tag="${2:-checkpoint-${TIMESTAMP}}"
        snap_name="${DATASET}@${tag}"
        echo "Creating instant ZFS snapshot: ${snap_name}..."
        sudo -n zfs snapshot "${snap_name}"
        echo "✓ Snapshot created: ${snap_name}"
        ;;
    list)
        limit="${2:-10}"
        echo "Recent snapshots on ${DATASET}:"
        sudo -n zfs list -t snapshot -o name,used,creation -s creation -r "${DATASET}" | tail -n "${limit}"
        ;;
    diff)
        tag="${2:-}"
        if [[ -z "$tag" ]]; then
            echo "Error: snapshot tag required for diff"
            usage
        fi
        snap_name="${DATASET}@${tag}"
        echo "Diffing ${snap_name} against current working state..."
        sudo -n zfs diff "${snap_name}" | head -n 40
        ;;
    rollback)
        tag="${2:-}"
        if [[ -z "$tag" ]]; then
            echo "Error: snapshot tag required for rollback"
            usage
        fi
        if [[ "${CONFIRM:-0}" != "1" ]]; then
            echo "Error: Rollback will discard all uncommitted changes since snapshot!"
            echo "To proceed, run: CONFIRM=1 $0 rollback ${tag}"
            exit 2
        fi
        snap_name="${DATASET}@${tag}"
        echo "Rolling back dataset to ${snap_name}..."
        sudo -n zfs rollback -r "${snap_name}"
        echo "✓ Rollback complete to ${snap_name}"
        ;;
    destroy)
        tag="${2:-}"
        if [[ -z "$tag" ]]; then
            echo "Error: snapshot tag required for destroy"
            usage
        fi
        snap_name="${DATASET}@${tag}"
        echo "Destroying snapshot ${snap_name}..."
        sudo -n zfs destroy "${snap_name}"
        echo "✓ Snapshot destroyed"
        ;;
    *)
        usage
        ;;
esac
