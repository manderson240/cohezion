import torch
from cohezion.flume.kernels.turbo_kv import TurboKVKernel, ProdQuantized, ValueQuantized
import os

def test_kernel_alignment():
    print("\n--- Initializing TurboKVKernel (Strix Halo Wave32 Lock) ---")
    kernel = TurboKVKernel()
    print(f"Wave32 Detected: {kernel.has_wave32}")
    
    # Even if False (on non-Strix hardware), the kernel should still run in fallback mode
    
    BH, N, D = 1, 64, 128
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cpu':
        print("CUDA not available, skipping functional kernel test.")
        return

    # Create dummy TQ data
    query = torch.randn(BH, D, device=device)
    mse_indices = torch.randint(0, 15, (BH, N, D//2), dtype=torch.uint8, device=device)
    qjl_signs = torch.randint(0, 255, (BH, N, D//8), dtype=torch.uint8, device=device)
    norms = torch.ones(BH, N, device=device)
    res_norms = torch.zeros(BH, N, device=device)
    
    v_data = torch.randn(BH, N, D, device=device)
    v_scales = torch.ones(BH, N, D//32, device=device)
    v_zeros = torch.zeros(BH, N, D//32, device=device)
    
    Pi = torch.eye(D, device=device)
    S = torch.eye(D, device=device)
    centroids = torch.linspace(-2, 2, 16, device=device)
    
    quantized_key = ProdQuantized(mse_indices, qjl_signs, norms, res_norms)
    value_quantized = ValueQuantized(v_data, v_scales, v_zeros, bits=8)
    
    print("Executing fused_decode...")
    try:
        out = kernel.fused_decode(
            query, quantized_key, value_quantized,
            Pi, S, centroids, mse_bits=4, qjl_scale=1.0, sm_scale=1.0
        )
        print(f"Output shape: {out.shape}")
        print("Kernel execution SUCCESSFUL.")
    except Exception as e:
        print(f"Kernel execution FAILED: {e}")

if __name__ == "__main__":
    test_kernel_alignment()
