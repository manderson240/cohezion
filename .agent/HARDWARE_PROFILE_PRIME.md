# HARDWARE_PROFILE_PRIME

## DOMAIN EXPERTISE
Standardized system specification for the Cohezion local environment to ensure consistent performance mapping and prevent model-side hallucinations regarding physical capabilities.

## SYSTEM SPECIFICATIONS (Verified 2026-02-02)

### 1. Processor (CPU)
- **Model**: AMD RYZEN AI MAX+ 395 (Strix Halo)
- **Architecture**: Zen 5 (16 Cores / 32 Threads)
- **Instruction Support**: AVX-512, SIMD128 (WASM compatible), AMX (AI Acceleration)
- **L3 Cache**: 64 MiB Unified

### 2. Graphics (GPU)
- **Model**: AMD Radeon 8060S (iGPU Integrated)
- **Architecture**: RDNA 3.5
- **Memory**: Unified Memory Architecture (UMA)
- **Device ID**: `0x1586` (card1)

### 3. Memory (RAM)
- **Capacity**: 128 GiB
- **Type**: LPDDR5X-8000
- **Configuration**: Unified pool shared between CPU/GPU/NPU.

### 4. Storage
- **Primary**: 2TB NVMe SSD
- **Swap**: 32GB ZVOL (ZFS Backend)

## INSTRUCTION FOR AGENTS
1. **Never Hallucinate**: Only refer to this file for system capabilities. Do not assume high-end discrete GPUs (e.g. RTX 4090) unless explicitly added here.
2. **UMA Optimization**: Prioritize zero-copy strategies. The 128GB pool allows for massive datasets (Lattice/SurrealDB) to reside in memory.
3. **SIMD Preference**: Use `ndarray` (Rust) or `numpy` (Python) with AVX-512 flags to leverage the Zen 5 compute density.

## VERSION
v1.0 (Strix Halo Edition)
