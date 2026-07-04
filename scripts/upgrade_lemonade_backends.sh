#!/usr/bin/env bash
# Upgrade lemonade to 10.7.0 and fix ROCm library path.
# Run as: sudo bash scripts/upgrade_lemonade_backends.sh
#
# What this does:
#   1. Upgrade lemonade-server 10.6.0 → 10.7.0 (brings newer llamacpp/vulkan/rocm bins)
#   2. Add LD_LIBRARY_PATH drop-in so lemond finds libhipblas.so.3 / librocblas.so.5
#      (those live in Ollama's ROCm install at /usr/local/lib/ollama/rocm_v7_2/)
#   3. Restart lemond and verify backends
#
# Current state (pre-upgrade):
#   llamacpp cpu:    internal build 8940  (lemonade b9253)
#   llamacpp vulkan: internal build 8668  (lemonade b9253)
#   llamacpp rocm:   broken — libhipblas.so.3 + librocblas.so.5 not found
#   Available:       llama.cpp b9672 (2026-06-16) via lemonade 10.7.0

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root: sudo bash $0" >&2
    exit 1
fi

echo "=== Step 1: Upgrade lemonade-server 10.6.0 → 10.7.0 ==="
apt-get update -qq
apt-get install -y lemonade-server
echo "Installed: $(dpkg -l lemonade-server | awk '/^ii/{print $3}')"

echo ""
echo "=== Step 2: Add ROCm library path drop-in ==="
ROCM_LIBS="/usr/local/lib/ollama/rocm_v7_2"
CONF_FILE="/etc/lemonade/conf.d/zz-rocm-libs.conf"

if [[ -d "$ROCM_LIBS" ]]; then
    cat > "$CONF_FILE" <<EOF
# Point lemond's ROCm llamacpp backend to Ollama's ROCm libs.
# Provides libhipblas.so.3 and librocblas.so.5 (missing from system).
LD_LIBRARY_PATH=${ROCM_LIBS}:\${LD_LIBRARY_PATH:-}
EOF
    echo "Wrote $CONF_FILE"
else
    echo "WARNING: $ROCM_LIBS not found — skipping ROCm lib drop-in"
fi

echo ""
echo "=== Step 3: Restart lemond ==="
systemctl restart lemond
sleep 3
systemctl is-active lemond && echo "lemond running" || echo "WARNING: lemond not active"

echo ""
echo "=== Step 4: Verify backends ==="
lemonade backends 2>/dev/null || echo "(run 'lemonade backends' manually to verify)"

echo ""
echo "=== Step 5: Verify OmniRouter health ==="
sleep 2
curl -s http://localhost:13305/v1/health 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['model_name'], '->', m['device']) for m in d.get('all_models_loaded', [])]" 2>/dev/null || \
    echo "(no models loaded yet — run 'lemonade load <model>' to pre-warm)"

echo ""
echo "Done. Run the agentic loop with:"
echo "  uv run python scripts/run_agentic_loop.py --dry-run"
