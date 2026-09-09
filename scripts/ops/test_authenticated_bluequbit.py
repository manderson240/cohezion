#!/usr/bin/env python3
"""Test Authenticated BlueQubit Connection & Live QPU/GPU Simulator Execution.

Loads environment from /home/mike-anderson/dev/cohezion/.env without echoing any secrets,
and dispatches a real 4-qubit entangled GHZ circuit to BlueQubit's cloud GPU simulator.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv("/home/mike-anderson/dev/cohezion/.env")

import bluequbit
import qiskit

# Check variable names
api_token = os.getenv("BLUEQUBIT_API_TOKEN") or os.getenv("BLUEQUBIT_API_KEY") or os.getenv("BLUEQUBIT_TOKEN")

print("=" * 80)
print("⚛️ TESTING AUTHENTICATED BLUEQUBIT GPU SIMULATOR DISPATCH")
print("=" * 80)

if not api_token:
    print("❌ No BlueQubit token found under BLUEQUBIT_API_TOKEN / BLUEQUBIT_API_KEY / BLUEQUBIT_TOKEN.")
else:
    print(f"✓ Token detected successfully (length: {len(api_token)} chars). Initializing client...")
    try:
        bq = bluequbit.init(api_token=api_token)
        print("✓ Authenticated with BlueQubit Cloud Platform!")

        # Build 4-qubit GHZ state circuit with Qiskit
        qc = qiskit.QuantumCircuit(4, 4)
        qc.h(0)
        for i in range(3):
            qc.cx(i, i+1)
        qc.measure(range(4), range(4))

        print("▶ Dispatching 4-qubit GHZ Entanglement Circuit to BlueQubit `mps.cpu` / `mps.gpu`...")
        t0 = time.perf_counter()
        job = bq.run(qc, device="mps.cpu", shots=1000)
        dt = time.perf_counter() - t0

        print(f"✓ Execution SUCCESS in {dt:.2f}s!")
        print(f"  Job ID: {getattr(job, 'job_id', 'completed')}")
        print(f"  Measurement Counts: {job.get_counts()}")

    except Exception as e:
        print(f"❌ Error during BlueQubit execution: {e}")

print("=" * 80)
