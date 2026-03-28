"""Extract Triton kernel source from Helion on CPU."""
import helion
import helion.language as hl
import torch


@helion.kernel()
def mxfp4_gemm(
    A_q: torch.Tensor,
    A_scale: torch.Tensor,
    B_q: torch.Tensor,
    B_scale: torch.Tensor,
) -> torch.Tensor:
    M = A_q.shape[0]
    N = B_q.shape[1]
    out = torch.empty([M, N], dtype=torch.bfloat16, device=A_q.device)
    for tile_m, tile_n in hl.tile([M, N]):
        acc = hl.zeros([tile_m, tile_n], dtype=torch.float32)
        for tile_k in hl.tile(A_q.shape[1]):
            acc = hl.dot_scaled(
                A_q[tile_m, tile_k], A_scale[tile_m, :], "e2m1",
                B_q[tile_k, tile_n], B_scale[:, tile_n], "e2m1",
                acc=acc,
            )
        out[tile_m, tile_n] = acc.to(torch.bfloat16)
    return out


if __name__ == "__main__":
    aq = torch.empty(256, 256, dtype=torch.uint8, device="cpu")
    asc = torch.empty(256, 16, dtype=torch.uint8, device="cpu")
    bq = torch.empty(256, 1024, dtype=torch.uint8, device="cpu")
    bsc = torch.empty(16, 1024, dtype=torch.uint8, device="cpu")

    bound = mxfp4_gemm.bind((aq, asc, bq, bsc))
    spec = bound.config_spec

    # Use default config
    default_cfg = spec.default_config()
    print(f"Default config: {default_cfg}")

    # Set it and generate code
    bound.set_config(default_cfg)
    print("\n=== Generated Triton Code ===")
    code = bound.to_triton_code()
    print(code)

    # Also try with larger block sizes for better performance
    print("\n\n=== Trying larger blocks ===")
    try:
        import copy
        cfg2 = copy.deepcopy(default_cfg)
        cfg2.block_sizes = [64, 64, 64]
        bound.set_config(cfg2)
        code2 = bound.to_triton_code()
        print(code2)
    except Exception as e:
        print(f"Larger blocks error: {type(e).__name__}: {e}")
