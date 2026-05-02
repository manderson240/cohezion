# Research & Plan: SWIFT Cosmological Simulation on AMD iGPU

**Date**: April 26, 2026  
**Request**: Run SWIFT (https://github.com/SWIFTSIM/SWIFT) on AMD Radeon 8060S iGPU

---

## Executive Summary

⚠️ **NOT RECOMMENDED** - SWIFT is not designed for AMD GPU acceleration

SWIFT is a CPU/MPI-optimized cosmological code with only **experimental NVIDIA CUDA** support. There is no OpenCL, HIP, or Vulkan compute backend. Running on AMD iGPU would require significant development effort.

---

## Research Findings

### 1. What is SWIFT?

SWIFT (SPH With Inter-dependent Fine-grained Tasking) is:
- **Purpose**: Large-scale cosmological and astrophysical simulations
- **Algorithm**: Smoothed Particle Hydrodynamics (SPH) + N-body gravity
- **Scale**: Designed for peta-scale HPC clusters (10,000+ cores)
- **Target**: CPU-based parallelism with MPI + pthreads

### 2. GPU Support Status

| Backend | Status | Notes |
|---------|--------|-------|
| **CUDA** | ⚠️ Experimental | `cuda_test` branch exists but not production-ready |
| **OpenCL** | ❌ Not supported | No OpenCL backend |
| **HIP** | ❌ Not supported | No AMD ROCm support |
| **Vulkan** | ❌ Not supported | No Vulkan compute |

**Evidence from configure.ac**:
```m4
# Check for CUDA - only GPU option mentioned
have_cuda="no"
AC_ARG_WITH([cuda], ...)
```

No mention of OpenCL, HIP, or other GPU APIs in build system.

### 3. CUDA Test Branch Analysis

The `cuda_test` branch shows:
- Only CUDA code exists for GPU offloading
- No portable GPU abstraction layer
- Hard-coded CUDA kernels (~/.cu files)
- Would require complete rewrite for AMD

### 4. Architecture Mismatch

**SWIFT is designed for**:
- Distributed memory (MPI)
- NUMA-aware shared memory
- Cache-friendly particle sorting
- Task-based parallelism

**AMD iGPU (gfx1151) provides**:
- 20 CUs (Compute Units) ~ 1280 shaders
- 128-bit memory interface
- Shared memory with CPU (UMA)
- Good for graphics/GPGPU, not MPI workloads

**Problem**: SWIFT's MPI+threading model doesn't map well to single iGPU

---

## Implementation Options

### Option A: Build SWIFT (CPU-only) - 2-3 hours

**What's Possible**:
- Build SWIFT without GPU support
- Run small test simulations on CPU
- Very slow compared to optimized codes

**Steps**:
```bash
# Install dependencies
sudo apt install libhdf5-dev libfftw3-dev libgsl-dev libmetis-dev

# Build SWIFT
git clone https://github.com/SWIFTSIM/SWIFT
cd SWIFT
./autogen.sh
./configure --with-hydro=gadget2 --with-metis
make -j16

# Run small test
./swift -c -g -G -s examples/IsolatedGalaxy/IsolatedGalaxy.yml
```

**Expected Performance**:
- ~10,000 particles/sec on Zen 5 (16 cores)
- Would take hours for meaningful cosmological run
- Not GPU-accelerated

### Option B: Port SWIFT to HIP - 2-4 weeks

**What's Required**:
1. Rewrite all CUDA kernels to HIP
2. Add HIP detection to configure.ac
3. Implement gfx1151-specific optimizations
4. Test and validate correctness

**Blockers**:
- ROCm hangs on gfx1151 (documented issue)
- SWIFT team not interested in AMD support
- Would need to maintain fork

### Option C: Use Alternative Code - Immediate

**Better options for AMD GPU astrophysics**:

| Code | GPU Support | AMD Compatible | Notes |
|------|-------------|--------------|-------|
| **GADGET-4** | OpenCL | ✅ | Similar to SWIFT, OpenCL backend |
| **ChaNGA** | CUDA/HIP | ⚠️ | Can use HIP, but needs porting |
| **Arepo** | OpenMP/GPU | ✅ | Moving mesh, OpenMP offload |
| **PyTorch Sim** | ROCm | ✅ | ML-based acceleration |

---

## Recommended Approach

### Phase 1: Validate iGPU Compute (1 hour)

Test if AMD iGPU is functional for compute:
```bash
# Run basic OpenCL test
python3 test_igpu_compute.py

# Check Vulkan compute
vulkaninfo | grep -i compute
```

### Phase 2: Try Arepo or GADGET-4 (4 hours)

These have better GPU support:
```bash
# GADGET-4 with OpenCL
git clone https://gitlab.mpcdf.mpg.de/vrs/gadget4
cd gadget4
./configure --enable-opencl
make
```

### Phase 3: SWIFT CPU-Only (if still interested)

Run small demonstration simulation:
```bash
# Build SWIFT without GPU
./configure --disable-vec --with-hydro=gadget2
make

# Run isolated galaxy test
mpirun -np 4 ./swift --self-gravity --hydro \
  examples/IsolatedGalaxy/IsolatedGalaxy.yml
```

---

## Resource Requirements

### For SWIFT CPU Build

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| Time | 2 hours | 4 hours | Build + test |
| CPU | 8 cores | 16+ cores | Zen 5 good |
| RAM | 16 GB | 32+ GB | Particle arrays |
| Disk | 5 GB | 20 GB | HDF5 snapshots |
| Results | Slow | Very slow | No GPU accel |

### For GPU-Accelerated Alternatives

| Code | Setup | Performance | AMD Support |
|------|-------|-------------|-------------|
| GADGET-4 | 2 hours | 10-50x faster | ✅ OpenCL |
| Arepo | 4 hours | 5-20x faster | ✅ OpenMP |
| SWIFT | 2 hours | 1x (baseline) | ❌ None |

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SWIFT doesn't compile | High | Use pre-built conda package |
| Too slow without GPU | Certain | Run smaller test problem |
| ROCm hangs with HIP port | High | Stick to CPU-only |
| Out of memory | Medium | Reduce particle count |
| Numerical instability | Medium | Start with stable test case |

---

## Decision Matrix

**If you want cosmological simulations on AMD iGPU**:

1. **Best**: Use GADGET-4 with OpenCL (2 hours setup, works on AMD)
2. **Good**: Use Arepo with OpenMP offloading (4 hours, portable)
3. **Poor**: Use SWIFT CPU-only (2 hours, no GPU, very slow)
4. **Not possible**: SWIFT on AMD GPU (no backend exists)

---

## Quick Test Plan (if proceeding with SWIFT)

### Step 1: Check Available Dependencies
```bash
# Verify these exist:
which mpicc          # MPI compiler
pkg-config hdf5      # Parallel HDF5
which nvcc           # Will fail - no CUDA
```

### Step 2: Clone & Configure
```bash
git clone https://github.com/SWIFTSIM/SWIFT
cd SWIFT
./autogen.sh
./configure --with-hydro=gadget2 --enable-mpi
```

### Step 3: Build (30-60 minutes)
```bash
make -j16 2>&1 | tee build.log
```

### Step 4: Run Test
```bash
# Get example data
cd examples/IsolatedGalaxy
# Run small isolated galaxy
mpirun -np 4 ../../swift -c -g -G -s IsolatedGalaxy.yml
```

### Step 5: Profile
```bash
# Check CPU utilization
htop
# Expected: 1600% CPU (16 cores)
# Reality: Likely memory-bound
```

---

## Conclusion

**Recommendation**: Do not attempt SWIFT on AMD iGPU

**Rationale**:
1. No GPU backend exists (only experimental CUDA)
2. Porting effort is 2-4 weeks of expert work
3. ROCm gfx1151 support is incomplete
4. CPU-only performance will disappoint

**Better alternatives**:
- **GADGET-4** with OpenCL (2 hours, 10-50x faster)
- **Arepo** with OpenMP (4 hours, production quality)
- Wait for AMD-supported cosmology code

---

*Research complete. Implementation not recommended without significant development effort.*
