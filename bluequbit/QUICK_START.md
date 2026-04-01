# BlueQubit Hackathon Quick Start Guide

**Challenge:** https://app.bluequbit.io/hackathons/wSvCWg8f38spoXX3  
**Starts:** In 3 days  
**Status:** Ready

---

## Quick Commands

### Test Connection
```bash
cd /home/mike-anderson/dev/cohezion/bluequbit
python3 -c "import bluequbit; bq = bluequbit.init(); print('✓ Connected')"
```

### Submit Test Circuit
```bash
cd hackathons/hackathon_wSvCWg8f38spoXX3/code_templates
python3 basic_circuit.py
```

### Monitor Jobs
```bash
python3 job_monitor.py
```

---

## Repository Map

```
bluequbit/
├── README.md                          # Overview
├── docs/
│   ├── bluequbit_hackathon_prep.md  # 3-day roadmap
│   ├── SDK_CRITICAL_FINDINGS.md     # Critical limitations
│   ├── DAY0_COMPLETION_REPORT.md    # Day 0 status
│   └── RESEARCH_SUMMARY_EXTERNAL.md # Research findings
├── hackathons/
│   ├── little_dimple/                # Previous challenge
│   └── hackathon_wSvCWg8f38spoXX3/  # Current challenge
│       ├── code_templates/           # Templates
│       │   ├── basic_circuit.py
│       │   ├── async_execution.py
│       │   ├── heavy_output_detection.py
│       │   ├── submission_pipeline.py
│       │   ├── circuit_library.py
│       │   ├── strategy_selector.py
│       │   ├── job_monitor.py
│       │   ├── bond_dimension_benchmark.py
│       │   └── sdk_complete_reference.py
│       └── tests/
│           └── test_sdk_methods.py
```

---

## Code Templates

### 1. Basic Circuit Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

result = bq.run(qc, device="mps.cpu")
print(result.get_counts())
```

### 2. Heavy Output Detection
```python
from code_templates.heavy_output_detection import detect_heavy_output

result = detect_heavy_output(qc, shots=100000, threshold=0.5)
print(f"Heavy output: {result['top_bitstring']}")
print(f"SNR: {result['snr_sigma']:.2f} sigma")
```

### 3. Submission Pipeline
```python
from code_templates.submission_pipeline import SubmissionPipeline

pipeline = SubmissionPipeline()
result = pipeline.submit_and_extract(qc, shots=100000)
```

### 4. Circuit Library
```python
from code_templates.circuit_library import CircuitLibrary

lib = CircuitLibrary()
qc = lib.ghz_state(20)  # or ghz_state, w_state, qft, etc.
```

### 5. Strategy Selector
```python
from code_templates.strategy_selector import StrategySelector

selector = StrategySelector()
challenge_type = selector.analyze_challenge(
    n_qubits=36,
    target="Find heavy output"
)
recommendation = selector.recommend_strategy(challenge_type, 36)
```

---

## Critical SDK Limitations

### MPS Qubit Limit
- **Limit:** 17 qubits for probabilities
- **Solution:** Always use shots for >17 qubits
```python
shots = 1024 if circuit.num_qubits > 17 else None
result = bq.run(qc, device="mps.cpu", shots=shots)
```

### State Vector Availability
- **Requires:** shots=0 (no measurement)
```python
# For statevector
qc = qiskit.QuantumCircuit(2)  # No measurement!
result = bq.run(qc, device="mps.cpu")
sv = result.get_statevector()

