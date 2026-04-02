# BlueQubit SDK Quick Reference Guide

**SDK Version:** 0.18.5b1  
**Documentation:** https://app.bluequbit.io/sdk-docs/index.html  
**API Reference:** https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html

---

## Installation

```bash
pip install bluequbit
```

**Requirements:** Python 3.10+

---

## Authentication

### Method 1: Environment Variable (Recommended)
```bash
export BLUEQUBIT_API_TOKEN="Wq0MRh8lQbTVSeFzbKZc8V6wqvnWZPWM"
```

```python
import bluequbit
bq = bluequbit.init()  # Auto-reads from env
```

### Method 2: Direct Token
```python
import bluequbit
bq = bluequbit.init("Wq0MRh8lQbTVSeFzbKZc8V6wqvnWZPWM")
```

---

## Core API

### `bluequbit.init(api_token=None, execution_mode=None)`

Initialize BlueQubit client.

**Parameters:**
- `api_token` (str | None): API token. If None, reads from `BLUEQUBIT_API_TOKEN` env var
- `execution_mode` (str | None): `"cloud"`, `"local"`, or `None` (default: cloud)

**Returns:** `BQClient` instance

---

## BQClient Methods

### `run(circuits, device='cpu', asynchronous=False, job_name=None, shots=None, pauli_sum=None, options=None, tags=None, timeout=None)`

Submit a job to run on BlueQubit platform.

**Parameters:**
- `circuits`: Qiskit or Cirq circuit (or list of circuits)
- `device` (str): Device to run on:
  - `"cpu"` - General simulation
  - `"gpu"` - GPU-accelerated simulation
  - `"quantum"` - Real quantum hardware
  - `"mps.cpu"` - **FREE** Matrix Product States on CPU
  - `"mps.gpu"` - MPS on GPU (paid)
  - `"pauli-path"` - **FREE** Ultra-fast expectation values (~100ms)
- `asynchronous` (bool): If True, return immediately without waiting
- `job_name` (str | None): Custom job name for tracking
- `shots` (int | None): Number of shots. If None for non-quantum, returns full probability distribution
- `pauli_sum`: List of `(pauli_string, coefficient)` tuples for expectation values
- `options` (dict | None): Device-specific options (see below)
- `tags` (dict | None): Key-value pairs for job tagging
- `timeout` (float | None): Max wait time in seconds (for synchronous mode)

**Returns:** `JobResult` object

---

### Device-Specific Options

#### MPS Devices (`mps.cpu`, `mps.gpu`)
```python
options = {
    "mps_bond_dimension": 64,  # Schmidt coefficients limit (default: None = unlimited)
}
```

**Note:** MPS has 17-qubit limit for full probabilities. Use `shots` for >17 qubits.

#### Pauli-Path Device (`pauli-path`)
```python
options = {
    "pauli_path_truncation_threshold": 0.01,  # Minimum coefficient (default: None)
    "pauli_path_circuit_transpilation_level": 2,  # 0-3 (default: 2)
}
```

- `pauli_path_truncation_threshold`: Lower bound on Pauli operator coefficients. Smaller = more accurate but slower. Minimum: 1e-5. Required for >13 qubits.
- `pauli_path_circuit_transpilation_level`: Extent of transpilation (0=minimal, 3=extensive)

---

### `estimate(circuits, device='cpu')`

Estimate job runtime and cost **before** running.

**Returns:** `EstimateResult` object with:
- `estimated_runtime` (int): milliseconds
- `estimated_cost` (float): US dollars
- `num_qubits` (int)
- `warning_message` (str)
- `error_message` (str)

---

### `wait(job_ids, timeout=None)`

Wait for async job completion.

**Parameters:**
- `job_ids`: Single ID, list of IDs, or `JobResult` object(s)
- `timeout` (float | None): Max wait time in seconds

**Returns:** `JobResult` or list of `JobResult`

---

### `get(job_ids)`

Get current metadata of jobs.

---

### `cancel(job_ids)`

Cancel pending/running jobs.

---

### `search(run_status=None, created_later_than=None, batch_id=None)`

Search jobs with filters.

**Parameters:**
- `run_status`: Filter by status: `"FAILED_VALIDATION"`, `"PENDING"`, `"QUEUED"`, `"RUNNING"`, `"TERMINATED"`, `"CANCELED"`, `"NOT_ENOUGH_FUNDS"`, `"COMPLETED"`
- `created_later_than`: Filter by datetime
- `batch_id`: Filter by batch ID

**Returns:** List of `JobResult` objects

---

### `run_native_async(*args, polling_interval=1.0, **kwargs)`

