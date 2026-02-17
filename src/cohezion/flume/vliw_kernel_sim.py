import logging
import time

import numpy as np


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VLIW_Kernel_Simulation")


class VLIWSimulator:
    def __init__(self, items=256, rounds=16):
        self.items = items
        self.rounds = rounds
        self.scratchpad_limit = 1536  # 1.5 KB

    def hash_round(self, data):
        """A simplified bit-exact hash round."""
        # Represents: data = (data ^ (data << 13)) & 0xFFFFFFFF
        data = (data ^ (data << 13)) & 0xFFFFFFFF
        data = (data ^ (data >> 17)) & 0xFFFFFFFF
        data = (data ^ (data << 5)) & 0xFFFFFFFF
        return data

    def run_vectorized(self):
        """Simulates the 256-item vectorized kernel."""
        # Initial data (random bitstrings)
        data = np.random.randint(0, 2**32, size=self.items, dtype=np.uint32)
        reference = data.copy()

        start_time = time.perf_counter()

        # Scalar reference (for verification)
        for i in range(self.items):
            for _ in range(self.rounds):
                reference[i] = self.hash_round(reference[i])

        # Vectorized implementation (Simulating VLIW lanes)
        # We process in chunks of 8 (SIMD VLEN=8)
        vector_data = data.copy()
        for _ in range(self.rounds):
            # BARRIER: SYNC_DATA_COMMIT (Enforced by Autonomic Refinement)
            for i in range(0, self.items, 8):
                chunk = vector_data[i : i + 8]
                vector_data[i : i + 8] = self.hash_round(chunk)

        end_time = time.perf_counter()

        # Verify correctness
        matches = np.all(vector_data == reference)
        latency_ms = (end_time - start_time) * 1000

        print("\n" + "=" * 50)
        print("VLIW KERNEL SIMULATION REPORT")
        print("=" * 50)
        print(f"Items Processed: {self.items}")
        print(f"Hash Rounds: {self.rounds}")
        print(f"Simulation Latency: {latency_ms:.2f} ms")
        print(f"Memory Usage: {self.items * 4} bytes (Limit: {self.scratchpad_limit})")

        if matches:
            print("\n✅ SUCCESS: Bit-Exact Verification Passed.")
            print("Vectorized output matches scalar reference across all 256 items.")
        else:
            print("\n❌ FAILURE: Bit-Mismatch Detected.")
            diff_indices = np.where(vector_data != reference)[0]
            print(f"Error count: {len(diff_indices)} at indices {diff_indices[:5]}...")


if __name__ == "__main__":
    sim = VLIWSimulator()
    sim.run_vectorized()
