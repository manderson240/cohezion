#!/bin/bash
# Lemonade ROCm Fix for gfx1151 (Strix Halo)

# Force gfx1151 recognition
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export HSA_ENABLE_SDMA=0  # Disable SDMA if causing issues

# GPU selection
export HIP_VISIBLE_DEVICES=0
export ROCR_VISIBLE_DEVICES=0

# ROCm performance tuning for 128GB UMA
export ROCM_FORCE_HOST_MEMORY=1
export HIP_PLATFORM=amd

# Start lemonade with these settings
echo "Starting Lemonade with ROCm gfx1151 fix..."
lemond "$@"