**Experimental:** Asyncio support for job submission.

```python
result = await bq.run_native_async(circuit, device="mps.cpu")
```

---

## JobResult Object

Properties:
- `job_id` (str): Unique job ID
- `batch_id` (str): Batch ID
- `job_name` (str): Custom name
- `device` (str): Device used
- `device_options` (dict): Options used
- `estimated_runtime` (int): Estimated ms
- `estimated_cost` (float): Estimated $
- `created_on` (datetime): UTC creation time
- `top_128_results` (dict): Top 128 results
- `num_qubits` (int): Total qubits
- `num_qubits_used` (int): Used qubits
- `tags` (dict): Job tags
- `pauli_sum`: Pauli sum if provided
- `expectation_value` (float | list): Expectation value(s)
- `queue_time_ms` (int): Queue time
- `run_time_ms` (int): Runtime
- `error_message` (str): Error if failed
- `cost` (float): Actual cost
- `has_statevector` (bool): If statevector available
- `circuit`: Original circuit
- `shots` (int): Shots used
- `run_results` (dict | None): Additional results (e.g., mps_build_time)
- `ok` (bool): True if status is "COMPLETED"

Methods:
- `get_statevector()`: Returns NumPy array. Throws if too large.
- `get_counts()`: Returns dict of counts/probabilities (top 131072 results)

---

## Device Comparison

| Device | Cost | Runtime | Best For | Limitations |
|--------|------|---------|----------|-------------|
| `mps.cpu` | **$0.00** | 6-60s | General simulation, peaked circuits | 17-qubit limit for probabilities |
| `pauli-path` | **$0.00** | ~100ms | Expectation values, VQE, QAOA | Expectations only, no counts |
| `mps.gpu` | $ | 2-20s | Large circuits | Requires minimum balance |
| `cpu` | $ | Varies | General simulation | Slower than MPS |
| `gpu` | $ | Varies | GPU-accelerated | Requires minimum balance |
| `quantum` | $$$ | ~1000 shots | Real hardware | Limited availability |

**Recommendation:**
- Use `mps.cpu` for peaked circuits (FREE)
- Use `pauli-path` for VQE/QAOA energy evaluation (FREE, ultra-fast)

---

## Common Patterns

### Pattern 1: Run and Get Statevector
```python
import qiskit
import bluequbit

bq = bluequbit.init()

qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

# No measurement = statevector
result = bq.run(qc, device="mps.cpu")
statevector = result.get_statevector()
print(statevector)
# [0.70710677+0.j 0.+0.j 0.+0.j 0.70710677+0.j]
```

### Pattern 2: Run with Shots (Sampling)
```python
qc = qiskit.QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

result = bq.run(qc, device="mps.cpu", shots=1000)
counts = result.get_counts()
print(counts)
# {'00': 497, '11': 503}
```

### Pattern 3: Pauli-Path Expectation Values
```python
qc = qiskit.QuantumCircuit(3)
qc.h(0)
qc.h(1)
qc.h(2)
qc.ry(0.3, 0)
qc.rz(0.6, 1)
qc.rx(0.7, 2)

pauli_sum = [
    ("XYZ", 0.5),
    ("XXX", 0.2),
    ("XII", 0.3),
    ("III", 0.4),
]

options = {
    "pauli_path_truncation_threshold": 0.1,
}

result = bq.run(
    qc, 
    device="pauli-path", 
    pauli_sum=pauli_sum, 
    options=options
)
print(result.expectation_value)
```

### Pattern 4: Async Execution
```python
# Submit without waiting
job = bq.run(qc, device="mps.cpu", asynchronous=True)
print(f"Job ID: {job.job_id}")

# Do other work...

# Wait for completion
result = bq.wait(job.job_id)
print(result.get_counts())
```

### Pattern 5: Estimate Before Running
```python
qc = qiskit.QuantumCircuit(40)
qc.h(0)
for i in range(39):
    qc.cx(i, i+1)
qc.measure_all()

estimate = bq.estimate(qc, device="mps.cpu")
print(f"Estimated time: {estimate.estimated_runtime}ms")
print(f"Estimated cost: ${estimate.estimated_cost:.4f}")
```

### Pattern 6: MPS with Bond Dimension
```python
qc = qiskit.QuantumCircuit(40)
qc.h(0)
for i in range(39):
    qc.cx(i, i+1)
qc.measure_all()

options = {
    "mps_bond_dimension": 2,  # Limit Schmidt coefficients
}

result = bq.run(qc, device="mps.cpu", options=options)
print(result.get_counts())
```

