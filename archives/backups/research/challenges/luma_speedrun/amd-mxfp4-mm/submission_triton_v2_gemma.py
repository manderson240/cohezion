Thinking...
Optimize a Triton GEMM kernel for AMD MI355X (gfx950) using `tl.dot_scaled`[15D[K
`tl.dot_scaled`.
23µs.
<13µs. Leader is 4.3µs.
M=16, K=7168. This is the bottleneck shape (currently 50.7µs).

        1.  `BLOCK_K` must be $\ge 128$ (64 fails silently).
        2.  LHS: `[BLOCK_M, BLOCK_K//2]` uint8 (FP4x2 packed).
        3.  RHS: `[BLOCK_K//2, BLOCK_N]` uint8 (K-major).
        4.  LHS Scale: `[BLOCK_M, BLOCK_K//32]` uint8 (M-first).
        5.  RHS Scale: `[BLOCK_N, BLOCK_K//32]` uint8 (N-first).
        6.  B input needs transposition to `[K//2, N]`.
        7.  B scales need unshuffling to `[N, K//32]`.

        *   Increase `BLOCK_K` to 256 or 512 for large K.
        *   Multi-stage accumulation (wider tiles).
        *   Better memory access for B transpose.
        *   Use `BLOCK_M=16` for small M shapes.

    *   *Tiling Strategy:* Currently `_pick_tiles` uses `BLOCK_M=32` for sm[2D[K
small M. The target bottleneck is $M=16$. Setting `BLOCK_M=16` precisely av[2D[K
avoids mask overhead and might improve alignment/utilization for $M=16$ cas[3D[K
cases.
    *   *BLOCK_K:* Current `_pick_tiles` sets `BLOCK_K=256` if $K \ge 4096$[5D[K
4096$. For $K=7168$, $256$ is used. However, $512$ might be even better to [K
reduce the loop count and maximize the compute-to-load ratio.
    *   *BLOCK_N:* Currently $128$. Increasing this (e.g., $256$) might hel[3D[K
help if the GPU can handle the register pressure.
    *   *Memory Layout:* The B transpose is handled outside the kernel (`B_[4D[K
(`B_t = B_bytes.t().contiguous()`). This is correct for `tl.dot_scaled` whi[3D[K
which requires the RHS to be K-major.
    *   *K-loop:* The loop processes `BLOCK_K` elements. For $K=7168$, $716[4D[K
$7168/256 = 28$ iterations. $7168/512 = 14$ iterations.

    *   **Modification 1: `_pick_tiles`**
        *   $M=16$ is a critical shape. Use `BLOCK_M=16` for $M \le 16$.
        *   Increase `BLOCK_K` to $512$ for $K \ge 4096$.
        *   Try increasing `BLOCK_N` to $256$ to increase the workload per [K
block, reducing the number of blocks and improving utilization.

    *   **Modification 2: Kernel Loop**
        *   Ensure `tl.dot_scaled` is the core.
        *   Check if any overheads can be removed.
        *   The scale loads are a bit frequent. Since scales are per 32 ele[3D[K
elements, we load $K_{sg} = BLOCK\_K // 32$. For $BLOCK\_K=512$, $K_{sg}=16[10D[K
$K_{sg}=16$.

    *   **Modification 3: B-scale Unshuffle Optimization**
        *   The current code uses `e8m0_unshuffle` in the cache. This is co[2D[K
correct.
        *   Wait, the bottleneck $M=16, K=7168$ is extremely compute-bound/[14D[K
compute-bound/memory-bound on the K-dimension. Since $M$ is so small, the k[1D[K
kernel is effectively a vector-matrix multiply.
        *   In this case, `BLOCK_M=16` and `BLOCK_N=256` (or larger) is opt[3D[K
optimal.

    *   $M=16, N=...$ (usually $N$ is large in these benchmarks, e.g., 4096[4D[K
4096 or 8192).
    *   If $M=16$, then `grid = (1, N // BLOCK_N)`.
    *   $K=7168$ means the inner loop is the dominant part.
    *   `BLOCK_K = 512` $\rightarrow$ 14 iterations.
    *   `BLOCK_N = 256` $\rightarrow$ More work per SM.

    *   The provided code uses `tl.dot_scaled`.
    *   The memory access patterns for A and B scales are linear.
    *   Check `B_t_ptr` strides. `B_t` is `[K//2, N]`. `B_t_ptr + offs_kb[:[9D[K
offs_kb[:, None] * stride_bk + offs_n[None, :] * stride_bn`. This is row-ma[6D[K
row-major access on a transposed B, which is optimal for the RHS of `dot_sc[7D[K
`dot_scaled`.

    *   Set `BLOCK_M = 16` if $M \le 16$.
    *   Set `BLOCK_K = 512` for $K \ge 4096$.
    *   Set `BLOCK_N = 256`.
    *   Keep the cache logic.
    *   Keep the `e8m0_unshuffle` logic.

    *   $K=7168$
    *   `BLOCK_K=512`
    *   `SGs = 512 // 32 = 16`
    *   A tile: $16 \times 256$ bytes.
    *   B tile: $256 \times 256$ bytes.
    *   As tile: $16 \times 16$ bytes.
    *   Bs tile: $256 \times 16$ bytes.
    *   This fits easily in shared memory/L1.

    *   `tl.dot_scaled` requires specific layouts.
    *   LHS: `[M, K]`
    *   LHS_scale: `[M, K//32]`
    *   RHS: `[K, N]`
    *   RHS_scale: `[N, K//32]`
    *   Our code uses `B_t` as RHS and `Bs_bytes` as RHS_scale.
    *   `B_t` is `[K//2, N]`. `Bs_bytes` is `[N, K//32]`.
    *   This matches the requirements.

    *   `M=16, K=7168`.
    *   `BLOCK_M = 16`.
    *   `BLOCK_N = 256`.
    *   `BLOCK_K = 512`.
    *   The `_pick_tiles` function should be more aggressive.

    *   Wait, if $M=16$, and we use `BLOCK_M=32`, we are masking out half t[1D[K
the block. Using `BLOCK_M=16` is definitely better.
    *   Let's double check the scale indexing.
    *   `offs_sg = k_sg_off + tl.arange(0, K_sg)`
    *   `K_sg = BLOCK_K // 32`. For 512, $K_{sg} = 16$.
    *   This is correct.

    *   Triton's `dot_scaled` is very sensitive to `BLOCK_K`.
    *   $128$ is the minimum. $256$ is standard. $512$ often provides the b[1D[K
best throughput for large $K$.

    *   Slicing/Indexing `S_bytes` in the cache:
        `Bs_unshuffled = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks[2D[K
ks)`
        `Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)`
        This produces `[N, ks]` where $ks = K//32$.
        This is passed as `Bs_ptr`.
        In the kernel: `Bs_ptr + offs_n[:, None] * stride_bsn + offs_sg[Non[11D[K
offs_sg[None, :] * stride_bsk`.
        `stride_bsn` is the row stride (N). `stride_bsk` is the col stride [K
(ks).
        This matches the "N-first" layout.

    *   The logic seems solid. I will implement the `_pick_tiles` update an[2D[K
and ensure the kernel is clean.
...done thinking.

```python
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Triton tl.dot_scaled GEMM for MXFP4 on AMD MI355X (gfx950).

Optimizations for M=16, K=7168 bottleneck:
1. BLOCK_M=16 for small M shapes to eliminate masking overhead.
2. BLOCK_K=512 to maximize compute-to-load ratio for large K.
3. BLOCK_N=256 to increase workload per block and improve SM utilization.
4. Verified BLOCK_K >= 128 for gfx950 stability.
"""

import torch
import triton
import triton.language as tl
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) [K
-> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to recover [orig_m, orig_n] E8M0 layout[6D[K
layout."""
    sm, sn = scale_shuffled.shape
    # The layout is specific to how aiter shuffles the E8M0 scales for the [K
hardware
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


@triton.jit
def fp4_gemm_dotscaled_kernel(
    # Pointers
    A_ptr,  # [M, K//2]  uint8, FP4x2 packed
    B_t_ptr,  # [K//2, N]  uint8, FP4x2 packed, B transposed
    As_ptr,  # [M, K//32] uint8, E8M0 A scales
    Bs_ptr,  # [N, K//32] uint8, E8M0 B scales (N-first, unshuffled)
    C_ptr,  # [M, N]     bf16 output
    # Dimensions
    M,
    N,
    K,
    # Strides
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_asm,
    stride_ask,
    stride_bsn,
    stride_bsk,
    # Tile sizes
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    K_bytes: tl.constexpr = BLOCK_K // 2
    K_sg: tl.constexpr = BLOCK_K // 32

    K_total_bytes = K // 2
    K_total_sg = K // 32

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k_iters = tl.cdiv(K, BLOCK_K)

    for k_iter in range(num_k_iters):
        k_byte_off = k_iter * K_bytes
        k_sg_off = k_iter * K_sg

        offs_kb = k_byte_off + tl.arange(0, K_bytes)
        offs_sg = k_sg_off + tl.arange(0, K_sg)

        # Load A tile
        a_mask = (offs_m[:, None] < M) & (offs_kb[None, :] < K_total_bytes)[14D[K
K_total_bytes)
        a = tl.load(
            A_ptr + offs_m[:, None] * stride_am + offs_kb[None, :] * stride[6D[K
stride_ak,
            mask=a_mask,
            other=0,
        )

        # Load B_t tile (K-major for dot_scaled RHS)
        b_mask = (offs_kb[:, None] < K_total_bytes) & (offs_n[None, :] < N)[2D[K
N)
        b = tl.load(
            B_t_ptr + offs_kb[:, None] * stride_bk + offs_n[None, :] * stri[4D[K
stride_bn,
            mask=b_mask,
            other=0,
        )

        # Load A scales
        as_mask = (offs_m[:, None] < M) & (offs_sg[None, :] < K_total_sg)
        a_scale = tl.load(
            As_ptr + offs_m[:, None] * stride_asm + offs_sg[None, :] * stri[4D[K
stride_ask,
            mask=as_mask,
            other=127,
        )

        # Load B scales (N-first layout)
        bs_mask = (offs_n[:, None] < N) & (offs_sg[None, :] < K_total_sg)
        b_scale = tl.load(
            Bs_ptr + offs_n[:, None] * stride_bsn + offs_sg[None, :] * stri[4D[K
stride_bsk,
            mask=bs_mask,
            other=127,
        )

        # Native MXFP4 Dot Scaled
        acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc)

    c = acc.to(tl.bfloat16)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(
        C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn,
        c,
        mask=c_mask,
    )


def _pick_tiles(M: int, K: int) -> tuple[int, int, int]:
    """Sized for M=16, K=7168 bottleneck."""
    # M=16 is critical; avoid 32 to reduce masking overhead and register pr[2D[K
pressure
    block_m = 16 if M <= 16 else 32
    # Increase BLOCK_K to 512 for large K to reduce loop trips
    block_k = 512 if K >= 4096 else 256
    # Increase BLOCK_N to 256 for better SM utilization
    block_n = 256
    return block_m, block_n, block_k


def _run_triton_gemm(
    A_bytes: torch.Tensor, 
    B_t: torch.Tensor, 
    As_bytes: torch.Tensor, 
    Bs_bytes: torch.Tensor, 
    M: int,
    N: int,
    K: int,
) -> torch.Tensor:
    BLOCK_M, BLOCK_N, BLOCK_K = _pick_tiles(M, K)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A_bytes.device)
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    fp4_gemm_dotscaled_kernel[grid](
        A_bytes,
        B_t,
        As_bytes,
        Bs_bytes,
        C,
        M,
        N,
        K,
        A_bytes.stride(0),
        A_bytes.stride(1),
        B_t.stride(0),
        B_t.stride(1),
        C.stride(0),
        C.stride(1),
        As_bytes.stride(0),
        As_bytes.stride(1),
        Bs_bytes.stride(0),
        Bs_bytes.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    return C


_weight_cache: dict = {}


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    cache_key = (B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _weight_cache:
        _weight_cache.clear()
        B_bytes = B_q.view(torch.uint8)
        B_t = B_bytes.t().contiguous() 
        Bs_unshuffled = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks)[3D[K
ks)
        Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)
        _weight_cache[cache_key] = (B_t, Bs_bytes)

    B_t, Bs_bytes = _weight_cache[cache_key]

    try:
        return _run_triton_gemm(A_bytes, B_t, As_bytes, Bs_bytes, M, N, K)
    except Exception as exc:
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
```

