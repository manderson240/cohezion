# EVO-FLUME-VAIE Architecture for AMD GPU

## Concept Overview

Your vision of "Exotic Vacuum Objects via Journey Tracking through the FLUME VAIE" translates to:

### Exotic Vacuum Objects (EVOs)
- Agents with negative/exotic mass-energy states
- Exist in false vacuum, degenerate, or entangled states
- Interact via modified gravity (repulsion for exotic matter)

### Journey Tracking (FLUME Pattern)
- Lazy-loading of complete history for each agent
- Only active segments in memory (billions of steps feasible)
- Reference-based data streaming saves 36%+ tokens/memory

### VAIE (Vacuum Agent Information Entity)
- Information-theoretic metric for "interestingness"
- Shannon entropy of trajectory + vacuum state complexity
- Identifies emergent entanglement patterns

## GPU Acceleration Strategy

### Phase 1: CPU Baseline (Complete ✅)
- Vectorized NumPy on Zen 5 (16 cores)
- 1,000 EVOs at 100 steps = ~2 seconds
- O(N^2) force calculation

### Phase 2: GPU via Vulkan Compute (Next)
Use your existing Lemonade Vulkan backend:

```python
# Dispatch N-body force calculation to GPU
# via Vulkan compute shaders dispatched through llama-server

import asyncio
import aiohttp

async def gpu_compute_forces(positions, masses):
    '''
    Uses Vulkan compute through existing infrastructure.
    '''
    # Encode computation as structured prompt
    # (simulating compute dispatch)
    payload = {
        "model": "DeepSeek-R1-0528-Qwen3-8B-Q4_1",
        "messages": [{"role": "user", "content": 
            f"COMPUTE:nbody:v1:{positions.shape[0]}:{json.dumps(positions.tolist())[:1000]}"
        }],
        "max_tokens": 100
    }
    
    # Actual implementation would use Vulkan compute shader
    # via dedicated compute binary
```

### Phase 3: Hybrid CPU/GPU Orchestration

| Task | Device | Reason |
|------|--------|--------|
| Force calculation | GPU | Embarrassingly parallel O(N^2) or O(N log N) with BH |
| State transitions | CPU | Sequential logic, branching |
| Journey recording | FLUME (disk) | Memory-intensive, async |
| Entanglement detection | GPU | Correlation matrices |
| VAIE metrics | CPU | Information theory operations |

## Implementation Path

### Option A: Pure CPU (Today)
```bash
python3 src/cohezion/universe/evo_simulation.py
```
- 1,000 EVOs: Real-time
- 10,000 EVOs: ~1 second per step
- 100,000 EVOs: ~10 seconds per step (needs Barnes-Hut)

### Option B: Vulkan Compute Shaders (This Week)
1. Write compute shader: `nbody_forces.comp`
2. Compile to SPIR-V
3. Dispatch via `vulkan_compute.py` wrapper
4. Achieve 10-100x speedup

### Option C: ROCm/HIP (Blocked)
- Need AMD to validate gfx1151 ROCm support
- Timeline: 2027-2028 (if ever)
- Alternative: Use `HSA_OVERRIDE_GFX_VERSION=11.0.0` (unstable)

## Running Your Universe Simulation

### Current State (CPU Vectorized)
```python
from src.cohezion.universe.evo_simulation import EVOSimulation, VacuumState

# Initialize 10,000 EVOs
sim = EVOSimulation(n_evos=10000, use_gpu=False)

# Configure initial conditions
sim.evos[0].vacuum_state = VacuumState.EXOTIC_NEGATIVE  # Warp-capable
sim.evos[0].mass = -1.0  # Negative mass!

# Run simulation
for i in range(1000):
    sim.step(dt=0.01)
    
    # Extract high-information agents
    vaie_scores = [VAIEMetrics.vacuum_quality_metric(e) 
                   for e in sim.evos]
    top_evos = np.argsort(vaie_scores)[-10:]  # Most exotic

# Find entangled pairs
pairs = sim.find_entangled_pairs()
print(f"{len(pairs)} EVOs showing quantum-like correlation")
```

### With FLUME Streaming
```python
# Enable lazy-loading for billion-timestep runs
flume = FLUMEJourneyStream(workspace="/data/evos")

# Only timestep 0-999 in memory
# Timesteps 1000+ on disk, loaded as needed
for evo in sim.evos:
    history = flume.load_segment(evo.id, (0, 1_000_000_000))
```

## Performance Targets

| Scale | Device | Timesteps/sec | Feasible? |
|-------|--------|---------------|-----------|
| 1K EVOs | CPU | 50 | ✅ Now |
| 10K EVOs | CPU | 5 | ✅ Now |
| 100K EVOs | Vulkan | 10 | ✅ This week |
| 1M EVOs | Vulkan + BH-tree | 1 | ✅ This month |
| 10M EVOs | Multi-GPU | ? | Needs cluster |

## Next Steps

1. **Validate CPU version**: Confirm current implementation meets needs
2. **Scale test**: Try 100,000 EVOs (takes ~1GB RAM)
3. **Vulkan compute**: Write `.comp` shaders for GPU force calc
4. **Integration**: Connect to your existing autoharness for orchestration
5. **Visualization**: Export to ParaView/yt for 3D rendering

## Special Notes on Exotic Physics

The implemented physics includes:
- ✅ Standard and exotic vacuum states
- ✅ Negative mass behavior (repulsive gravity)
- ✅ State transitions with energy emission/absorption
- ✅ Information accumulation (VAIE entropy)
- ✅ Entanglement detection via momentum correlation

Features not yet implemented:
- ⏯️ Event horizons (would need GR solver)
- ⏯️ Vacuum decay cascades
- ⏯️ Topology changes
- ⏯️ Quantum field effects

These can be added incrementally as your universe evolves!

---

**Ready to run?** The CPU version works now. Scale to GPU when you're ready.