### Pattern 7: Search Jobs
```python
# Find completed jobs
completed = bq.search(run_status="COMPLETED")

# Find recent jobs
from datetime import datetime, timedelta
recent = bq.search(
    created_later_than=datetime.utcnow() - timedelta(hours=24)
)

# Get specific job
job = bq.get("job_id_here")
print(job.status)
```

### Pattern 8: Pennylane Integration
```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("bluequbit.cpu", wires=1, token="YOUR_TOKEN")

@qml.qnode(dev)
def circuit(angle):
    qml.RY(angle, wires=0)
    return qml.probs(wires=0)

probabilities = circuit(np.pi / 4)
print(probabilities)
# [0.85355339 0.14644661]
```

**Note:** Requires `pennylane >= 0.39`. Supports up to 32 qubits (CPU) or 33 qubits (GPU).

---

## Qiskit Provider

```python
from bluequbit import BlueQubitProvider

provider = BlueQubitProvider()
backend = provider.get_backend()

# Use with Qiskit
from qiskit import QuantumCircuit, transpile

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

transpiled = transpile(qc, backend)
job = backend.run(transpiled)
result = job.result()
```

---

## Error Handling

All exceptions in `bluequbit.exceptions`:

```python
from bluequbit import exceptions

try:
    result = bq.run(circuit, device="mps.cpu")
except exceptions.BQJobInvalidDeviceTypeError:
    print("Invalid device")
except exceptions.BQJobNotCompleteError:
    print("Job not complete")
except exceptions.BQJobStatevectorTooLargeError:
    print("Statevector too large")
except exceptions.BQUnauthorizedAccessError:
    print("Invalid token or no access")
except exceptions.BQAPIError as e:
    print(f"API error: {e}")
```

---

## Critical Limitations

### MPS Devices
- **17-qubit limit** for full probability distribution
- For >17 qubits, must use `shots` parameter (sampling)
- Returns only **top 131072 (2^17)** results in counts

### Pauli-Path
- **Expectation values only** - no counts, no statevector
- For >13 qubits, `pauli_path_truncation_threshold` is **required**
- Only supports Qiskit circuits (not Cirq directly)

### Statevector
- Throws exception if too large
- Use only for small circuits (<20 qubits)

---

## Tips for Hackathons

### 1. Use Free Devices for Testing
```python
# Test on FREE device before submitting
result = bq.run(circuit, device="mps.cpu")  # FREE
# or
result = bq.run(circuit, device="pauli-path", pauli_sum=observable)  # FREE
```

### 2. Estimate Costs First
```python
estimate = bq.estimate(circuit, device="mps.gpu")
if estimate.estimated_cost < 0.01:  # Less than 1 cent
    result = bq.run(circuit, device="mps.gpu")
```

### 3. Use Job Names for Tracking
```python
result = bq.run(
    circuit, 
    device="mps.cpu",
    job_name="hackathon_attempt_1",
    tags={"challenge": "oEOtLSSrPSVH60Ah", "attempt": 1}
)
```

### 4. Search for Previous Jobs
```python
# Find all your jobs for a challenge
jobs = bq.search(tags={"challenge": "oEOtLSSrPSVH60Ah"})
```

### 5. Handle Large Circuits
```python
# For >17 qubits, use shots
result = bq.run(large_circuit, device="mps.cpu", shots=100000)
counts = result.get_counts()
```

---

## Full Example: Peaked Circuit Solver

```python
import qiskit
import bluequbit
from collections import Counter

bq = bluequbit.init()

# Load peaked circuit
with open("peaked_36q.qasm") as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# Run with high shots
result = bq.run(
    qc, 
    device="mps.cpu",
    shots=100000,
    options={"mps_bond_dimension": 128}
)

# Find heavy output
counts = result.get_counts()
total_shots = sum(counts.values())
mean_prob = 1.0 / len(counts)

heavy_outputs = [
    bitstring for bitstring, count in counts.items()
    if count / total_shots > mean_prob
]

# Calculate SNR
heavy_count = sum(counts[b] for b in heavy_outputs)
snr = (heavy_count / total_shots - 0.5) / (0.5 / total_shots ** 0.5)

print(f"Found {len(heavy_outputs)} heavy outputs")
print(f"SNR: {snr:.2f} sigma")
print(f"Best bitstring: {max(counts, key=counts.get)}")
```

---

## Links

- **Main Docs:** https://app.bluequbit.io/sdk-docs/index.html
- **API Reference:** https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html
- **Platform:** https://app.bluequbit.io
- **Support:** info@bluequbit.io

---

**Last Updated:** 2026-04-01  
**SDK Version:** 0.18.5b1
