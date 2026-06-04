#!/usr/bin/env bash
# scripts/recover_fleet.sh — recovery runbook for a zombie / OOM box.
#
# Two paths:
#   --soft (default): pkill inference procs, drop_caches, re-check.
#                     Safe to run unattended.
#   --hard: prints the cold-boot instructions and refuses to run them.
#           A human must be at the keyboard. NEVER automate the hard
#           path — soft recovery usually works; hard is a last resort.
#
# Usage:
#   bash scripts/recover_fleet.sh              # soft recovery
#   bash scripts/recover_fleet.sh --soft       # explicit soft
#   bash scripts/recover_fleet.sh --hard       # print cold-boot playbook
#   bash scripts/recover_fleet.sh --dry-run    # print plan, do nothing

set -euo pipefail

MODE="soft"
[[ "${1:-}" == "--soft" ]] && MODE="soft"
[[ "${1:-}" == "--hard" ]] && MODE="hard"
[[ "${1:-}" == "--dry-run" ]] && MODE="dry-run"

log() { echo "[recover] $*"; }

soft_recovery() {
  log "soft recovery: pkill llama-server, lemonade, ollama"
  pkill -9 -f "llama-server|lemonade|ollama" 2>/dev/null || true
  sleep 2

  log "drop_caches (needs sudo)"
  if sudo -n sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null; then
    log "drop_caches ok"
  else
    log "drop_caches failed (no sudo or kernel denied); continuing"
  fi

  log "post-recovery check"
  if command -v rocm-smi >/dev/null 2>&1; then
    rocm-smi --showuse 2>/dev/null | head -5 || true
  fi
  free -h
  echo ""
  log "If free -h shows available < 20 GiB OR rocm-smi shows VRAM use > 80% with no live process,"
  log "the soft path didn't clear the zombie state. Cold boot required (see --hard)."
}

hard_recovery() {
  cat <<'EOF'

=================================================================
  COLD BOOT RECOVERY — MANUAL STEPS
=================================================================

The soft recovery did not free the GPU/VRAM. The kernel is
holding a zombie allocation. This is a Strix Halo aperture
race recovery (see strix-halo-concurrent-model-load-oom skill).

DO NOT run this from a script. Do it at the keyboard.

  1. Save any unsaved work in OTHER terminals.
  2. Shut down cleanly:   sudo shutdown -h now
  3. WAIT 5 SECONDS with the power off (cold = VRAM zeroed).
  4. Power on.
  5. Verify with:        rocm-smi --showuse
     Expected: VRAM use 0% with no zombie state.
  6. If zombie state persists, the kernel module may need a
     full driver reload:  sudo modprobe -r amdgpu && sudo modprobe amdgpu

Then return here and re-run:
  bash scripts/preflight_fleet.sh
  bash scripts/daily_researcher.py --dry-run --skip-preflight

=================================================================
EOF
}

dry_run() {
  log "dry-run: would run --soft recovery (pkill + drop_caches + recheck)"
  log "no actions taken"
}

case "${MODE}" in
  soft)      soft_recovery ;;
  hard)      hard_recovery ;;
  dry-run)   dry_run ;;
  *)         echo "unknown mode: ${MODE}" >&2; exit 1 ;;
esac
