# Popcorn CLI Usage Guide for Luma AMD Speedrun

## Quick Reference

### Installation
```bash
# One-line install (Linux/macOS)
curl -fsSL https://raw.githubusercontent.com/gpu-mode/popcorn-cli/main/install.sh | bash

# Or download from releases:
# https://github.com/gpu-mode/popcorn-cli/releases/latest
```

### Authentication
```bash
# Register with Discord (recommended)
popcorn-cli register discord

# Or register with GitHub
popcorn-cli register github

# If auth issues, re-register
popcorn-cli reregister discord

# Verify auth
cat ~/.popcorn.yaml
```

### Submission Commands

#### 1. Test Mode (Check Correctness)
```bash
popcorn-cli submit submission.py \
  --leaderboard amd-mixed-mla \
  --gpu MI355X \
  --mode test \
  --no-tui
```

#### 2. Benchmark Mode (Get Performance)
```bash
popcorn-cli submit submission.py \
  --leaderboard amd-mixed-mla \
  --gpu MI355X \
  --mode benchmark \
  --no-tui
```

#### 3. Leaderboard Mode (Official Submission)
```bash
popcorn-cli submit submission.py \
  --leaderboard amd-mixed-mla \
  --gpu MI355X \
  --mode leaderboard \
  --no-tui
```

### Leaderboard Names
- `amd-mixed-mla` - MLA Decode
- `amd-mxfp4-mm` - MXFP4 GEMM
- `amd-moe-mxfp4` - MXFP4 MoE

### File Directives (Embed in submission.py)
```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

def custom_kernel(data):
    # Your implementation
    pass
```

With directives, submit simply:
```bash
popcorn-cli submit submission.py --mode test --no-tui
```

### Managing Submissions
```bash
# List your submissions
popcorn-cli submissions list --leaderboard amd-mixed-mla

# Limit results
popcorn-cli submissions list --leaderboard amd-mixed-mla --limit 10

# View submission details
popcorn-cli submissions show <ID>

# Delete submission
popcorn-cli submissions delete <ID>
```

### Submission Modes Explained

| Mode | Purpose | Time | Affects Leaderboard |
|------|---------|------|---------------------|
| `test` | Verify correctness | ~240s | No |
| `benchmark` | Get performance | ~240s | No |
| `leaderboard` | Official rank | ~240s | Yes |
| `profile` | NCU profiling | Varies | No |

### Key Timing Information
- **Timeout**: 300 seconds (5 minutes)
- **JIT Compilation**: ~170s (aiter module building)
- **Kernel Execution**: Microseconds (9-158µs)
- **Total**: 240-300s per submission

### Workflow Best Practices
1. **Test first** - Verify correctness before benchmarking
2. **Benchmark second** - Check performance before official submission
3. **Submit to leaderboard last** - Only when ready
4. **Wait between submissions** - Allow queue to clear
5. **Use --no-tui** - For scripts and CI/CD

### Troubleshooting

**Timeout Error:**
- Submission took >300s
- Retry during off-peak hours
- Check if JIT compilation is caching

**Auth Error (401):**
```bash
popcorn-cli reregister discord
# or
popcorn-cli reregister github
```

**Import Errors:**
- Expected locally (aiter not installed)
- Will work on runner (pre-installed)
- Test with: `python3 -m py_compile submission.py`

**File Not Found:**
- Use absolute paths: `/home/user/path/submission.py`
- Ensure file is readable

### Competition Details
- **Qualifier Phase**: March 6 - April 6, 2026
- **Finals Phase**: April 7 - May 15, 2026
- **Prize Pool**: $1.1M total
- **Top 10**: Advance to finals ($10K each)

### Resources
- **Reference Kernels**: https://github.com/gpu-mode/reference-kernels
- **Discord**: https://discord.gg/gpumode
- **Documentation**: https://github.com/gpu-mode/popcorn-cli

### Submission File Requirements

**Must export:**
```python
def custom_kernel(data: input_t) -> output_t:
    """Main entry point."""
    # Implementation
    return output
```

**Input/Output Types:**
- Import from `task`: `from task import input_t, output_t`
- Match reference implementation signatures

**No __future__ imports:**
- Popcorn CLI injects code at top of file
- `from __future__` imports will cause syntax errors
- Keep imports simple and at top

### Example Submission Structure
```python
"""
Kernel description and optimization notes.
"""

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

import torch
from task import input_t, output_t
# ... other imports

def custom_kernel(data: input_t) -> output_t:
    """
    Optimized kernel implementation.
    """
    # Unpack data
    # Process with aiter kernels
    # Return output
    pass
```

---

**Last Updated**: 2026-03-18
**Session**: hip-kernels-kimi-k2-5
