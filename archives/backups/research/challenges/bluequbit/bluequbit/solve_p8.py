import os

import bluequbit
from qiskit.qasm2 import loads


cohezion_root = "/home/mike-anderson/dev/cohezion"
api_token = None
with open(os.path.join(cohezion_root, ".env")) as f:
    for line in f:
        if "BLUEQUBIT_API_TOKEN" in line:
            api_token = line.split("=")[1].strip()
            break

bq = bluequbit.init(api_token)

# Load P8 circuit
qasm_path = "hackathons/hackathon_oEOtLSSrPSVH60Ah/problems/P8_grid_888_iswap.qasm"
with open(qasm_path) as f:
    qasm = f.read()

circuit = loads(qasm)
print(f"P8: {circuit.num_qubits} qubits, {len(circuit.data)} gates")

print("Running mps.cpu with bond_dim=64...")
result = bq.run(circuit, device="mps.cpu", shots=100000, options={"mps_bond_dimension": 64})

counts = result.get_counts()
top = counts.most_common(5)

print("\nTop 5 results:")
for raw, count in top:
    answer = raw[::-1]
    prob = count / 100000
    print(f"  Raw: {raw}")
    print(f"  Answer: {answer} (prob: {prob:.4f})")
    print(f"  {'✅ Good' if prob > 0.002 else '⚠️ Low prob'}\n")
