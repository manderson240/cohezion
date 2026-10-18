#!/usr/bin/env bash
# ==============================================================================
# Cohezion Sovereign Storage Hygiene & Tiering Engine
# ------------------------------------------------------------------------------
# Automates first-principles storage auditing, tiering policy enforcement,
# ZFS ARC/dataset inspection, and deterministic reclamation of legacy assets.
#
# Usage:
#   bash scripts/ops/storage_hygiene.sh audit         # Full storage audit
#   bash scripts/ops/storage_hygiene.sh plan          # Show reclaimable candidates
#   bash scripts/ops/storage_hygiene.sh reclaim-safe  # Safely clear temp & runner caches
#   bash scripts/ops/storage_hygiene.sh reclaim-models# Prune legacy GGUFs violating NPU policy
# ==============================================================================

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

CMD="${1:-audit}"

audit_storage() {
    echo -e "${BOLD}${CYAN}=== [1/4] ZFS Pool & Dataset Utilization ===${NC}"
    zfs list -o name,used,avail,refer,compressratio,recordsize rpool rpool/USERDATA/home_7r4ayl rpool/ROOT/ubuntu_c3mvhb/var/lib rpool/swap_cohezion 2>/dev/null || true
    echo ""

    echo -e "${BOLD}${CYAN}=== [2/4] ZFS ARC Memory Sizing in RAM ===${NC}"
    if [ -f /proc/spl/kstat/zfs/arcstats ]; then
        awk '/^size/ {printf "  Current ARC Size: %.2f GB\n", $3/1024/1024/1024} /^c_max/ {printf "  Max ARC (c_max):   %.2f GB\n", $3/1024/1024/1024}' /proc/spl/kstat/zfs/arcstats
    else
        echo "  ZFS arcstats not available."
    fi
    echo ""

    echo -e "${BOLD}${CYAN}=== [3/4] High-Density Storage Consumers ===${NC}"
    echo "  Checking major consumer directories..."
    [ -d /var/lib/lemonade/.cache/huggingface ] && sudo -n du -sh /var/lib/lemonade/.cache/huggingface 2>/dev/null | awk '{print "  Lemonade HF Models:    " $1}' || true
    [ -d /var/lib/docker ] && sudo -n du -sh /var/lib/docker 2>/dev/null | awk '{print "  Docker Storage:        " $1}' || true
    [ -d /home/mike-anderson/gh-runner/_work ] && du -sh /home/mike-anderson/gh-runner/_work 2>/dev/null | awk '{print "  GH Runner Workspace:   " $1}' || true
    [ -d /home/mike-anderson/cohezion-labs ] && du -sh /home/mike-anderson/cohezion-labs 2>/dev/null | awk '{print "  Cohezion Labs Builds:  " $1}' || true
    [ -d /home/mike-anderson/.gemini ] && du -sh /home/mike-anderson/.gemini 2>/dev/null | awk '{print "  Gemini CLI Cache:      " $1}' || true
    [ -d /home/mike-anderson/.cache ] && du -sh /home/mike-anderson/.cache 2>/dev/null | awk '{print "  User Pip/UV Cache:     " $1}' || true
    [ -d /dev/shm ] && df -h /dev/shm | awk 'NR==2 {print "  Shared Memory (SHM):   " $3 " used / " $2 " total (" $5 ")"}'
    echo ""

    echo -e "${BOLD}${CYAN}=== [4/4] ZFS Snapshots Retention Status ===${NC}"
    local snap_count
    snap_count=$(zfs list -t snapshot -H -o name 2>/dev/null | wc -l)
    echo "  Total Active Snapshots: $snap_count"
    zfs list -t snapshot -o name,used,refer -s creation rpool/USERDATA/home_7r4ayl 2>/dev/null | tail -n 5 || true
    echo ""
}

plan_reclamation() {
    echo -e "${BOLD}${YELLOW}=== Reclamation Plan & Candidates ===${NC}"
    echo "1. Legacy GGUF Models (violating 2026-10-06 NPU-only policy):"
    echo "   Location: /var/lib/lemonade/.cache/huggingface/hub"
    echo "   Candidate weights: Mistral-Medium-128B, LMX-Omni-52B, gemma-4-31B, Qwen3.6-35B, FLUX.2"
    echo "   Estimated Reclaimable Space: ~350+ GB"
    echo ""
    echo "2. GitHub Runner Workspace Artifacts:"
    echo "   Location: /home/mike-anderson/gh-runner/_work"
    echo "   Estimated Reclaimable Space: ~25-29 GB"
    echo ""
    echo "3. Stale Docker Image & Builder Layers:"
    echo "   Estimated Reclaimable Space: ~15-30 GB"
    echo ""
    echo "4. User Build & Package Caches (~/.cache/pip, uv, wheels):"
    echo "   Estimated Reclaimable Space: ~5-10 GB"
    echo ""
    echo -e "${GREEN}Total Potential Reclaimable Space: > 400 GB!${NC}"
}

reclaim_safe() {
    echo -e "${BOLD}${CYAN}Cleaning transient user build caches...${NC}"
    rm -rf /home/mike-anderson/.cache/pip /home/mike-anderson/.cache/uv /home/mike-anderson/.cache/pytest_cache 2>/dev/null || true
    echo "✓ Cleaned user pip/uv/pytest caches."

    if [ -d /home/mike-anderson/gh-runner/_work ]; then
        echo "Pruning GH runner work artifacts older than 7 days..."
        find /home/mike-anderson/gh-runner/_work -mindepth 2 -maxdepth 2 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
        echo "✓ GH runner work artifacts pruned."
    fi

    if command -v docker >/dev/null 2>&1; then
        echo "Pruning dangling docker builder cache..."
        docker builder prune -f --filter "until=168h" 2>/dev/null || true
        echo "✓ Docker builder cache pruned."
    fi
    echo -e "${BOLD}${GREEN}Safe reclamation complete!${NC}"
}

case "$CMD" in
    audit)
        audit_storage
        ;;
    plan)
        plan_reclamation
        ;;
    reclaim-safe)
        reclaim_safe
        ;;
    reclaim-models)
        echo -e "${BOLD}${YELLOW}To prune legacy GGUF models that violate Tier 1 NPU policy, run:${NC}"
        echo "  sudo rm -rf /var/lib/lemonade/.cache/huggingface/hub/models--gghfez--Mistral-Medium-3.5-128B-IQ4_KT-GGUF"
        echo "  sudo rm -rf /var/lib/lemonade/.cache/huggingface/hub/models--lemonade-sdk--LMX-Omni-52B-Halo"
        echo "  sudo rm -rf /var/lib/lemonade/.cache/huggingface/hub/models--unsloth--gemma-4-*-GGUF.disabled"
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Usage: $0 {audit|plan|reclaim-safe|reclaim-models}"
        exit 1
        ;;
esac
