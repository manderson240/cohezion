#!/usr/bin/env python3
"""Retry P7 with better parameters using system Python"""

import os

import bluequbit
from qiskit.qasm2 import loads


# Load API token from parent directory
cohezion_root = "/home/mike-anderson/dev/cohezion"

api_token = None
with open(os.path.join(cohezion_root, ".env")) as f:
    for line in f:
        if "BLUEQUBIT_API_TOKEN" in line:
            api_token = line.split("=")[1].strip()
            break

# Initialize client
bq = bluequbit.init(api_token)

# Change to bluequbit directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Load circuit and convert to Qiskit
qasm_path = "hackathons/hackathon_oEOtLSSrPSVH60Ah/problems/P7_heavy_hex_1275.qasm"
with open(qasm_path) as f:
    qasm = f.read()

# Convert QASM to Qiskit circuit
circuit = loads(qasm)
print(f"Circuit loaded: {circuit.num_qubits} qubits, {len(circuit.data)} gates")

print("=" * 60)
print("P7 Heavy Hex - Retry with better parameters")
print("=" * 60)

# Method 1: mps.cpu with mps_bond_dimension=32
try:
    print("\n1. Running mps.cpu with mps_bond_dimension=32...")
    result = bq.run(circuit, device="mps.cpu", shots=100000, options={"mps_bond_dimension": 32})

    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        top = counts.most_common(1)[0]
        raw = top[0]
        answer = raw[::-1]  # Reverse for MSB
        prob = top[1] / 100000

        print(f"   Raw bitstring: {raw}")
        print(f"   Answer (reversed): {answer}")
        print(f"   Probability: {prob:.4f}")
        print(f"   Length: {len(answer)} bits")

        if prob > 0.002:  # SNR > 2
            print("   ✅ Good result - submit to platform")
        else:
            print("   ⚠️ Low probability")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Method 2: mps.cpu with mps_bond_dimension=64
try:
    print("\n2. Running mps.cpu with mps_bond_dimension=64...")
    result = bq.run(circuit, device="mps.cpu", shots=100000, options={"mps_bond_dimension": 64})

    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        top = counts.most_common(1)[0]
        raw = top[0]
        answer = raw[::-1]
        prob = top[1] / 100000

        print(f"   Raw bitstring: {raw}")
        print(f"   Answer (reversed): {answer}")
        print(f"   Probability: {prob:.4f}")

        if prob > 0.002:
            print("   ✅ Good result - submit to platform")
        else:
            print("   ⚠️ Low probability")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Method 3: mps.cpu with no bond dimension limit
try:
    print("\n3. Running mps.cpu with no bond dimension limit...")
    result = bq.run(circuit, device="mps.cpu", shots=100000)

    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        top = counts.most_common(1)[0]
        raw = top[0]
        answer = raw[::-1]
        prob = top[1] / 100000

        print(f"   Raw bitstring: {raw}")
        print(f"   Answer (reversed): {answer}")
        print(f"   Probability: {prob:.4f}")

        if prob > 0.002:
            print("   ✅ Good result - submit to platform")
        else:
            print("   ⚠️ Low probability")

except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Done!")
