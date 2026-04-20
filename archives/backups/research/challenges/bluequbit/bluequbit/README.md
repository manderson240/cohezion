# BlueQubit Repository

**Repository:** https://github.com/manderson240/cohezion/bluequbit  
**Platform:** https://app.bluequbit.io  
**Status:** Active development

This repository contains tools, templates, and documentation for BlueQubit quantum computing platform challenges.

## Repository Structure

```
bluequbit/
├── docs/                          # Documentation and guides
│   └── bluequbit_hackathon_prep.md
├── hackathons/                    # Challenge-specific code
│   ├── little_dimple/            # Previous: 36-qubit peaked circuit
│   └── hackathon_wSvCWg8f38spoXX3/ # Current: New challenge (starts in 3 days)
│       ├── code_templates/        # Reusable code templates
│       ├── tests/                 # Test scripts
│       └── docs/                  # Challenge-specific docs
└── templates/                     # Generic templates

```

## Quick Start

### Prerequisites
- Python 3.10+
- BlueQubit API token

### Installation

```bash
# Install dependencies
pip3 install --break-system-packages bluequbit python-dotenv qiskit pennylane quimb cotengra

# Or with uv
cd /path/to/cohezion
uv pip install bluequbit python-dotenv qiskit pennylane quimb cotengra
```

### Authentication

Add to `.env`:
```bash
BLUEQUBIT_API_TOKEN=your_token_here
```

### Test Connection

```bash
python3 -c "import bluequbit; bq = bluequbit.init(); print('✓ Connected')"
```

## Available Hackathons

### 1. Little Dimple (Completed)
**Type:** 36-qubit peaked circuit simulation  
**Strategy:** FLIER (Matrix Product States)  
**Result:** SNR 9,947 sigma

**Location:** `hackathons/little_dimple/`

**Key Files:**
- `peaked_solver.py` - MPS simulation engine
- `verify_result.py` - Result verification
- `DETAILED_SOLUTION.md` - Full methodology

### 2. Current Challenge (In Progress)
**Type:** Unknown (starts in 3 days)  
**URL:** https://app.bluequbit.io/hackathons/wSvCWg8f38spoXX3

**Location:** `hackathons/hackathon_wSvCWg8f38spoXX3/`

**Status:** Preparation phase - Day 0

## Code Templates

All templates are tested and ready to use:

### Basic Circuit Execution
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

See `hackathons/hackathon_wSvCWg8f38spoXX3/code_templates/basic_circuit.py`

### Available Devices

| Device | Qubits | Type | Cost |
|--------|--------|------|------|
| mps.cpu | 40+ | CPU simulation | $0.00 |
| mps.gpu | 40+ | GPU simulation | $ |
| pauli-path | Any | Observable simulation | $0.00 |
| ibm.heron | 156 | Real QPU | $$ |
| quantinuum.h2 | 56 | Real QPU | $$ |

## Documentation

- **SDK Docs:** https://app.bluequbit.io/sdk-docs
- **API Reference:** https://app.bluequbit.io/sdk-docs/bluequbit.sdk.html
- **Prep Guide:** `docs/bluequbit_hackathon_prep.md`

## Support

- **Platform:** https://app.bluequbit.io
- **Email:** info@bluequbit.io

## Previous Challenges

### Little Dimple Summary
- **Challenge:** Find heavy output from 36-qubit circuit
- **Approach:** Matrix Product State (MPS) simulation
- **Key Innovation:** Manual linear routing with 15,752 SWAP gates
- **Bond Dimension:** 128-512
- **Runtime:** ~44 minutes
- **Result:** Successfully identified heavy output bitstring

## Development

### Adding New Templates

Place in `bluequbit/hackathons/<challenge>/code_templates/`

Template format:
```python
"""
Description of template
"""
import bluequbit
import qiskit

def template_function():
    # Implementation
    pass

if __name__ == "__main__":
    template_function()
```

### Testing

Test all templates before use:
```bash
cd bluequbit/hackathons/<challenge>/code_templates
python3 basic_circuit.py
```

## License

See repository root for license information.

---

**Maintained by:** BMad Master  
**Last Updated:** 2026-04-01
