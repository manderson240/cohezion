---
name: gfx950-mfma-register-layouts
description: |
  MFMA register-to-output mappings for AMD MI355X (gfx950/CDNA4) GPU kernels via load_inline.
  Use when: (1) writing custom HIP kernels with MFMA intrinsics on gfx950,
  (2) getting wrong results from __builtin_amdgcn_mfma_* despite compilation success,
  (3) debugging "output is transposed" or "column 0 correct but column 1+ wrong",
  (4) choosing between FP4 native MFMA vs BF16 MFMA with dequant.
  Key insight: output mapping is COLUMN-MAJOR per thread (4 consecutive rows at 1 column),
  NOT row-major (1 row at 4 consecutive columns). This is the opposite of what you'd assume.
author: Claude Code (Session 90, April 2026)
version: 1.0.0
---

# gfx950 MFMA Register Layouts

## Problem

Writing custom HIP GEMM kernels with MFMA intrinsics on AMD MI355X (gfx950) produces
wrong results because the register-to-output mapping is non-obvious and differs between
instruction sizes. The AMD ROCm blog examples don't clearly distinguish the output format.

## BF16 MFMA 16x16x16 (VERIFIED CORRECT)

### Instruction
```cpp
typedef short v4s __attribute__((ext_vector_type(4)));
typedef float v4f __attribute__((ext_vector_type(4)));
v4f c = __builtin_amdgcn_mfma_f32_16x16x16bf16_1k(a, b, c, 0, 0, 0);
```

### Input Mapping (64 threads, wave64)
```
A input: thread t reads A[tid % 16][(tid / 16) * 4 : +4]  // 4 BF16 from row tid%16
B input: thread t reads B[tid % 16][(tid / 16) * 4 : +4]  // 4 BF16 from row tid%16
```

### Output Mapping (COLUMN-MAJOR per thread)
```
c_reg[j] → C[(tid / 16) * 4 + j][tid % 16]    for j = 0..3
```
- Thread writes to 4 CONSECUTIVE ROWS at a SINGLE COLUMN
- Column = tid % 16 (fixed per thread)
- Row base = (tid / 16) * 4 (group 0: rows 0-3, group 1: rows 4-7, etc.)

### Epilogue Code
```cpp
int out_col = bn + (tid % 16);
int out_row_base = bm + (tid / 16) * 4;
if (out_col < N) {
    for (int j = 0; j < 4; j++) {
        int out_row = out_row_base + j;
        if (out_row < M) {
            C[out_row * N + out_col] = (__hip_bfloat16)(((float*)&c_reg)[j]);
        }
    }
}
```

### Status: VERIFIED (Session 90, 4/4 tests passed, max error 0.0)

## FP4 MFMA 32x32x64 (VERIFIED CORRECT — Session 91)

### CRITICAL: Register Type
```cpp
// WRONG (compilation error: "cannot initialize parameter of type vector of 8 int"):
typedef uint8_t a_reg_t __attribute__((ext_vector_type(16)));  // 16 bytes — WRONG

// CORRECT (MFMA always takes 8×int = 32 bytes, FP4 uses first 16 bytes):
typedef int a_reg_t __attribute__((ext_vector_type(8)));   // 32 bytes
typedef int b_reg_t __attribute__((ext_vector_type(8)));   // 32 bytes
typedef float c_reg_t __attribute__((ext_vector_type(16))); // 16 floats output
```

### Instruction
```cpp
c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
    a_reg, b_reg, c_reg,
    4,     // cbsz = FP4 E2M1 for A
    4,     // blgp = FP4 E2M1 for B
    0,     // neg_a
    sa,    // int: A scale (E8M0 zero-extended to int)
    0,     // neg_b
    sb);   // int: B scale (E8M0 zero-extended to int)
```

### Input A Loading (VERIFIED)
```
Lane tid (0-63), K=64 FP4 elements = 32 bytes per row:
  Row = tid % 32 (lanes 0-31 → rows 0-31, lanes 32-63 → rows 0-31)
  Lanes 0-31:  load bytes [0:16] of row into first 16 bytes of register
  Lanes 32-63: load bytes [16:32] of row into first 16 bytes of register
  Remaining 16 bytes of register (v4-v7) = zero
```
```cpp
int a_row = bm + (tid & 31);
int k_byte_off = kt * 32 + (tid >> 5) * 16;
uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
const uint8_t* a_ptr = A + a_row * K_half + k_byte_off;
for (int i = 0; i < 16; i++) a_bytes[i] = a_ptr[i];
```

