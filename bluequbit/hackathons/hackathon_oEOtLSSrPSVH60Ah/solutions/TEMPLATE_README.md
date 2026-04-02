# Dynamic Solution Template System

**Location:** `bluequbit/hackathons/hackathon_oEOtLSSrPSVH60Ah/solutions/`

## Files

- **`_template.md`** - Master template with placeholders
- **`generate_solutions.py`** - Python script to generate solutions from data
- **`solutions_data.json`** - JSON data store for all solutions

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PROBLEM_NAME}}` | Filename | P1_little_peak |
| `{{PROBLEM_DISPLAY_NAME}}` | Display name | Little Peak |
| `{{EMOJI}}` | Problem emoji | 🌱 |
| `{{NUM_QUBITS}}` | Qubit count | 4 |
| `{{NUM_GATES}}` | Gate count | 6 |
| `{{CIRCUIT_TYPE}}` | Type description | Simple peaked |
| `{{BOND_DIM}}` | Bond dimension | 64 |
| `{{SHOTS}}` | Number of shots | 10000 |
| `{{RAW_BITSTRING}}` | Raw from BlueQubit | 0011 |
| `{{BITSTRING}}` | Reversed for submission | 1100 |
| `{{PROBABILITY}}` | Best probability | 66.5 |
| `{{UNIFORM_PROB}}` | Uniform probability | 6.67 |
| `{{SNR}}` | SNR value | 90.44 |
| `{{CONFIDENCE}}` | Confidence level | VERY HIGH |
| `{{CONFIDENCE_DESC}}` | Description | extremely clear |
| `{{NOTES}}` | Special notes | Required reversal |
| `{{KEY_INSIGHT}}` | Key insight text | Circuit analysis |
| `{{STATUS}}` | Status | CORRECT, READY |
| `{{DATE}}` | Completion date | 2026-04-02 |

## Usage

### Generate Single Solution
```python
python generate_solutions.py P1
```

### Generate All Solutions
```python
python generate_solutions.py
```

### Add New Problem

Edit `solutions_data.json`:

```json
{
  "P6": {
    "problem_name": "P6_titan_pinnacle",
    "display_name": "Titan Pinnacle",
    "emoji": "🏔️",
    "qubits": 62,
    "gates": 10486,
    "type": "Massive peaked",
    "bond_dim": 16,
    "shots": 100000,
    "raw_bitstring": "...",
    "bitstring": "...",
    "probability": 25.5,
    "uniform_prob": 0.000015,
    "snr": 40.2,
    "confidence": "HIGH",
    "confidence_desc": "clear",
    "notes": " Requires paid tier or bond_dim=16.",
    "key_insight": "62-qubit circuit requiring optimization.",
    "status": "READY",
    "date": "2026-04-02"
  }
}
```

Then run: `python generate_solutions.py P6`

## Benefits

1. **Consistency** - All solutions follow same format
2. **Maintainability** - Update template, regenerate all
3. **Scalability** - Easy to add P11, P12, etc.
4. **Automation** - Can be integrated into CI/CD

## Example Output

See: `P1_little_peak.md`, `P2_swift_rise.md`, etc.

All generated from `_template.md` with consistent formatting.

---

**Version:** 1.0  
**Created:** 2026-04-02
