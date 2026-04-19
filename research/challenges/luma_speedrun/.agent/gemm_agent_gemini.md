# 🎯 GEMM Agent — Gemini CLI Assignment

**Agent:** Gemini CLI  
**Kernel:** GEMM (amd-mxfp4-mm)  
**Current Best:** 13.425µs (rank ~126)  
**Target:** <8µs (rank ~50)  
**Gap:** 1.7x improvement needed  

---

## 📋 CURRENT STATUS

**Phase:** Pending Agent Spawn  
**Started:** -  
**Last Update:** -  
**ETA:** T+2 hours for first implementation

---

## 🎯 ASSIGNMENT

### Primary Approach: MFMA 128×128 8-Wave Ping-Pong Kernel

**From MFMA_TILED_BLUEPRINT.md:**
The only path to beat aiter's CK ASM (4.3µs leader) is custom HIP with:
- 512 threads = 8 waves of 64
- Output tile: 128×128 (4×4 grid of 32×32 MFMA tiles)
- Double-buffered LDS with XOR swizzle
- Cooperative loading with 128-bit global loads
- Wave scheduling with `__builtin_amdgcn_s_setprio`

**Why This Could Win:**
1. Current best is aiter baseline (13.4µs) — custom MFMA kernel exists (26µs)
2. Gap to leader is 3.1x — needs larger tiles + better parallelism
3. 128×128 tiles amortize dispatch overhead across more compute
4. 8-wave ping-pong hides memory latency

---

## 🔧 TECHNICAL DETAILS

### Implementation Requirements

**File to Create:** `../amd-mxfp4-mm/submission_mfma_128x128_v1.py`

**Architecture:**
```cpp
#define THREADS 512
#define WAVES 8
#define TILE_M 128
#define TILE_N 128
#define TILE_K 64

__global__ __launch_bounds__(THREADS, 1)
void gemm_128x128_pingpong(
    const uint8_t* __restrict__ A,   // [M, K/2] fp4
    const uint8_t* __restrict__ B,   // [N, K/2] fp4
    const uint8_t* __restrict__ As,  // [M, K/32] e8m0
    const uint8_t* __restrict__ Bs,  // [N, K/32] e8m0
    __hip_bfloat16* __restrict__ C, // [M, N] bf16
    int M, int N, int K
) {
    // 8-wave ping-pong scheduling:
    // Wave 0-3: Compute tile A while waves 4-7 load next tile
    // __builtin_amdgcn_s_setprio for priority-based scheduling
    
    // 128×128 output = 16 MFMA 32×32 tiles in 4×4 grid
    // Each wave handles 2×2 = 4 MFMA tiles
    // Double-buffered LDS with XOR swizzle
    // Cooperative 128-bit global loads
}
```

### Key Optimizations

1. **Wave Scheduling:**
   ```cpp
   __builtin_amdgcn_s_setprio(1);  // Higher priority for compute waves
   __builtin_amdgcn_s_setprio(0);  // Lower priority for load waves
   ```

2. **LDS Double Buffering:**
   ```cpp
   __shared__ uint8_t lds_a[2][TILE_M * TILE_K / 2];  // Ping-pong buffers
   __shared__ uint8_t lds_b[2][TILE_N * TILE_K / 2];
   ```

3. **XOR Swizzle for Bank Conflict Avoidance:**
   ```cpp
   int swizzled = (lane ^ (lane >> 4)) & 0xF;  // Example pattern
   ```

4. **128-bit Global Loads:**
   ```cpp
   typedef int4 load_t;  // 128-bit vector load
   load_t data = *(load_t*)(ptr + offset);
   ```

---

## 🧪 TESTING PROTOCOL

### Step 1: Correctness (Test Mode)
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-mxfp4-mm
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission_mfma_128x128_v1.py
```

**Expected:** 4/4 tests pass

### Step 2: Benchmark (If Correct)
```bash
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission_mfma_128x128_v1.py
```

**Target:** <10µs geomean (first milestone)

---

## 📝 DISCOVERY LOG

### (To be populated by Gemini CLI...)

---

## 🚧 BLOCKER TRACKER

| Blocker | Status | Resolution |
|---------|--------|------------|
| Agent spawn | ⚪ PENDING | Waiting for activation signal |

---

## 🔗 REFERENCES

- [MFMA_TILED_BLUEPRINT.md](../MFMA_TILED_BLUEPRINT.md) — Architecture blueprint
- [Session 95 Findings](../SESSION_95_CONTINUATION.md)
- [Runner Inventory](../RUNNER_INVENTORY.md) — See GEMM section
- [Current GEMM Submission](../amd-mxfp4-mm/submission.py)
- [COORDINATION_HUB](./COORDINATION_HUB.md)
- [SHARED_DISCOVERIES](./SHARED_DISCOVERIES.md)

---

**Activation Signal:** Begin when this file is modified with "🟢 ACTIVE"
