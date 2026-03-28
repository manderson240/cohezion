"""Helion kernel generator for MLA-style attention on AMD MI355X.

This generates Triton code that can be adapted for the MLA decode kernel.
DeepSeek R1 MLA parameters:
- Q dimension: 576 (KV_LORA_RANK 512 + QK_ROPE_HEAD_DIM 64)
- V dimension: 512 (KV_LORA_RANK)
- FP8 quantization for Q and KV
- Loose tolerance: rtol=0.1, atol=0.1

Usage:
    source .venv-helion/bin/activate
    python helion_mla_generator.py
"""

import torch
import helion
import helion.language as hl


@helion.kernel(autotune_effort="none", print_output_code=True)
def mla_decode_simplified(
    q: torch.Tensor,  # [total_q, num_heads, 576] - absorbed query
    kv_buffer: torch.Tensor,  # [total_kv, num_kv_heads, 576] - compressed KV
) -> torch.Tensor:
    """Simplified MLA decode - fused attention for single batch.

    Computes: softmax(Q @ K^T / sqrt(576)) @ V
    Where K and V are from compressed KV buffer.
    """
    total_q, num_heads, qk_dim = q.shape
    total_kv, num_kv_heads, _ = kv_buffer.shape
    v_dim = 512
    sm_scale = 1.0 / (576**0.5)

    out = torch.empty([total_q, num_heads, v_dim], dtype=torch.bfloat16)

    # Tile over (num_heads) dimension
    for tile_h in hl.tile([num_heads]):
        # For each head
        for pos_q in range(total_q):
            # Q for this position and head: [qk_dim]
            q_vec = q[pos_q, tile_h, :]

            # Accumulator for output
            acc = hl.zeros([v_dim], dtype=torch.float32)

            # Iterate over KV sequence
            for tile_kv in hl.tile([total_kv]):
                # K for this KV position: [qk_dim]
                k_vec = kv_buffer[tile_kv, 0, :]

                # Score: Q @ K^T (dot product)
                score = torch.dot(q_vec, k_vec) * sm_scale

                # For proper attention, we'd need online softmax
                # Simplified: just accumulate
                v_vec = kv_buffer[tile_kv, 0, :v_dim]
                acc = acc + v_vec * score

            out[pos_q, tile_h, :] = acc.to(torch.bfloat16)

    return out


@helion.kernel(autotune_effort="none", print_output_code=True)
def mla_gemm_kernel(
    a: torch.Tensor,  # [M, K]
    b: torch.Tensor,  # [K, N]
) -> torch.Tensor:
    """Simple GEMM to get base Triton patterns."""
    m, k = a.shape
    n = b.shape[1]

    c = torch.empty([m, n], dtype=torch.bfloat16)

    for tile_m, tile_n in hl.tile([m, n]):
        acc = hl.zeros([tile_m, tile_n], dtype=torch.float32)

        for tile_k in hl.tile([k]):
            a_tile = a[tile_m, tile_k]
            b_tile = b[tile_k, tile_n]
            acc = torch.matmul(a_tile, b_tile) + acc

        c[tile_m, tile_n] = acc.to(torch.bfloat16)

    return c


def main():
    """Generate Triton code from Helion kernels."""
    print("=" * 80)
    print("Generating Triton code for MLA decode kernels")
    print("=" * 80)

    # Create dummy inputs for GEMM
    m, k, n = 64, 576, 512
    a = torch.zeros(m, k, dtype=torch.bfloat16)
    b = torch.zeros(k, n, dtype=torch.bfloat16)

    print("\n>>> Generating GEMM kernel...")
    try:
        code = mla_gemm_kernel.bind((a, b)).to_triton_code()
        print(code)

        # Save to file
        with open("luma_speedrun/helion_generated_gemm.py", "w") as f:
            f.write(code)
        print("\nSaved to luma_speedrun/helion_generated_gemm.py")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Kernel generation complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
