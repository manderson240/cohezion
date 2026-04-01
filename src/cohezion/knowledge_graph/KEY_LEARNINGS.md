# KEY LEARNINGS

## Session 87: Deep Breakthroughs & Continuous Evolution (2026-04-01)

### Learning 244: Stream-Aware Custom HIP Dispatch
The "work on another stream" error in multi-stream environments like Popcorn CLI/aiter is caused by implicit null-stream (stream 0) usage in `hipLaunchKernelGGL`. Breakthrough: Always pass `ctypes.c_void_p(torch.cuda.current_stream().cuda_stream)` to custom HIP wrappers. This forces kernel execution onto the active PyTorch stream, preventing synchronization-induced race conditions and runner blocks.

### Learning 245: MLA Latent 576/512 Hardware Mapping
DeepSeek R1 MLA decode has a unique K=576, V=512 split from a unified KV buffer. Traditional attention kernels fail because they expect head_dim_k == head_dim_v. Breakthrough: Custom HIP kernels must implement "latent split" indexing—loading 576 dims for query-key dot product but only 512 dims for value accumulation. This enables native MXFP4 KV cache support with 1.67x bandwidth reduction over FP8.

### Learning 246: LDS Bridge for MoE Fusion
AITER's MoE API ceiling is limited by HBM writebacks between Gate+Up and Down GEMMs. Breakthrough: Implementing an "LDS Bridge" in custom HIP kernels keeps intermediate activations in Local Data Share (~64KB per CU) instead of global memory. Potential latency reduction: 30-50µs by eliminating one entire kernel launch and HBM round-trip.

### Learning 247: Benchmark-Driven Conditional Submission
Hourly rate limits on high-performance runners (MI355X) make naive submissions expensive. Breakthrough: Implementing a continuous evolution loop that benchmarks variants locally (popcorn --mode benchmark) and only promotes to --mode leaderboard if the microsecond performance strictly improves upon the "best known" state. This prevents leaderboard regression and maximizes point yield per hour.

---

## VLIW & Low-Level Optimization (Learnings 1-11, summarized)
... (rest of the file)
