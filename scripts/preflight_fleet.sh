#!/usr/bin/env bash
# scripts/preflight_fleet.sh — read-only safety check for local inference swarms.
#
# Refuses to start a swarm if the box shows signs of OOM, zombie VRAM,
# or kernel-level GPU faults. Exits 0 (SAFE) or 1 (NOT SAFE) with
# reasons on stderr.
#
# Usage:
#   bash scripts/preflight_fleet.sh
#   bash scripts/preflight_fleet.sh --verbose    # also print OK status
#
# Checks (per the WS1 PreflightFleetCheck class):
#   1. free -h: available memory >= 20 GiB
#   2. free -h: swap used < 10%
#   3. rocm-smi (if present): VRAM use < 80% (zombie state guard)
#   4. dmesg (if readable): no GCVM_L2_PROTECTION_FAULT in last 15 min

set -euo pipefail

VERBOSE=0
[[ "${1:-}" == "--verbose" ]] && VERBOSE=1

MIN_AVAILABLE_GIB=20
MAX_SWAP_PCT=10
MAX_VRAM_PCT=80
GCVM_PATTERN='GCVM_L2_PROTECTION_FAULT'

ok()  { echo "  ✓ $*"; }
err() { echo "  ✗ $*" >&2; }
info() { (( VERBOSE )) && echo "  · $*"; }

fail=0

# 1. free -h
echo "Checking memory state..."
if ! command -v free >/dev/null 2>&1; then
  err "free(1) unavailable — cannot confirm memory state"
  fail=1
else
  mem_line=$(free -h | grep -E "^Mem:")
  if [[ -z "${mem_line}" ]]; then
    err "could not parse 'free' output"
    fail=1
  else
    avail=$(echo "${mem_line}" | awk '{print $7}')
    info "available: ${avail}"
    avail_gib=$(echo "${avail}" | numfmt --from=iec --to=none 2>/dev/null || echo "0")
    if (( $(echo "${avail_gib} < ${MIN_AVAILABLE_GIB}" | bc -l 2>/dev/null || echo 1) )); then
      err "available memory ${avail} is below the ${MIN_AVAILABLE_GIB} GiB floor"
      fail=1
    else
      ok "available memory ${avail} >= ${MIN_AVAILABLE_GIB} GiB"
    fi

    swap_line=$(free -h | grep -E "^Swap:")
    if [[ -n "${swap_line}" ]]; then
      swap_total=$(echo "${swap_line}" | awk '{print $2}')
      swap_used=$(echo "${swap_line}" | awk '{print $3}')
      info "swap: used ${swap_used} of ${swap_total}"
      # If swap_total is 0, this is a non-issue
      total_bytes=$(echo "${swap_total}" | numfmt --from=iec --to=none 2>/dev/null || echo "0")
      used_bytes=$(echo "${swap_used}" | numfmt --from=iec --to=none 2>/dev/null || echo "0")
      if (( total_bytes > 0 )); then
        pct=$(awk "BEGIN { printf \"%.0f\", (${used_bytes}/${total_bytes})*100 }")
        if (( pct > MAX_SWAP_PCT )); then
          err "swap used ${pct}% exceeds the ${MAX_SWAP_PCT}% threshold"
          fail=1
        else
          ok "swap used ${pct}% <= ${MAX_SWAP_PCT}%"
        fi
      fi
    fi
  fi
fi

# 2. rocm-smi (optional — only if the binary exists)
echo "Checking AMD GPU state..."
if command -v rocm-smi >/dev/null 2>&1; then
  rocm_out=$(rocm-smi --showuse 2>/dev/null || true)
  vram_pct=$(echo "${rocm_out}" | grep -oE "GPU use[[:space:]]*\(%\)[[:space:]]+[0-9.]+" | awk '{print $NF}' | head -1)
  if [[ -n "${vram_pct}" ]]; then
    info "VRAM use: ${vram_pct}%"
    # Compare integers
    vram_int=${vram_pct%.*}
    if (( vram_int > MAX_VRAM_PCT )); then
      err "VRAM use ${vram_pct}% exceeds the ${MAX_VRAM_PCT}% threshold (zombie state?)"
      fail=1
    else
      ok "VRAM use ${vram_pct}% <= ${MAX_VRAM_PCT}%"
    fi
  else
    info "rocm-smi present but no GPU use line found; skipping"
  fi
else
  info "rocm-smi not on PATH; skipping GPU check"
fi

# 3. dmesg (optional — only if readable)
echo "Checking kernel ring buffer..."
if dmesg --since="-15min" >/dev/null 2>&1; then
  if dmesg --since="-15min" 2>/dev/null | grep -q "${GCVM_PATTERN}"; then
    err "GCVM_L2_PROTECTION_FAULT seen in dmesg within the last 15 minutes — kernel is unhappy"
    fail=1
  else
    ok "no GCVM faults in last 15 min"
  fi
else
  info "dmesg unreadable (likely needs sudo); skipping kernel check"
fi

if (( fail == 0 )); then
  echo ""
  echo "✅ SAFE TO START SWARM"
  exit 0
else
  echo ""
  echo "❌ NOT SAFE — see reasons above. Recovery: bash scripts/recover_fleet.sh"
  exit 1
fi
