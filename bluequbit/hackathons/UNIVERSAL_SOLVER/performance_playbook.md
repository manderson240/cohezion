# BlueQubit Universal Winning Playbook
**Version:** 1.0  
**Purpose:** Reusable winning strategies for ANY BlueQubit hackathon  
**Status:** Field-tested and ready

---

## Core Philosophy

**"Win by systematic execution, not clever tricks"**

Based on Little Dimple success (SNR 9,947 sigma):
1. **Reproduce first** - Get working baseline
2. **Instrument everything** - Measure, don't guess
3. **Optimize systematically** - Tune one parameter at a time
4. **Validate constantly** - Check results at each step

---

## Challenge Type Quick Reference

### Type 1: Peaked Circuit (Heavy Output)
**Signature:** "Find heavy output", "Peaked distribution", "Dominant bitstring"

**Strategy:**
```python
# 1. Submit with HIGH shots
shots = 100000  # High statistics

# 2. Detect heavy output
from heavy_output_detection import find_heavy_output
heavy = find_heavy_output(counts, threshold=0.5)

# 3. Calculate SNR
top_bitstring = max(heavy.items(), key=lambda x: x[1])
snr = calculate_snr(top_bitstring[1], n_qubits)

# 4. Validate
assert snr > 2.0, "Low SNR - increase shots"
```

**Bond Dimension:**
- ≤10 qubits: 64
- 11-20 qubits: 128
- 21-30 qubits: 256
- 31+ qubits: 512

**Shots:**
- Always use shots for >17 qubits
- Start with 100000, adjust based on SNR

---

### Type 2: VQA/VQE (Optimization)
**Signature:** "Minimize energy", "Ground state", "Optimize parameters"

**Strategy:**
```python
# 1. Build shallow ansatz (avoid barren plateaus)
depth = 2  # Keep shallow
qc = variational_circuit(n_qubits, depth)

# 2. Use Pennylane for optimization
dev = qml.device("bluequbit.cpu", wires=n)
@qml.qnode(dev)
def circuit(params):
    for i in range(n):
        qml.RY(params[i], wires=i)
    return qml.expval(H)

# 3. Optimize with scipy
from scipy.optimize import minimize
result = minimize(circuit, initial_params, method="COBYLA")
```

**Key Insights:**
- Depth > 4 often hits barren plateaus
- Use gradient-free optimizers (COBYLA, SPSA)
- Start with good initial parameters
- Monitor for convergence

---

### Type 3: QAOA (MaxCut)
**Signature:** "Maximize cut", "Graph partition", "Combinatorial optimization"

**Strategy:**
```python
# 1. Define graph
edges = [(0,1), (1,2), (2,3), (0,3)]

# 2. QAOA circuit
def qaoa_circuit(gamma, beta):
    for i in range(n):
        qml.Hadamard(i)
    for u, v in edges:
        qml.CNOT(u, v)
        qml.RZ(gamma, v)
        qml.CNOT(u, v)
    for i in range(n):
        qml.RX(2*beta, i)

# 3. Optimize gamma and beta
```

**Key Insights:**
- p=1 QAOA often sufficient for small graphs
- Classical optimization critical
- Parameter initialization matters

---

### Type 4: State Preparation
**Signature:** "Prepare GHZ", "Create W-state", "Bell state"

**Strategy:**
```python
# Use pre-built circuits
from circuit_library import CircuitLibrary
lib = CircuitLibrary()

# For statevector
qc = lib.ghz_state(n_qubits)  # No measurement!
result = bq.run(qc, device="mps.cpu")  # shots=0
statevector = result.get_statevector()

# For sampling
qc.measure_all()
result = bq.run(qc, device="mps.cpu", shots=10000)
counts = result.get_counts()
```

---

## Universal Tuning Guide

### Bond Dimension Selection

| Qubits | Recommended χ | Rationale |
|--------|---------------|-----------|
| ≤10 | 64 | Fast, sufficient |
| 11-20 | 128 | Balance speed/accuracy |
| 21-30 | 256 | Higher entanglement |
| 31-40 | 512 | Maximum accuracy |
| >40 | 512+ | May need GPU |

**Validation:**
- Increase χ until results converge
- If χ=512 still changing, use higher
- Trade-off: higher χ = slower runtime

### Shots Selection

