# EXACT 32x32 MFMA D-Matrix Register Layout

Source: AMD matrix_calculator (CDNA3 v_mfma_f32_32x32x16_fp8_fp8, identical for CDNA4)

## Formula
For thread tid (0-63), register index r (0-15):
```
D[row][col] where:
  col = tid % 32
  row = (r % 4) + (r / 4) * 8 + (tid / 32) * 4
```

## Register-to-Row Mapping

| Register | Lanes 0-31 Rows | Lanes 32-63 Rows |
|----------|-----------------|------------------|
| v0-v3    | 0-3             | 4-7              |
| v4-v7    | 8-11            | 12-15            |
| v8-v11   | 16-19           | 20-23            |
| v12-v15  | 24-27           | 28-31            |

## C++ Epilogue Code
```cpp
int col = bn + (tid % 32);
if (col < N) {
    for (int r = 0; r < 16; r++) {
        int row = bm + (r % 4) + (r / 4) * 8 + (tid / 32) * 4;
        if (row < M) {
            C[row * N + col] = (__hip_bfloat16)(c_reg[r]);
        }
    }
}
```

## Key Insight
The blog's pattern `(tid/32)*4 + j + i*8` with `r = i*4 + j` IS correct:
  row = (tid/32)*4 + (r%4) + (r/4)*8

If c_reg[r] maps to VGPR v_r in order, the blog's epilogue is CORRECT.
The bug was likely in the INPUT mapping (A/B loading), not the output.

## CRITICAL: ext_vector_type indexing
c_reg[0] MUST correspond to v0 for this mapping to work.
If the compiler reorders registers, the mapping breaks.

## A-Matrix Input Layout

For FP8 32×32×16:
- Thread tid provides A[tid % 32][K_as_bytes_in_registers]
- v0{tid} = A[tid%32][0:4], v1{tid} = A[tid%32][4:8] (lanes 0-31)
- v0{tid} = A[tid%32][8:12], v1{tid} = A[tid%32][12:16] (lanes 32-63)

For FP4 32×32×64 (32 bytes per row):
- Lanes 0-31: a_reg[0..15] = 16 bytes from A[tid%32], K[0:16]
- Lanes 32-63: a_reg[0..15] = 16 bytes from A[tid%32], K[16:32]

A loading: each thread reads 16 consecutive bytes from its row. Simple sequential read.

## B-Matrix Input Layout (CRITICAL — TRANSPOSED!)

B[K][N] NOT B[N][K] — K is packed in bytes WITHIN registers, N is ACROSS lanes.

For FP8 32×32×16:
- Lane tid holds column N=tid%32
- v0{tid}.[7:0] = B[K=0][N=tid%32]
- v0{tid}.[15:8] = B[K=1][N=tid%32]
- v0{tid}.[23:16] = B[K=2][N=tid%32]
- v0{tid}.[31:24] = B[K=3][N=tid%32]
- v1{tid}.[7:0] = B[K=4][N=tid%32]
- Lanes 32-63: v0 holds K[8:12], v1 holds K[12:16] for same column

For FP4 32×32×64 (32 bytes of K data per column):
- Each lane holds K data for one N column
- K bytes packed sequentially in registers
- Lanes 0-31: columns 0-31, K[0:16] (16 bytes)
- Lanes 32-63: columns 0-31, K[16:32] (16 bytes)

B loading: each thread reads K elements from ONE COLUMN.
This means reading B[row_k][col_n] for varying k, fixed n = transpose!
Our B data is stored as B[N, K/2] row-major. Thread tid needs B[*, tid%32].
This requires strided access: B[0][tid%32], B[1][tid%32], ... (stride = K/2)

THIS IS WHY THE BLOG'S B LOADING IS COMPLEX — it performs the B transpose.
