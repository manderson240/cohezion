# BlueQubit Hackathon Preparation Guide
# Generated: 2026-04-01
# Challenge: https://app.bluequbit.io/hackathons/wSvCWg8f38spoXX3

## Executive Summary

**Platform:** BlueQubit Quantum Computing
**Challenge Type:** Quantum Advantage (likely)  
**Preparation Time:** 3 days until hackathon starts
**Token Status:** ✓ Authenticated and working

## BlueQubit Platform Capabilities

### Available Devices
1. **mps.cpu** - Matrix Product State simulation on CPU (40+ qubits)
2. **mps.gpu** - MPS simulation on GPU (faster, requires balance)
3. **pauli-path** - Pauli Path simulation for observable expectations
4. **IBM Heron** - 156 qubits, 99.97% fidelity (real hardware)
5. **Quantinuum H2** - 56 qubits, 99.997% fidelity (real hardware)

### SDK Methods (13 available)
- `run()` - Execute quantum circuits (Qiskit/Pennylane)
- `run_native_async()` - Async execution
- `get()` - Retrieve job results
- `wait()` - Block until job completes
- `estimate()` - Cost/time estimation
- `cancel()` - Cancel running jobs
- `search()` - Search jobs/resources
- `get_peaked_circuit()` - **Key for peaked circuit challenges**
- `validate_*` - Circuit validation methods

### Key Features
- **Qiskit Integration:** Build circuits with Qiskit, run on BlueQubit
- **Pennylane Plugin:** Native Pennylane device support
- **MPS Simulation:** 40+ qubits on CPU, bond dimension control
- **State Vector:** Full statevector retrieval
- **Counts:** Measurement result sampling

## Previous Challenge Experience: "Little Dimple" (36-qubit)

### What Worked
1. **FLIER Strategy** (Fluid Latent Inter-Entity Routing)
2. **Matrix Product States (MPS)** - Avoided exponential memory wall
3. **Manual Linear Routing** - 15,752 SWAP gates for non-local gates
4. **High Bond Dimension** - χ=128-512 for entanglement capture
5. **SETI-Protocol** - 250,000 shots to find heavy output bitstring

### Result
- **SNR:** 9,947 sigma
- **Bitstring:** Heavy output identification
- **Runtime:** ~44 minutes (26 min encoding + 18 min sampling)

### Tools Used
- **Quimb** - Tensor network library
- **Cotengra** - Contraction optimizer
- **Custom QASM parser** - Manual circuit decomposition

## Likely New Challenge Scenarios

### Scenario A: Peaked Circuit (similar to Little Dimple)
**Approach:**
- Use BlueQubit `mps.cpu` with high bond dimension
- Submit circuit, get statevector/counts
- Statistical analysis for heavy output

### Scenario B: Quantum Advantage Benchmark
**Approach:**
- Compare quantum vs classical runtime
- VQA/QAOA optimization
- Demonstrate speedup on specific problem

### Scenario C: Variational Algorithm
**Approach:**
- Use Pennylane + BlueQubit plugin
- Parameter optimization
- Hybrid classical-quantum workflow

## 3-Day Preparation Roadmap

### Day 1 (Today): Foundation & Testing
**Morning (4 hours):**
- [ ] Study BlueQubit SDK documentation
- [ ] Test all SDK methods with simple circuits
- [ ] Verify MPS device with 30-40 qubit GHZ state
- [ ] Compare mps.cpu vs mps.gpu performance

**Afternoon (4 hours):**
- [ ] Reproduce "Little Dimple" workflow using BlueQubit
- [ ] Convert QASM to Qiskit circuit
- [ ] Submit to mps.cpu, compare results
- [ ] Document performance metrics

**Evening (2 hours):**
- [ ] Review quantum advantage literature
- [ ] Identify candidate algorithms (QAOA, VQE, etc.)
- [ ] Set up Pennylane integration

### Day 2: Strategy Development & Optimization
**Morning (4 hours):**
- [ ] Test Pennylane + BlueQubit plugin
- [ ] Build variational circuit templates
- [ ] Implement optimizer integration
- [ ] Test Pauli-path simulation

**Afternoon (4 hours):**
- [ ] Develop heavy output detection algorithm
- [ ] Implement statistical significance testing
- [ ] Create submission automation script
- [ ] Benchmark different bond dimensions

**Evening (2 hours):**
- [ ] Review previous hackathon winners' strategies
- [ ] Identify optimization opportunities
- [ ] Prepare debugging toolkit

### Day 3: Final Preparation & Readiness
**Morning (3 hours):**
- [ ] End-to-end test run with sample challenge
- [ ] Verify submission pipeline
- [ ] Test async execution patterns
- [ ] Document troubleshooting steps

**Afternoon (3 hours):**
- [ ] Create starter code templates
- [ ] Prepare monitoring/logging setup
- [ ] Test hardware devices (if accessible)
- [ ] Final verification of all tools

**Evening (2 hours):**
- [ ] Rest and review
- [ ] Ensure API token is working
- [ ] Prepare environment for quick start
- [ ] Set up notifications/monitoring