| Challenge Type | Shots | Rationale |
|----------------|-------|-----------|
| Peaked circuit | 100000 | High statistics for SNR |
| VQA | 1024 | Balance speed/noise |
| QAOA | 10000 | Good expectation values |
| State prep | 10000 | Sampling quality |

**Rule:** Always use shots for circuits >17 qubits

---

## Failure Recovery Guide

### Issue: "No results returned"
**Cause:** shots=0 with small circuits  
**Fix:**
```python
shots = 100 if circuit.num_qubits <= 17 else 10000
result = bq.run(qc, device="mps.cpu", shots=shots)
```

### Issue: "Too many qubits for MPS"
**Cause:** >17 qubits without shots  
**Fix:** Always use shots parameter

### Issue: "Statevector not available"
**Cause:** Ran with measurement + shots > 0  
**Fix:** Remove measurement gates

### Issue: "Job failed validation"
**Cause:** 25+ qubits without shots  
**Fix:** Add shots=1024 minimum

### Issue: "403 Forbidden" for get_peaked_circuit
**Cause:** Challenge not active or no access  
**Fix:** Wait for challenge start or build circuit manually

---

## Time Management Strategy

### 3-Day Hackathon Timeline

**Day 1: Foundation (4-6 hours)**
- [ ] Connect and test SDK
- [ ] Classify challenge type
- [ ] Get first working result
- [ ] Set up monitoring

**Day 2: Optimization (6-8 hours)**
- [ ] Tune bond dimension
- [ ] Optimize shots
- [ ] Try multiple strategies
- [ ] Performance profiling

**Day 3: Refinement (4-6 hours)**
- [ ] Final validation
- [ ] Backup submissions
- [ ] Submit best result
- [ ] Monitor leaderboard

### During Challenge

**First Hour:**
1. Read challenge rules carefully
2. Identify challenge type
3. Get working baseline (any result)
4. Set up monitoring

**Hours 2-8:**
- Iterative optimization
- Test different parameters
- Document findings
- Save checkpoints

**Hours 9-24:**
- Fine-tuning
- Multiple attempts
- Compare strategies
- Prepare final submission

---

## Debugging Checklist

### Before Submitting
- [ ] Circuit validated (test with small version)
- [ ] Shots parameter set (especially if >17 qubits)
- [ ] Bond dimension appropriate
- [ ] Results make sense (sanity check)
- [ ] Submission logged
- [ ] Backup created

### Common Mistakes
- [ ] Using shots=0 for small circuits (returns empty)
- [ ] Forgetting shots for >17 qubits (fails validation)
- [ ] Measuring then trying to get statevector
- [ ] Too deep circuits for VQA (barren plateaus)
- [ ] Insufficient shots for peaked circuits

---

## Performance Benchmarks

### Expected Runtimes (mps.cpu)

| Qubits | Depth | Shots | Expected Time |
|--------|-------|-------|---------------|
| 2 | 5 | 1024 | 6-7s |
| 10 | 10 | 10000 | 18-20s |
| 20 | 20 | 10000 | 40-50s |
| 30 | 30 | 10000 | 60-80s |

**Red Flags:**
- >120s for <20 qubits → check bond dimension
- <2s for >10 qubits → may be using shots=0
- Timeout after 300s → reduce shots or bond dim

---

## Reusable Code Modules

### Module 1: Universal Solver
```python
from universal_solver import UniversalSolver

solver = UniversalSolver(challenge_id="xyz")
result = solver.auto_solve(circuit=qc, description="Find heavy output")
```

### Module 2: Heavy Output Detection
```python
from heavy_output_detection import detect_heavy_output

result = detect_heavy_output(qc, shots=100000, threshold=0.5)
print(f"Heavy output: {result['top_bitstring']}")
print(f"SNR: {result['snr_sigma']:.2f} sigma")
```

### Module 3: Circuit Library
```python
from circuit_library import CircuitLibrary

lib = CircuitLibrary()
qc = lib.ghz_state(20)  # Pre-built optimized circuits
```

### Module 4: Job Monitor
```python
from job_monitor import JobMonitor

monitor = JobMonitor()
monitor.add_job(job_id, device, n_qubits, shots)
monitor.print_dashboard()
```

---

## Skill Transfer Guide

### From Little Dimple → Any Peaked Challenge

**Transferable:**
- ✓ Heavy output detection algorithm
- ✓ SNR calculation
- ✓ Bond dimension scaling
- ✓ High-shot strategy
- ✓ SETI protocol

