# gfx1151 ROCm Final Status 2026-04-10

## Experiment Results

### ROCm 7.2.1 + Custom llama.cpp Build
- **Status**: Failed - hang persists
- **ROCm Version**: 7.2.1.70201-81~24.04
- **NPU Status**: Working (75+ TPS via FLM)
- **GPU Status**: Detected but inference hangs at `sched_reserve`

### Key Changes Applied
1. Upgraded ROCm 7.2.0 → 7.2.1
2. Built llama.cpp with gfx1151 + ROCWMMA optimizations:
   - `-DGGML_HIP=ON`
   - `-DAMDGPU_TARGETS="gfx1151"`
   - `-DGGML_HIP_ROCWMMA_FATTN=ON`
   - Git commit: 5dd1025
3. Replaced Lemonade's bundled llama-server

### System State Now
- ROCm detects both GPU (`gfx1151`) and NPU (`aie2p`)
- NPU fully operational via FLM
- GPU inference still blocked by Issue #6027 (scheduler hang)
- Hang manifests as 100% CPU spin during layer offloading

### Working Recommendation
**Use FLM NPU** for local inference:
```bash
flm serve gemma3:4b --port 13306  # 60-80 TPS
```

**Vulkan backend** as alternative (requires SDK install).

## Blocking Issue
llama.cpp Issue #6027 - `sched_reserve` deadlock on RDNA3.5/gfx1151.

Not fixed by:
- ROCm 7.2.1 driver update
- PR #21344 VGPR optimizations
- -fit off flag

## Resources
- Full report: `GFX1151_ROCM_FINAL_STATUS.md`
- Backup: `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server.backup.original`
- Build source: `/tmp/llama.cpp/`

## Next Steps
1. Monitor for Lemonade >10.2.0 with gfx1151 fix
2. Install Vulkan SDK to test alternative backend
3. Continue using NPU for production workloads

Tags: #rocm #gfx1151 #lemonade #npu #amd #strix-halo
