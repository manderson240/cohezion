# CPU-lane measurement — Qwen3-Coder-30B-A3B (Q4_K_M), Strix Halo, 2026-09-30

Method: `scripts/ops/silicon_bench.py --gguf <file> --threads-list 8,12,16` (router-free; runs
Lemonade's own `llamacpp/cpu` `llama-bench`, `-p 512 -n 128 -r 3`). CPU kernels loaded: `zen4` set.

| Threads | Decode tok/s | Prefill tok/s (pp512) |
|---:|---:|---:|
| 8  | 13.65 | 53.9  |
| 12 | 13.91 | 45.8  |
| 16 | 16.85 | 127.1 |

## What this says
- **Decode is bandwidth-bound, not compute-bound:** doubling threads 8 -> 16 bought +23%.
  ~3.3B active params at Q4_K_M is ~2 GB/token, so 16.85 tok/s is ~34 GB/s of effective CPU-side
  read bandwidth — a fraction of the 256 GB/s LPDDR5X peak. (Active-bytes figure is an estimate.)
- **Threads 8 is the efficient setting:** ~81% of the 16-thread decode on half the cores, leaving
  cores for finetuning dataloaders and the OS.
- The prior estimate (25-35 tok/s) was ~2x too optimistic. Vendor NPU figures for a 35B-A3B MoE
  (17.5 tok/s decode, other hardware) are in the same range as this CPU result.

## Caveats (read before relying on the numbers)
- **Noisy:** measured on a shared box (load average ~6.5 from other sessions). Prefill is
  non-monotonic (12 threads slower than 8), which is contention, not a real effect. One sweep.
- Single model, one context (pp512/tg128), zen4 kernel build on Zen5 hardware.
- Prefill (~50-130 tok/s) makes a 2k-token prompt a 15-40 s wait: fine for background agents,
  poor for interactive use.
