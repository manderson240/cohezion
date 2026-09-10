#!/usr/bin/env bash
# Auto-submit ARC-AGI-2 kernel after daily quota reset
set -euo pipefail

KAGGLE_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.kaggle/kaggle.json'))['key'])")

submit_version() {
    local VER=$1
    echo "[$(date -u)] Submitting ARC-AGI-2 kernel v${VER}..."
    RESPONSE=$(curl -s -X POST "https://api.kaggle.com/v1/competitions.CompetitionApiService/CreateCodeSubmission" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $KAGGLE_KEY" \
      -d "{
        \"competitionName\": \"arc-prize-2026-arc-agi-2\",
        \"kernelOwner\": \"manderson240\",
        \"kernelSlug\": \"arc-agi-2-fork-lb33-89-20260903\",
        \"versionNumber\": ${VER},
        \"fileName\": \"submission.json\",
        \"submissionDescription\": \"Cohezion AutoHarness Invariants + Qwen3-4B LoRA L4 v${VER}\"
      }")

    echo "Response: $RESPONSE"
    if echo "$RESPONSE" | grep -q '"ref"'; then
        echo "✅ v${VER} submission successful!"
        return 0
    else
        echo "❌ v${VER} submission failed."
        return 1
    fi
}

# Try v4 first (public kernel), then v2 as fallback
submit_version 4 || submit_version 2 || echo "Both versions failed. Manual intervention needed."