# For counts
qc.measure_all()
result = bq.run(qc, device="mps.cpu", shots=1024)
counts = result.get_counts()
```

---

## Device Selection Guide

| Device | Qubits | Speed | Cost | Best For |
|--------|--------|-------|------|----------|
| mps.cpu | 17 (prob) / 40+ (shots) | Medium | $0.00 | General use |
| mps.gpu | 40+ | Fast | $ | Large circuits |
| pauli-path | Any | Medium | $0.00 | Observable expectations |
| ibm.heron | 156 | Real | $$ | Hardware access |
| quantinuum.h2 | 56 | Real | $$ | Hardware access |

---

## Performance Benchmarks

**Timing (mps.cpu):**
- 2 qubits: ~6.6s
- 10 qubits: ~18.2s
- 20 qubits: Requires shots

**Cost Estimates:**
- Small circuits (<20 qubits): $0.00
- Large circuits: $0.20-$1.00

---

## Workflow Template

```python
# 1. Load credentials and initialize
from dotenv import load_dotenv
import bluequbit
import qiskit

load_dotenv()
bq = bluequbit.init()

# 2. Build circuit
qc = qiskit.QuantumCircuit(20)
qc.h(0)
for i in range(19):
    qc.cx(i, i+1)
qc.measure_all()

# 3. Set up options
shots = 1024  # Required for >17 qubits
options = {"mps_bond_dimension": 128}

# 4. Submit
try:
    result = bq.run(qc, device="mps.cpu", shots=shots, options=options)
    counts = result.get_counts()
    print(f"Success! {len(counts)} distinct states")
except Exception as e:
    print(f"Error: {e}")

# 5. Process results
from code_templates.heavy_output_detection import find_heavy_output
heavy = find_heavy_output(counts)
print(f"Heavy outputs: {heavy}")
```

---

## Common Issues & Solutions

### Issue 1: "Access denied for get_peaked_circuit"
**Cause:** Method requires active challenge access  
**Solution:** Wait for hackathon to start or use provided circuit

### Issue 2: "Number of measured qubits is too big"
**Cause:** Circuit >17 qubits with shots=0  
**Solution:** Set shots=1024

### Issue 3: "Statevector is not available"
**Cause:** Job run with shots > 0  
**Solution:** Remove measurement gates for statevector

### Issue 4: Pennylane hanging
**Cause:** Device initialization issues  
**Solution:** Use standard bq.run() instead

---

## Debugging Checklist

Before submitting:
- [ ] API token set in .env
- [ ] Circuit validated (test with small version)
- [ ] Shots parameter set if >17 qubits
- [ ] Bond dimension appropriate for circuit size
- [ ] Submission logged

After submission:
- [ ] Job ID recorded
- [ ] Status monitored
- [ ] Results saved
- [ ] Heavy output extracted (if applicable)

---

## Resources

### Official
- **Platform:** https://app.bluequbit.io
- **Docs:** https://app.bluequbit.io/sdk-docs
- **Examples:** https://github.com/BlueQubitDev/sdk-examples

### This Repository
- **Prep Guide:** `docs/bluequbit_hackathon_prep.md`
- **Findings:** `docs/SDK_CRITICAL_FINDINGS.md`
- **Templates:** `hackathons/hackathon_wSvCWg8f38spoXX3/code_templates/`

### Research
- **ArXiv:** https://arxiv.org/list/quant-ph/recent
- **GitHub:** See `docs/RESEARCH_SUMMARY_EXTERNAL.md`

---

## Emergency Contacts

- **BlueQubit Support:** info@bluequbit.io
- **Platform:** https://app.bluequbit.io

---

## Final Checklist (Before Hackathon Starts)

### Environment
- [ ] Python environment ready
- [ ] Dependencies installed
- [ ] API token working
- [ ] Network connectivity verified

### Tools
- [ ] All templates tested
- [ ] Submission pipeline working
- [ ] Monitoring configured
- [ ] Debugging tools ready

### Knowledge
- [ ] SDK methods reviewed
- [ ] Limitations understood
- [ ] Circuit library familiar
- [ ] Strategy selector tested

### Preparation
- [ ] Bond dimension benchmarks complete
- [ ] Circuit patterns ready
- [ ] Quick reference printed
- [ ] Backup plans prepared

---

**Status:** Ready for hackathon  
**Confidence:** High  
**Next Step:** Wait for challenge to start

---

**Maintained by:** BMad Master  
**Last Updated:** 2026-04-01  
**Version:** 1.0
