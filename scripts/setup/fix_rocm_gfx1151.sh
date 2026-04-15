#!/bin/bash
# Fix ROCm gfx1151 hang on Strix Halo (Ryzen AI MAX+ 395)
# Issue: amdgpu-dkms incompatible with kernel 6.17

set -e

echo "=== ROCm gfx1151 Fix Script ==="
echo ""

echo "Step 1: Removing DKMS kernel modules..."
sudo apt remove -y amdgpu-dkms amdgpu-dkms-firmware
echo "✓ DKMS removed"
echo ""

echo "Step 2: Installing ROCm WITHOUT DKMS..."
# Make sure we have the installer
if ! command -v amdgpu-install &> /dev/null; then
    echo "ERROR: amdgpu-install not found. Please install ROCm first."
    exit 1
fi

# Install ROCm without DKMS (the critical fix)
sudo amdgpu-install --usecase=rocm --no-dkms -y
echo "✓ ROCm installed without DKMS"
echo ""

echo "Step 3: Verifying installation..."
# Check no dkms
dkms status | grep amdgpu || echo "✓ No amdgpu DKMS"
echo ""

echo "Step 4: Reloading kernel modules..."
sudo modprobe -r amdgpu || true
sudo modprobe amdgpu
echo "✓ amdgpu module reloaded"
echo ""

echo "Step 5: Testing ROCm detection..."
rocminfo | grep -i "gfx1151\|radeon" | head -5
echo ""

echo "=== Fix Applied ==="
echo ""
echo "You MUST reboot before testing Lemonade:"
echo "  sudo reboot"
echo ""
echo "After reboot, test with:"
echo "  lemonade load Gemma-4-E2B-it-GGUF --llamacpp rocm --ctx-size 4096"