**Adapt:**
- Number of qubits
- Circuit connectivity
- Shots count
- Threshold value

### From VQA → QAOA

**Transferable:**
- ✓ Variational circuit structure
- ✓ Optimization framework
- ✓ Parameter initialization
- ✓ Convergence monitoring

**Adapt:**
- Cost function
- Mixer Hamiltonian
- Problem encoding

---

## Advanced Tactics

### Tactic 1: Parallel Submissions
```python
# Submit multiple parameter sets simultaneously
from concurrent.futures import ThreadPoolExecutor

def submit_with_params(params):
    return bq.run(circuit, **params)

param_sets = [
    {"shots": 10000, "bond_dimension": 64},
    {"shots": 100000, "bond_dimension": 128},
    {"shots": 50000, "bond_dimension": 256},
]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(submit_with_params, param_sets))
```

### Tactic 2: Adaptive Optimization
```python
# Start coarse, refine fine
for bond_dim in [32, 64, 128, 256]:
    result = bq.run(qc, options={"mps_bond_dimension": bond_dim})
    if converged(result):
        break
```

### Tactic 3: Checkpoint Recovery
```python
import json

# Save every 300s
checkpoint = {
    "config": config.__dict__,
    "best_result": best_result,
    "timestamp": time.time()
}

with open("checkpoint.json", "w") as f:
    json.dump(checkpoint, f)
```

---

## Meta-Learning

### What We Learned from Little Dimple

1. **MPS is powerful** - 36 qubits on CPU
2. **Manual routing essential** - For non-local gates
3. **High shots matter** - 250k for statistical significance
4. **Renormalization critical** - Every 50 gates
5. **Verification required** - Mapping can scramble bits

### What to Expect in New Challenges

**Likely patterns:**
- Higher qubit counts (40+)
- Different connectivity (2D, all-to-all)
- Time-constrained optimization
- Multiple objectives

**Preparation:**
- Test higher bond dimensions
- Practice Pauli-path device
- Benchmark GPU vs CPU
- Prepare adaptive strategies

---

## Emergency Protocols

### If SDK Fails
1. Check token validity
2. Verify network connectivity
3. Try simpler circuit
4. Check BlueQubit status page
5. Contact info@bluequbit.io

### If Results Don't Make Sense
1. Validate circuit with visualization
2. Check shots parameter
3. Verify bond dimension
4. Test with known circuit (GHZ)
5. Compare with classical simulation

### If Running Out of Time
1. Use default parameters (bond_dim=128, shots=10000)
2. Submit current best result
3. Don't chase perfection
4. Document what you tried
5. Prepare explanation

---

## Success Metrics

### Before Challenge
- [ ] SDK connectivity verified
- [ ] All templates tested
- [ ] Strategy selected
- [ ] Monitoring configured
- [ ] Backup plan ready

### During Challenge
- [ ] First result within 1 hour
- [ ] Multiple attempts logged
- [ ] Parameters documented
- [ ] Convergence verified
- [ ] Final submission validated

### After Challenge
- [ ] Results saved
- [ ] Skills captured
- [ ] Lessons learned documented
- [ ] Playbook updated
- [ ] Next challenge prepared

---

## Quick Reference Card

### Essential Imports
```python
import bluequbit
import qiskit
from circuit_library import CircuitLibrary
from heavy_output_detection import detect_heavy_output
```

### Quick Circuit Test
```python
bq = bluequbit.init()
qc = CircuitLibrary().ghz_state(10)
result = bq.run(qc, device="mps.cpu", shots=10000)
counts = result.get_counts()
```

### Heavy Output Quick
```python
result = detect_heavy_output(qc, shots=100000)
print(result['top_bitstring'])
```

### Emergency Fallback
```python
# If all else fails, try this
qc = qiskit.QuantumCircuit(n)
qc.h(0)
for i in range(n-1):
    qc.cx(i, i+1)
qc.measure_all()
result = bq.run(qc, device="mps.cpu", shots=10000)
```

---

## Version History

**v1.0** (2026-04-01)
- Initial playbook based on Little Dimple success
- Universal strategies for peaked, VQA, QAOA
- Performance benchmarks
- Failure recovery guide

---

**Maintained by:** BMad Master  
**Status:** Field-tested  
**Confidence:** HIGH

**END OF PLAYBOOK**
