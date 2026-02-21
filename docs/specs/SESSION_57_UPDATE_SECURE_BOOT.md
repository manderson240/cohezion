# Session 57 Update: Secure Boot Blocking GPU Training

## Status After Reboot

- ✅ ROCm 7.2 packages installed
- ❌ AMDGPU kernel module not loading
- 🔒 **Root Cause**: Secure Boot enabled, blocking unsigned amdgpu module

## Secure Boot Issue

```
mokutil --sb-state
# Output: SecureBoot enabled

modprobe amdgpu
# Error: Key was rejected by service
```

## Options to Enable GPU Training

### Option 1: Disable Secure Boot (Recommended for dev machine)
1. Reboot → Enter UEFI setup (F2 or Del)
2. Navigate to Boot/Security tab
3. Disable "Secure Boot"
4. Save & Exit
5. Reboot and verify: `rocminfo`

### Option 2: Enroll MOK Key
```bash
sudo mokutil --disable-validation
# Creates enrollment request, requires reboot + physical confirmation
```

## Current Fallback: Modelfile Soft-Finetuning

While Secure Boot is enabled, we can still iterate using:
- `cohezion_v1` (phi3:mini, 2.2GB) - deployed
- `cohezion_v2` (qwen3:8b, 5.2GB) - deployed

These use Ollama Modelfiles for system prompt-based "soft finetuning".

## Next Steps

1. Disable Secure Boot OR enroll MOK
2. Reboot
3. Verify: `rocminfo` shows GPU
4. Install PyTorch ROCm: `uv pip install torch --index-url https://download.pytorch.org/whl/rocm6.0`
5. Run QLoRA training: `llamafactory-cli train examples/training/qwen3_cohezion_qlora.yaml`

## Files
- Spec: `docs/specs/LOCAL_MODEL_FINETUNING_PIPELINE_SPEC.md`
- Vault log: `~/vaults/cohezion-vault/experiments/session-57-local-finetuning.md`
