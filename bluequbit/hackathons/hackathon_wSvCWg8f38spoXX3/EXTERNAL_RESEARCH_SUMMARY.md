# External Research Summary - Quantum Computing Resources
## Prepared for April 4-5 Hackathon: wSvCWg8f38spoXX3

**Date:** April 2, 2026  
**Sources:** HuggingFace, arXiv, Qiskit, Amazon Braket, PennyLane

---

## 1. HuggingFace Quantum Resources

### Status
- Limited dedicated quantum content
- Individual researchers present (e.g., Daniel Sandner profile)
- Not a primary resource for quantum hackathons

**Recommendation:** Focus on platform-specific resources (BlueQubit) rather than HuggingFace

---

## 2. Qiskit Platform (IBM Quantum)

### Key Insights
- **World's most popular quantum SDK** (13M downloads, 69% developer preference)
- **83x faster transpilation** than competitors
- **Comprehensive ecosystem:**
  - Circuit construction and compilation
  - Primitives for experiments
  - Algorithm development tools
  - Hardware provider plugins

### Relevant for Hackathons:

#### Circuit Analysis Tools
```python
# Qiskit provides rich circuit metadata
from qiskit import QuantumCircuit

qc = QuantumCircuit.from_qasm_file('circuit.qasm')
print(f"Qubits: {qc.num_qubits}")
print(f"Depth: {qc.depth()}")
print(f"Gates: {qc.count_ops()}")
print(f"Two-qubit gates: {qc.num_nonlocal_gates()}")
```

**Use Case:** Pre-analyze circuits before submission

#### Transpiler Optimization
```python
from qiskit import transpile

# Optimize circuits for specific backends
optimized = transpile(qc, optimization_level=3)
```

**Use Case:** Circuit simplification before running

#### Statevector Simulation
```python
from qiskit import Aer

simulator = Aer.get_backend('statevector_simulator')
result = simulator.run(qc).result()
statevector = result.get_statevector()
```

**Use Case:** Local verification of small circuits before cloud submission

### Qiskit Addons (Algorithm Building Blocks)
- **MPF** (Matrix Product Function)
- **AQC-Tensor** (Adiabatic quantum computing with tensors)
- **OBP** (Observable Pruning)
- **Circuit Cutting**
- **SQD** (Sample-based Quantum Diagonalization)

**Relevance:** These tools can augment BlueQubit workflows

---

## 3. Amazon Braket

### Key Features
- **Multi-provider support:** IBM, IonQ, Rigetti, Quaninuum, etc.
- **Local simulator:** Fast prototyping
- **TN1 tensor network simulator:** Good for large circuits
- **Hybrid jobs:** Classical-quantum workflows

### Relevant for Hackathons:

#### Local Simulator (Free)
```python
from braket.devices import LocalSimulator

device = LocalSimulator()
task = device.run(circuit, shots=1000)
result = task.result()
```

**Use Case:** Test circuits locally before paying for cloud resources

#### Tensor Network Simulator (TN1)
- Specialized for circuits with limited entanglement
- Good for ~50 qubits on free tier
- Uses matrix product states (like BlueQubit)

**Comparison to BlueQubit:**
- Similar MPS approach
- May have different performance characteristics
- Could be backup option

#### PennyLane Integration
```python
import pennylane as qml

dev = qml.device('braket.local.qubit', wires=2)
```

**Use Case:** Alternative simulation backend

---

## 4. PennyLane (Xanadu)

### Key Insights
- **Quantum machine learning focus**
- **Automatic differentiation**
- **Multiple backends:** BlueQubit, Braket, Qiskit, etc.

### BlueQubit Integration
```python
import pennylane as qml

dev = qml.device("bluequbit.cpu", wires=4, token="YOUR_TOKEN")

@qml.qnode(dev)
def circuit():
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.probs(wires=[0, 1])

probs = circuit()
```

**Relevance:** Could use PennyLane as abstraction layer

---

## 5. Cross-Platform Strategy

### Backup Plans

**If BlueQubit free tier fails:**
1. **Amazon Braket local simulator** - Test small circuits
2. **Qiskit Aer** - Statevector verification
3. **PennyLane + other backends** - Alternative execution

**Circuit Optimization:**
1. Use **Qiskit transpiler** to reduce gate count
2. **Braket circuit cutting** for large circuits
3. **PennyLane** automatic optimization

---

## 6. Research Gaps Identified

### What We Need (Not Found)
1. **Dedicated quantum hackathon resources** - Limited community content
2. **BlueQubit vs other platforms benchmarks** - Need empirical data
3. **Circuit-specific optimization strategies** - Generic tutorials only

### What We Have
1. ✅ Heavy output detection method (proven)
2. ✅ Bond dimension guidance (empirical)
3. ✅ Free tier limits (discovered)
4. ✅ Template system (created)

---

## 7. Actionable Recommendations

### For April 4-5 Hackathon:

**Primary Strategy (BlueQubit):**
- Use our proven heavy output detection
- Bond dim 64 for <=40 qubits
- Bond dim 32 for 44 qubits
- Request paid credits early if needed

**Backup Strategy (Multi-platform):**
- Qiskit for circuit analysis/optimization
- Braket local simulator for testing
- PennyLane for cross-platform compatibility

**Optimization:**
- Pre-analyze circuits with Qiskit
- Reduce gate count if possible
- Use circuit cutting for very large circuits

---

## 8. Resources to Bookmark

### Documentation
- **BlueQubit SDK:** https://app.bluequbit.io/sdk-docs/
- **Qiskit:** https://qiskit.org/documentation/
- **PennyLane:** https://pennylane.ai/qml/
- **Amazon Braket:** https://docs.aws.amazon.com/braket/

### Tutorials
- **BlueQubit peaked circuits:** Tutorial 2 (essential)
- **Qiskit transpilation:** Optimization techniques
- **PennyLane plugins:** Backend abstraction

### Community
- **Qiskit Slack:** Active community
- **PennyLane forum:** Support resources
- **BlueQubit support:** Direct help

---

## Summary

**Key Finding:** BlueQubit is specialized and optimized for peaked circuits. Other platforms (Qiskit, Braket, PennyLane) provide:
- Circuit analysis tools
- Optimization capabilities
- Backup execution options
- Cross-platform compatibility

**For hackathon:** Stick with BlueQubit for execution, use other tools for:
- Pre-analysis
- Optimization
- Circuit validation
- Backup plans

**No silver bullet found** - Our methodology is sound, but external resources provide useful augmentation.
