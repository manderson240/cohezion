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

MIN_AVAILABLE_GIB=25
MAX_SWAP_PCT=10
MAX_VRAM_PCT=80
MAX_GTT_GIB=50
MAX_PSI_PRESSURE=20.0
GCVM_PATTERN='GCVM_L2_PROTECTION_FAULT'

ok()  { echo "  ✓ $*"; }
err() { echo "  ✗ $*" >&2; }
info() { (( VERBOSE )) && echo "  · $*" || true; }

fail=0

# 1. Memory and Swap State (/proc/meminfo exact kB parsing)
echo "Checking memory state..."
if [[ ! -r /proc/meminfo ]]; then
  err "/proc/meminfo unreadable — cannot confirm memory state"
  fail=1
else
  avail_kb=$(grep -E "^MemAvailable:" /proc/meminfo | awk '{print $2}')
  total_kb=$(grep -E "^MemTotal:" /proc/meminfo | awk '{print $2}')
  if [[ -z "${avail_kb}" || -z "${total_kb}" ]]; then
    err "could not parse /proc/meminfo"
    fail=1
  else
    avail_gib=$((avail_kb / 1048576))
    info "available: ${avail_gib} GiB (total: $((total_kb / 1048576)) GiB)"
    if (( avail_gib < MIN_AVAILABLE_GIB )); then
      err "available memory ${avail_gib} GiB is below the ${MIN_AVAILABLE_GIB} GiB floor"
      fail=1
    else
      ok "available memory ${avail_gib} GiB >= ${MIN_AVAILABLE_GIB} GiB floor"
    fi

    swap_total_kb=$(grep -E "^SwapTotal:" /proc/meminfo | awk '{print $2}')
    swap_free_kb=$(grep -E "^SwapFree:" /proc/meminfo | awk '{print $2}')
    if [[ -n "${swap_total_kb}" && "${swap_total_kb}" -gt 0 ]]; then
      swap_used_kb=$((swap_total_kb - swap_free_kb))
      swap_pct=$(( (swap_used_kb * 100) / swap_total_kb ))
      swap_used_gib=$((swap_used_kb / 1048576))
      info "swap: used ${swap_pct}% (${swap_used_gib} GiB of $((swap_total_kb / 1048576)) GiB)"
      if (( swap_pct > MAX_SWAP_PCT )); then
        err "swap used ${swap_pct}% exceeds the ${MAX_SWAP_PCT}% threshold (${swap_used_gib} GiB used)"
        fail=1
      else
        ok "swap used ${swap_pct}% <= ${MAX_SWAP_PCT}% threshold"
      fi
    else
      ok "swap is disabled or not configured"
    fi
  fi
fi

# 2. Kernel Memory Pressure Stall Information (PSI)
echo "Checking kernel memory pressure (PSI)..."
if [[ -r /proc/pressure/memory ]]; then
  psi_some_10=$(grep -E "^some" /proc/pressure/memory | sed -E 's/.*avg10=([0-9.]+).*/\1/' || echo "0.00")
  info "memory pressure (some avg10): ${psi_some_10}"
  if (( $(echo "${psi_some_10} > ${MAX_PSI_PRESSURE}" | bc -l 2>/dev/null || echo 0) )); then
    err "memory pressure avg10=${psi_some_10} exceeds threshold ${MAX_PSI_PRESSURE} (system actively thrashing)"
    fail=1
  else
    ok "memory pressure avg10=${psi_some_10} <= ${MAX_PSI_PRESSURE}"
  fi
else
  info "/proc/pressure/memory not present; skipping PSI check"
fi

# 3. AMD GPU & GTT State (sysfs direct probe + rocm-smi fallback)
echo "Checking AMD GPU / GTT state..."
gtt_used_bytes=0
gtt_total_bytes=0
for gtt_file in /sys/class/drm/card*/device/mem_info_gtt_used; do
  if [[ -r "${gtt_file}" ]]; then
    val=$(cat "${gtt_file}" 2>/dev/null || echo "0")
    gtt_used_bytes=$((gtt_used_bytes + val))
  fi
done
for gtt_file in /sys/class/drm/card*/device/mem_info_gtt_total; do
  if [[ -r "${gtt_file}" ]]; then
    val=$(cat "${gtt_file}" 2>/dev/null || echo "0")
    gtt_total_bytes=$((gtt_total_bytes + val))
  fi
done

if (( gtt_total_bytes > 0 )); then
  gtt_used_gib=$((gtt_used_bytes / 1073741824))
  gtt_total_gib=$((gtt_total_bytes / 1073741824))
  gtt_pct=$(( (gtt_used_bytes * 100) / gtt_total_bytes ))
  info "GTT sysfs: ${gtt_used_gib} GiB used / ${gtt_total_gib} GiB total (${gtt_pct}%)"
  if (( gtt_used_gib > MAX_GTT_GIB )); then
    err "GPU GTT used ${gtt_used_gib} GiB exceeds the ${MAX_GTT_GIB} GiB ceiling (UMA aperture saturation)"
    fail=1
  else
    ok "GPU GTT used ${gtt_used_gib} GiB <= ${MAX_GTT_GIB} GiB ceiling"
  fi
elif command -v rocm-smi >/dev/null 2>&1; then
  rocm_out=$(rocm-smi --showuse 2>/dev/null || true)
  vram_pct=$(echo "${rocm_out}" | grep -oE "GPU use[[:space:]]*\(%\)[[:space:]]+[0-9.]+" | awk '{print $NF}' | head -1)
  if [[ -n "${vram_pct}" ]]; then
    info "VRAM use: ${vram_pct}%"
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
  info "Neither DRM GTT sysfs nor rocm-smi readable; skipping GPU check"
fi

# 4. dmesg (optional — only if readable)
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

# Ensure Cohezion Hermes Router Policy is pinned on Lemonade port 13305
if [ -f "src/cohezion/registry/cohezion_hermes_router_policy.json" ]; then
  curl -s -X POST http://localhost:13305/api/v1/pull -H "Content-Type: application/json" --data-binary @src/cohezion/registry/cohezion_hermes_router_policy.json > /dev/null 2>&1 || true
fi
