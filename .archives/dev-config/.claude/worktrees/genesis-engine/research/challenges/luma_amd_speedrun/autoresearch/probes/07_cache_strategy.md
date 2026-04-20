# Persistent Cache Strategy for AMD Speedrun

**Date:** 2026-03-27
**Objective:** Minimize JIT compilation overhead on Popcorn CLI runners

---

## JIT Compilation Costs

| Component | Build Time | Cacheable |
|-----------|-----------|-----------|
| moe_sorting | ~25s | Yes |
| ck2stages_fp4x2 | ~103s | Yes |
| cktile2stages | ~132s | Yes |
| module_moe_asm | ~31s | Yes |
| **Total** | **~260s** | **All** |

**Problem:** GitHub Actions runners are ephemeral - cache is lost between submissions.

---

## Cache Environment Variables

### Triton Cache

```bash
export TRITON_CACHE_DIR=/tmp/triton_cache
export TRITON_OVERRIDE_DIR=/tmp/triton_override
```

**Behavior:**
- Triton compiles kernels to `$TRITON_CACHE_DIR`
- Reuses cached `.so` files if kernel hash matches
- Default: `~/.triton/cache/` (not persistent on runners)

### AITER Cache

```bash
export AITER_JIT_DIR=/tmp/aiter_jit_cache
export AITER_JIT_BUILD_DIR=/tmp/aiter_jit_build
```

**Behavior:**
- AITER compiles JIT modules to `$AITER_JIT_DIR`
- Modules: `module_moe_sorting`, `module_moe_ck2stages_fp4x2`, etc.
- Must be set BEFORE importing aiter

### Combined Setup

```python
# At the very top of submission.py, before any imports:
import os

# Set cache directories
os.environ['TRITON_CACHE_DIR'] = '/tmp/triton_cache'
os.environ['AITER_JIT_DIR'] = '/tmp/aiter_jit_cache'
os.environ['AITER_JIT_BUILD_DIR'] = '/tmp/aiter_jit_build'

# Create directories
os.makedirs('/tmp/triton_cache', exist_ok=True)
os.makedirs('/tmp/aiter_jit_cache', exist_ok=True)
os.makedirs('/tmp/aiter_jit_build', exist_ok=True)

# Now import aiter
import aiter
```

---

## Cache Persistence on Runners

### Problem: Ephemeral Filesystem

GitHub Actions runners:
- Fresh VM per workflow run
- `/tmp` is local to the VM
- Cache is lost after job completes

### Potential Solutions

#### Option 1: GitHub Actions Cache

```yaml
# .github/workflows/cache.yml
- name: Cache AITER JIT
  uses: actions/cache@v3
  with:
    path: /tmp/aiter_jit_cache
    key: aiter-jit-${{ runner.os }}-${{ hashFiles('**/requirements.txt') }}
```

**Issue:** Requires control over GitHub Actions workflow. Popcorn CLI submissions may not support this.

#### Option 2: Pre-compiled Kernels in Submission

```python
# Include pre-compiled .so files in submission package
# Load them at runtime

import ctypes
import os

so_path = os.path.join(os.path.dirname(__file__), 'jit_cache')
if os.path.exists(so_path):
    # Pre-load cached modules
    for so_file in os.listdir(so_path):
        if so_file.endswith('.so'):
            ctypes.CDLL(os.path.join(so_path, so_file))
```

**Issue:**
- Kernels are machine-specific (gfx950 only)
- May not match runner's ROCm version
- Size constraints on submission package

#### Option 3: Artifact Registry (if available)

```python
# If runners have access to shared storage:
os.environ['AITER_JIT_DIR'] = '/shared/aiter_jit_cache'
```

**Status:** Unknown if Popcorn provides shared storage.

---

## Verification Script

```python
#!/usr/bin/env python3
"""Verify cache setup works correctly."""

import os
import sys

# Set BEFORE importing aiter
os.environ['AITER_JIT_DIR'] = '/tmp/aiter_jit_cache_test'
os.environ['TRITON_CACHE_DIR'] = '/tmp/triton_cache_test'

print("Environment variables set:")
print(f"  AITER_JIT_DIR={os.environ.get('AITER_JIT_DIR')}")
print(f"  TRITON_CACHE_DIR={os.environ.get('TRITON_CACHE_DIR')}")

# Create directories
os.makedirs(os.environ['AITER_JIT_DIR'], exist_ok=True)
os.makedirs(os.environ['TRITON_CACHE_DIR'], exist_ok=True)

print("\nCache directories created.")
print(f"  AITER: {os.listdir(os.environ['AITER_JIT_DIR'])}")
print(f"  TRITON: {os.listdir(os.environ['TRITON_CACHE_DIR'])}")

# Import aiter (triggers JIT if not cached)
try:
    import aiter
    print("\naiter imported successfully.")

    # Check where JIT files are created
    import subprocess
    result = subprocess.run(
        ['find', '/tmp', '-name', '*.so', '-mmin', '-1'],
        capture_output=True, text=True
    )
    if result.stdout:
        print("\nRecently created .so files:")
        print(result.stdout)

except Exception as e:
    print(f"\naiter import failed: {e}")
    sys.exit(1)

print("\nCache verification complete.")
```

---

## Recommendations

### Immediate (Submission-Level)

1. **Set cache env vars at top of submission.py:**
   ```python
   import os
   os.environ['AITER_JIT_DIR'] = '/tmp/aiter_jit_cache'
   os.environ['TRITON_CACHE_DIR'] = '/tmp/triton_cache'
   ```

2. **Verify in stderr:**
   ```python
   import sys
   sys.stderr.write(f"AITER_JIT_DIR={os.environ.get('AITER_JIT_DIR')}\n")
   sys.stderr.write(f"TRITON_CACHE_DIR={os.environ.get('TRITON_CACHE_DIR')}\n")
   ```

3. **Don't rely on cache persistence** between submissions - it's likely not available.

### Long-Term (If Phase 2 Qualified)

1. **Request persistent cache from Popcorn organizers**
2. **Pre-compile kernels for specific shapes**
3. **Use offline JIT to generate portable cache**

---

## Expected Time Savings

| Scenario | Time Without Cache | Time With Cache | Savings |
|----------|-------------------|-----------------|---------|
| First submission | ~260s | ~260s | 0s |
| Cached submission | ~260s | ~30s | ~230s |

**Note:** Cache only helps within a single submission, not across submissions on ephemeral runners.

---

## References

- AITER JIT: https://github.com/ROCm/aiter/blob/main/aiter/jit/core.py
- Triton Cache: https://github.com/triton-lang/triton/blob/main/python/triton/runtime/cache.py
- GitHub Actions Caching: https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows

---

*Document created:* 2026-03-27
*Status:* Ready for implementation
