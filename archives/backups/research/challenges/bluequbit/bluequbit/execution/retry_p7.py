import os

import bluequbit as bq


# Load API token
api_token = os.environ.get("BLUEQUBIT_API_TOKEN")
if not api_token:
    with open(".env") as f:
        for line in f:
            if "BLUEQUBIT_API_TOKEN" in line:
                api_token = line.split("=")[1].strip()
                break

bq.init(api_token)

# Load circuit
qasm_path = "../hackathons/hackathon_oEOtLSSrPSVH60Ah/problems/P7_heavy_hex_1275.qasm"
with open(qasm_path) as f:
    qasm = f.read()

print("P7: 45 qubits - trying with higher bond_dim")

# Try mps.cpu with bond_dim=32
try:
    task_id = bq.submit(
        qasm, name="P7_heavy_hex_retry_1", device="mps.cpu", shots=100000, bond_dim=32
    )
    print(f"P7 retry submitted: {task_id}")

    result = bq.get(task_id)
    print(f"P7 result: {result}")

    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        top = counts.most_common(1)[0]
        raw = top[0]
        answer = raw[::-1]  # Reverse for MSB
        print(f"Top bitstring (raw): {raw}")
        print(f"Top bitstring (reversed): {answer}")
        print(f"Probability: {top[1] / 100000:.4f}")
except Exception as e:
    print(f"Error: {e}")

# Try pauli-path method
try:
    print("\n--- Trying pauli-path method ---")
    result_pp = bq.submit(qasm, name="P7_heavy_hex_pauli", device="pauli-path", shots=100000)
    print(f"Pauli-path submitted: {result_pp}")
    result = bq.get(result_pp)
    print(f"Pauli-path result: {result}")

    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        top = counts.most_common(1)[0]
        raw = top[0]
        answer = raw[::-1]
        print(f"Pauli-path top bitstring (raw): {raw}")
        print(f"Pauli-path top bitstring (reversed): {answer}")
except Exception as e:
    print(f"Pauli-path error: {e}")