### Input B Loading (VERIFIED — B stored as B[N, K/2])
```
B[N, K/2] row-major: each row n contains all K data for column n.
Thread tid loads B[tid%32] row — K packed in registers, N across lanes.
Same loading pattern as A (symmetric for this memory layout).
```

### Output D Mapping (VERIFIED — blog pattern IS CORRECT)
```
c_reg[r] → D[row][col]  where:
  col = tid % 32
  row = (r % 4) + (r / 4) * 8 + (tid / 32) * 4
```
```cpp
for (int r = 0; r < 16; r++) {
    int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
    int out_col = bn + (tid & 31);
    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
}
```

### Scale Handling
```
K=64 FP4 per tile → 2 scale groups (32 FP4 each)
Lanes 0-31:  scale group index = kt * 2 + 0
Lanes 32-63: scale group index = kt * 2 + 1
Each thread provides 1 E8M0 scale, zero-extended to int.
```

### e8m0_unshuffle (recover B scale from shuffled format)
```python
def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]
```

### E8M0 Scale Computation (aiter's formula — Session 91 reverse-engineered)
Aiter does NOT use `ceil(log2(max/6))`. It extracts the BF16 exponent directly:
```cpp
// HIP kernel version:
__hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
int bf16_exp = (bf16_bits >> 7) & 0xFF;
int bf16_man = bf16_bits & 0x7F;
if (bf16_man >= 96) bf16_exp += 1;  // bump when fractional part >= 0.75
int scale_exp = max(bf16_exp - 2, 0);
```
**Key:** The -2 offset and mantissa threshold of 96/128=0.75 are hardware-specific to aiter's
MXFP4 implementation. This can produce scales where max/scale > 6.0, causing FP4 clipping.

### FP4 E2M1 Rounding (round-to-nearest-even)
At midpoints, round toward even mantissa (LSB=0):
```cpp
if      (a <= 0.25f) code = 0;  // even (mantissa=0)
else if (a <  0.75f) code = 1;
else if (a <= 1.25f) code = 2;  // even
else if (a <  1.75f) code = 3;
else if (a <= 2.5f)  code = 4;  // even
else if (a <  3.5f)  code = 5;
else if (a <= 5.0f)  code = 6;  // even
else                  code = 7;
```

### Status: VERIFIED (Session 91, 4/4 tests, max error 0.0, all shapes)
### Benchmark: 19-52µs (v4 with e8m0_unshuffle, no B re-quant)

### WARNING: PyTorch data_ptr Cache Poisoning
Never cache GPU tensor data by `data_ptr()` — PyTorch reuses addresses across
different tensor allocations. Use shape-based keys or content hashes instead.

## Critical HIP/load_inline Patterns

### BFloat16 Type Cast
```cpp
// WRONG (compilation error):
C[idx] = __float2bfloat16(val);    // __hip_bfloat16 != at::BFloat16
C[idx] = at::BFloat16(val);         // type mismatch

// CORRECT:
C[idx] = (__hip_bfloat16)val;       // direct C-style cast
```

### Kernel Launch (NO explicit stream)
```cpp
// WRONG (HTTP 500 "work on another stream"):
kernel<<<grid, block, 0, at::cuda::getCurrentCUDAStream()>>>(args);

// CORRECT (default stream):
kernel<<<grid, block>>>(args);
```

### Thread Synchronization
```cpp
// WRONG (UB when M < BLOCK_M, some threads exit early):
if (row >= M) return;  // threads exit before __syncthreads()
...
__syncthreads();       // remaining threads deadlock or corrupt

// CORRECT (guard writes, all threads participate in sync):
bool valid = (row < M && col < N);
...
__syncthreads();       // ALL threads participate
if (valid) {
    // compute and write
}
```

### Compilation Flags
```python
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"  # BEFORE importing torch
os.environ["CXX"] = "clang++"
extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"]
```

## Vector Types
```cpp
// BF16 16x16
typedef short v4s __attribute__((ext_vector_type(4)));   // 4x int16 for BF16 MFMA input
typedef float v4f __attribute__((ext_vector_type(4)));    // 4x f32 for BF16 output

// FP4 32x32 (MUST use int, NOT uint8_t!)
typedef int a_reg_t __attribute__((ext_vector_type(8)));  // 8x int32 = 32 bytes per thread
typedef int b_reg_t __attribute__((ext_vector_type(8)));  // same for B
typedef float c_reg_t __attribute__((ext_vector_type(16)));  // 16x f32 output
```

All compile on gfx950 with ROCm 7.1.
