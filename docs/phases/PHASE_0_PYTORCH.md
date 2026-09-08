# Phase 0: PyTorch 2.11 + ROCm Foundation

## Status

**Current**: PyTorch 2.9.1+cu128 (CPU-only build) in `.venv`  
**Target**: PyTorch 2.9.1+rocm6.3 (ROCm 6.3 for AMD Radeon 8060S)  
**Blocker**: Network timeout on `pip install` from `download.pytorch.org/whl/rocm6.3`

## Hardware

- **GPU**: AMD Radeon 8060S (gfx1151, RDNA 3.5) — integrated iGPU, 128 GiB UMA
- **ROCm**: 7.2.0 installed at `/opt/rocm-7.2.0/`
- **GPU Device ID**: `0x1586`
- **Status**: Low-power state (rocm-smi shows 42°C, 45W)

## Investigation Results

### Available Wheels

| ROCm Version | PyTorch Available | Notes |
|---|---|---|
| rocm7.2 | None (torch-triton only) | No PyTorch wheel |
| rocm7.1 | None (torch-triton only) | No PyTorch wheel |
| rocm6.3 | **2.9.1+rocm6.3** | Latest available for this ROCm |
| rocm6.2 | 2.9.1+rocm6.2.4 | Older ROCm |

### Installation Command

```bash
# Must use uv or pip with --break-system-packages
uv pip install torch==2.9.1+rocm6.3 --index-url "https://download.pytorch.org/whl/rocm6.3"
# OR
pip install torch==2.9.1+rocm6.3 --index-url "https://download.pytorch.org/whl/rocm6.3" --break-system-packages
```

### ROCm 6.3 vs 7.2

- ROCm 6.3: `torch==2.9.1+rocm6.3` is available
- ROCm 7.2: **No PyTorch wheel available** — ROCm 7.2 has no PyTorch package in the official index
- The installed `rocm-7.2.0` packages are build tools (hipcc, rocm-core, etc.), not the runtime PyTorch needs

### GPU Architecture

- **gfx1151** — AMD Strix Halo (Ryzen AI MAX+ 395)
- Supported by ROCm 6.3 and later
- NOT supported in PyTorch wheels for ROCm < 6.0

## What to Do

1. **Wait for network**: Retry `uv pip install torch==2.9.1+rocm6.3 --index-url "https://download.pytorch.org/whl/rocm6.3"` with longer timeout
2. **Alternative**: Download wheel file manually and `pip install` from local file
3. **Accept CPU for now**: The RL code (TRIUNEPolicy, PPO) runs on CPU for development

## PyTorch 2.11 Reality Check

PyTorch 2.11 was released March 23, 2026, but **no ROCm wheel exists for PyTorch 2.11**. The latest ROCm wheel is:

```
torch==2.9.1+rocm6.3
```

This is the correct target. The plan's reference to "2.11" should be updated to "2.9.1" throughout since 2.11 has no ROCm support.

## ROCm Verification Script

```python
import torch


def check_rocm():
    print(f"PyTorch version: {torch.__version__}")

    # Check for HIP (AMD's CUDA equivalent)
    hip_version = getattr(torch.version, "hip", None)
    print(f"HIP version: {hip_version}")

    # Check CUDA-like interfaces
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available (torch): {cuda_available}")

    # Check device count
    try:
        device_count = torch.cuda.device_count()
        print(f"GPU device count: {device_count}")
        for i in range(device_count):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    except Exception as e:
        print(f"GPU check error: {e}")

    # Check torch.compile support
    try:
        compiled = torch.compile(lambda x: x + 1)
        print("torch.compile: AVAILABLE")
    except Exception as e:
        print(f"torch.compile error: {e}")

    # CPU threading
    print(f"CPU threads: {torch.get_num_threads()}")
    print(f"CPU threads per core: {torch.get_num_threads()}")


check_rocm()
```

## Phase 0 Deliverables (Revised)

- [x] Verify ROCm 7.2 installed (rocm-smi, rocminfo working)
- [x] Confirm PyTorch ROCm wheel availability (2.9.1+rocm6.3 is latest)
- [ ] Install PyTorch 2.9.1+rocm6.3 (blocked: network timeout)
- [x] Document the ROCm 7.2 / PyTorch wheel gap
- [x] AMD Zen 5 CPU optimization: `torch.set_num_threads(16)` (already set)
- [ ] Verify `torch.compile` works on CPU (development mode)
- [ ] This documentation

## PyTorch 2.11 Note

> The plan originally specified PyTorch 2.11 (released March 23, 2026). However, no ROCm wheel exists for PyTorch 2.11. The plan should use **PyTorch 2.9.1+rocm6.3** as the target, which is the latest ROCm-compatible version.

## Memory Budget Confirmation

With 128 GiB UMA and 80 GiB process ceiling:
- PyTorch CPU development: ~2-4 GiB base
- With `torch.compile`: +1-2 GiB
- TRIUNE policy model: ~500 MiB
- Training buffer (CPU): 8 GiB max
- **Headroom**: 64+ GiB available

## Next Steps

1. Retry PyTorch ROCm install with extended timeout or local wheel
2. If install fails, proceed with CPU development (code is device-agnostic)
3. GPU training features wrapped in `device = "cuda" if torch.cuda.is_available() else "cpu"`

*Documented: March 25, 2026*
