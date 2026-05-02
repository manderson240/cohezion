# SWIFT Universe Simulation - Implementation Plan

## Goal
Run cosmological simulations using SWIFT (https://github.com/SWIFTSIM/SWIFT) on AMD Strix Halo hardware.

## Hardware Reality Check

| Component | Status | Implication |
|-----------|--------|-------------|
| **AMD GPU (gfx1151)** | ❌ Not supported by SWIFT | Only experimental CUDA exists, no HIP/OpenCL |
| **CPU (Zen 5, 16 cores)** | ✅ Fully supported | MPI + OpenMP parallelism available |
| **RAM (128GB UMA)** | ✅ Excellent | Large particle counts feasible |
| **NPU (XDNA2)** | ❌ Irrelevant | Not used for cosmological sims |

**Verdict**: Run SWIFT in **CPU-only mode** with MPI parallelism.

## SWIFT Overview

**What it is**: Smoothed Particle Hydrodynamics (SPH) + N-body gravity code
**Scales to**: 10,000+ cores on HPC clusters
**Use cases**: Galaxy formation, cosmology, planetary dynamics
**Algorithm**: 
- SPH for gas hydrodynamics
- Tree-based gravity (Barnes-Hut or FMM)
- Task-based parallelism

## Dependencies Check

### Required (from research):
- ✅ **MPI**: OpenMPI available (`mpicc` in PATH)
- ✅ **HDF5**: Parallel HDF5 available (`pkg-config hdf5`)
- ✅ **FFTW**: For periodic gravity
- ✅ **GSL**: For cosmological integration
- ⚠️ **METIS/ParMETIS**: Domain decomposition
- ✅ **Libtool**: Build system

### Optional:
- ❌ **CUDA**: Not available/usable
- ❌ **Grackle**: Cooling library
- ❌ **HEALPix**: For lightcone outputs

## Build Plan

### Step 1: Clone SWIFT
```bash
cd /tmp
git clone https://github.com/SWIFTSIM/SWIFT
cd SWIFT
```

### Step 2: Configure (CPU-only)
```bash
./autogen.sh
./configure \
    --with-hydro=gadget2 \
    --enable-mpi \
    --disable-hand-vec \
    CC=mpicc
```

### Step 3: Build
```bash
make -j16  # Use 16 Zen 5 cores
```

Expected time: 30-60 minutes

## Configuration Options

### Hydro Schemes (choose one):
- `gadget2`: Standard SPH, stable
- `minimal`: Fast, testing only  
- `hopkins`: Pressure-entropy SPH
- `gizmo`: Meshless finite-mass

### Physics Modules:
- `--self-gravity`: N-body gravity
- `--hydro`: Gas dynamics
- `--stars`: Star formation
- `--cooling`: Radiative cooling

## Test Simulation Plan

### Example 1: Isolated Galaxy (small)
```bash
# Get example data
cd examples/IsolatedGalaxy

# Run with 4 MPI ranks
mpirun -np 4 ./swift \
    --self-gravity \
    --hydro \
    IsolatedGalaxy.yml
```

**Particle count**: ~10,000
**Runtime**: ~minutes
**Output**: HDF5 snapshots

### Example 2: Cosmological Box (medium)
```bash
# Requires downloading ICs (initial conditions)
cd examples/SmallCosmoVolume

# Run
mpirun -np 16 ./swift \
    --self-gravity \
    --hydro \
    --cooling \
    --cosmology \
    small_cosmo.yml
```

**Particle count**: ~100,000
**Runtime**: ~hours
**Physical box**: ~10 Mpc/h

## Performance Expectations

### On AMD Strix Halo (16-core Zen 5):

| Simulation Size | Cores | Particles | Time/Step | Est. Total |
|----------------|-------|-----------|-----------|------------|
| Small test | 4 | 10K | ~0.1s | Minutes |
| Medium | 16 | 100K | ~1s | Hours |
| Large | 16 | 1M | ~10s | Days |

**Note**: Without GPU acceleration, this is purely CPU-bound.

## Integration with Cohezion/FLUME

### Option A: Post-process with FLUME
```python
# After SWIFT simulation
# Load HDF5 snapshots into FLUME VAE
# Analyze latent structure of galaxy formation
```

### Option B: Coupled Simulation (Future)
```python
# FLUME agents influence SWIFT ICs
# SWIFT outputs feed FLUME journey tracking
# Iterative universe generation
```

### Option C: Generate Training Data
- Run parameter sweep of SWIFT simulations
- Use outputs to train FLUME on cosmological structures
- Latent space = compressed representation of universes

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Build fails | Medium | Use released version (v2026.01), not master |
| Out of memory | Low | Test with small particle counts first |
| Slow performance | High | Expected - no GPU acceleration |
| IC files missing | Medium | Download from SWIFT website |
| HDF5 compatibility | Low | Use parallel HDF5 already installed |

## Success Criteria

1. SWIFT compiles successfully
2. Run IsolatedGalaxy example to completion
3. Output valid HDF5 snapshot files
4. Optional: Visualize with yt or ParaView

## Next Steps

1. **Confirm**: Proceed with CPU-only build?
2. **Scope**: Small test (Isolated Galaxy) or larger cosmology?
3. **Integration**: How to connect with FLUME/Cohezion after?

---

**Ready to proceed**: Can start build immediately (~1 hour).
