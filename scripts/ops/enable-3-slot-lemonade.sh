#!/bin/bash
# Enable 3-slot Lemonade architecture (NPU + GPU + CPU concurrent)
# Run ONLY when Pi agent is not actively using Lemonade server
#
# Pre-check: curl -s http://localhost:13307/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin))"
# If Pi has a model loaded, wait for it to finish.

set -euo pipefail

CONFIG="vendor/lemonade/config.json"

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: $CONFIG not found. Run from repo root."
    exit 1
fi

echo "Current max_loaded_models: $(python3 -c "import json; print(json.load(open('$CONFIG'))['max_loaded_models'])")"

# Check if any models are currently loaded
MODELS=$(curl -sf http://localhost:13307/v1/models 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
echo "Currently loaded models: $MODELS"

if [ "$MODELS" -gt 0 ]; then
    echo "WARNING: $MODELS model(s) currently loaded. Ensure Pi agent is idle before proceeding."
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Apply change
python3 -c "
import json
with open('$CONFIG') as f:
    d = json.load(f)
d['max_loaded_models'] = 3
with open('$CONFIG', 'w') as f:
    json.dump(d, f, indent=2)
print('Updated max_loaded_models: 1 -> 3')
"

echo "Done. Restart Lemonade server to apply: systemctl --user restart lemonade.service"