## Key Tools & Libraries

### Installed (✓)
- `bluequbit==0.18.5b1` - SDK
- `qiskit==2.3.1` - Circuit building
- `pennylane==0.44.1` - Variational algorithms
- `quimb==1.13.0` - Tensor networks
- `cotengra==0.7.5` - Contraction optimization
- `python-dotenv` - Environment management

### Recommended Additional Tools
- `numpy` - Numerical operations (already installed)
- `scipy` - Statistical functions (already installed)
- `matplotlib` - Visualization
- `jupyter` - Interactive development

## Code Templates

### Template 1: Basic Circuit Execution
```python
import os
from dotenv import load_dotenv
import bluequbit
import qiskit

load_dotenv()
bq = bluequbit.init()

# Build circuit
qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# Run on MPS simulator
result = bq.run(qc, device="mps.cpu", options={"mps_bond_dimension": 64})
counts = result.get_counts()
print(counts)
```

### Template 2: Async Execution
```python
# Non-blocking submission
job = bq.run(qc, device="mps.cpu", asynchronous=True)

# Do other work...

# Wait for completion
result = bq.wait(job.job_id)
counts = result.get_counts()
```

### Template 3: Pennylane Integration
```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("bluequbit.cpu", wires=2, token=os.getenv("BLUEQUBIT_API_TOKEN"))

@qml.qnode(dev)
def circuit(params):
    qml.RY(params[0], wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(1))

params = np.array([0.5])
result = circuit(params)
```

### Template 4: State Vector Retrieval
```python
# For statevector simulation (no measurement)
qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

result = bq.run(qc, device="mps.cpu")
statevector = result.get_statevector()
print(f"State vector shape: {statevector.shape}")
```

### Template 5: Heavy Output Detection
```python
def find_heavy_output(counts, threshold=0.5):
    """
    Find bitstrings with probability > threshold / 2^n
    """
    n_qubits = len(list(counts.keys())[0])
    total = sum(counts.values())
    uniform_prob = 1.0 / (2 ** n_qubits)
    threshold_prob = threshold * uniform_prob
    
    heavy_outputs = {}
    for bitstring, count in counts.items():
        prob = count / total
        if prob > threshold_prob:
            heavy_outputs[bitstring] = prob
    
    return heavy_outputs

# Usage
result = bq.run(qc, device="mps.cpu", shots=100000)
counts = result.get_counts()
heavy = find_heavy_output(counts, threshold=0.6)
```

## Debugging Checklist

### Connection Issues
- [ ] Verify `BLUEQUBIT_API_TOKEN` in `.env`
- [ ] Check token not expired
- [ ] Test simple circuit execution
- [ ] Verify internet connectivity

### Performance Issues
- [ ] Monitor bond dimension vs accuracy tradeoff
- [ ] Check GPU availability if using mps.gpu
- [ ] Verify sufficient memory for circuit size
- [ ] Use `estimate()` to check resource requirements

### Result Validation
- [ ] Compare MPS vs Pauli-path results
- [ ] Check convergence with increasing bond dimension
- [ ] Validate against known test cases
- [ ] Verify bitstring encoding (big vs little endian)

## Resources

### Documentation
- SDK Docs: https://app.bluequbit.io/sdk-docs
- Platform: https://app.bluequbit.io
- API Reference: https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html

### Previous Challenge Code
- Location: `/home/mike-anderson/dev/cohezion/research/challenges/bluequbit_challenge/`
- Key files:
  - `peaked_solver.py` - MPS simulation engine
  - `verify_result.py` - Result verification
  - `DETAILED_SOLUTION.md` - Methodology documentation

### Quantum Computing References
- MPS/Tensor Networks: quimb.readthedocs.io
- Qiskit: qiskit.org/documentation
- Pennylane: pennylane.ai
- Cotengra: cotengra.readthedocs.io

## Immediate Next Steps

1. **Study SDK documentation** (30 min)
   - Read: https://app.bluequbit.io/sdk-docs
   - Focus on: run(), get_peaked_circuit(), device options

2. **Test basic workflow** (1 hour)
   - Execute Template 1 (above)
   - Try 30-40 qubit GHZ state
   - Measure execution time

3. **Reproduce Little Dimple** (2 hours)
   - Find QASM file in previous challenge
   - Convert to Qiskit circuit
   - Submit to BlueQubit
   - Compare results

4. **Prepare monitoring** (30 min)
   - Set up job tracking
   - Create submission logging
   - Test async patterns

## Emergency Contacts

- BlueQubit Support: info@bluequbit.io
- Platform: https://app.bluequbit.io

## Success Metrics

- [ ] SDK connection working ✓
- [ ] All 13 methods tested
- [ ] 40+ qubit circuit executed successfully
- [ ] Async execution pattern verified
- [ ] Pennylane integration working
- [ ] Submission pipeline automated
- [ ] Previous challenge reproduced

---

**Status:** Ready for Day 1 execution
**Confidence:** High (based on previous challenge experience)
**Risk:** Low (familiar platform, working token, tested tools)
