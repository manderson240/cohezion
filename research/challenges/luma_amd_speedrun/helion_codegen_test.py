"""Test Helion code generation on CPU — extract Triton kernel source."""
import helion
import helion.language as hl
import torch


@helion.kernel(settings=helion.Settings(print_output_code=True))
def bf16_gemm(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    out = torch.empty([x.shape[0], y.shape[1]], dtype=x.dtype, device=x.device)
    for tile_m, tile_n in hl.tile([out.shape[0], out.shape[1]]):
        acc = hl.zeros([tile_m, tile_n], dtype=torch.float32)
        for tile_k in hl.tile(x.shape[1]):
            acc = hl.dot(x[tile_m, tile_k], y[tile_k, tile_n], acc)
        out[tile_m, tile_n] = acc.to(out.dtype)
    return out


@helion.kernel(settings=helion.Settings(print_output_code=True))
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
    print("=== bf16 GEMM bind ===")
    try:
        a = torch.empty(256, 512, dtype=torch.bfloat16, device="cpu")
        b = torch.empty(512, 1024, dtype=torch.bfloat16, device="cpu")
        bound = bf16_gemm.bind((a, b))
        print(f"Bound type: {type(bound)}")
        attrs = [x for x in dir(bound) if not x.startswith("_")]
        print(f"Attrs: {attrs}")
        for attr in ["source_code", "triton_code", "code", "output_code", "src"]:
            if hasattr(bound, attr):
                print(f"\n=== {attr} ===")
                print(getattr(bound, attr))
    except Exception as e:
        print(f"bf16 error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== MXFP4 GEMM bind ===")
    try:
        aq = torch.empty(256, 256, dtype=torch.uint8, device="cpu")
        asc = torch.empty(256, 16, dtype=torch.uint8, device="cpu")
        bq = torch.empty(256, 1024, dtype=torch.uint8, device="cpu")
        bsc = torch.empty(16, 1024, dtype=torch.uint8, device="cpu")
        bound = mxfp4_gemm.bind((aq, asc, bq, bsc))
        print(f"Bound type: {type(bound)}")
        attrs = [x for x in dir(bound) if not x.startswith("_")]
        print(f"Attrs: {attrs}")
        for attr in ["source_code", "triton_code", "code", "output_code", "src"]:
            if hasattr(bound, attr):
                print(f"\n=== {attr} ===")
                print(getattr(bound, attr))
    except Exception as e:
        print(f"mxfp4 error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
